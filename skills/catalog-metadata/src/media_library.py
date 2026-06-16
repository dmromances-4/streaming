"""Resolución de archivos de vídeo/HLS en biblioteca local o servidor remoto."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

from episode_utils import matches_episode_filename

from config import settings

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".m4v", ".webm", ".mov", ".ts"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass"}
HLS_MANIFEST_NAMES = ("index.m3u8", "playlist.m3u8", "master.m3u8")

_series_index_cache: dict[str, tuple[float, dict[tuple[int, int], Path]]] = {}


@lru_cache(maxsize=1)
def _load_media_aliases() -> dict[str, str]:
    path = Path(settings.media_aliases_path)
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if v}


def reload_media_aliases() -> None:
    _load_media_aliases.cache_clear()
    clear_series_index_cache()


def clear_series_index_cache(series_id: str | None = None) -> None:
    if series_id:
        _series_index_cache.pop(series_id, None)
    else:
        _series_index_cache.clear()


def _slug_folder_names(series_id: str, series_title: str) -> list[str]:
    names: list[str] = []
    for value in (series_id, series_title):
        if value and value not in names:
            names.append(value)
    return names


def _season_dir_names(season: int) -> list[str]:
    return [
        f"Season {season:02d}",
        f"Season {season}",
        f"S{season:02d}",
        f"Season{season:02d}",
    ]


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _title_tokens(series_title: str) -> list[str]:
    return [t for t in _normalize_for_match(series_title).split() if len(t) > 2]


def _is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def _find_hls_manifest(directory: Path) -> Path | None:
    for name in HLS_MANIFEST_NAMES:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    for candidate in sorted(directory.glob("*.m3u8")):
        if candidate.is_file():
            return candidate
    return None


_EPISODE_INDEX_PATTERN = re.compile(r"(?i)s0?(\d+)[ ._-]?e0?(\d+)\b")


def _episode_from_filename(name: str) -> tuple[int, int] | None:
    match = _EPISODE_INDEX_PATTERN.search(name)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _index_episode_file(path: Path, index: dict[tuple[int, int], Path]) -> None:
    if not path.is_file():
        return
    coords = _episode_from_filename(path.name)
    if not coords:
        return
    season, episode = coords
    if path.suffix.lower() != ".m3u8" and not _is_video_file(path):
        return
    current = index.get((season, episode))
    if current is None:
        index[(season, episode)] = path
    elif _is_video_file(path) and _is_video_file(current):
        if path.stat().st_size > current.stat().st_size:
            index[(season, episode)] = path
    elif path.suffix.lower() == ".m3u8":
        index[(season, episode)] = path


def _build_series_index(series_dirs: list[Path]) -> dict[tuple[int, int], Path]:
    index: dict[tuple[int, int], Path] = {}
    for series_dir in series_dirs:
        if not series_dir.is_dir():
            continue
        for path in series_dir.rglob("*"):
            if path.is_file():
                _index_episode_file(path, index)
    return index


def _series_dirs_mtime(series_dirs: list[Path]) -> float:
    mtimes = [d.stat().st_mtime for d in series_dirs if d.is_dir()]
    return max(mtimes) if mtimes else 0.0


def get_series_episode_index(
    series_id: str, series_title: str
) -> dict[tuple[int, int], Path]:
    root = Path(settings.media_root)
    if not root.is_dir():
        return {}
    series_dirs = _resolve_series_directories(series_id, series_title, root)
    if not series_dirs:
        return {}

    mtime = _series_dirs_mtime(series_dirs)
    cached = _series_index_cache.get(series_id)
    if cached and cached[0] == mtime:
        return cached[1]

    index = _build_series_index(series_dirs)
    _series_index_cache[series_id] = (mtime, index)
    return index


def _pick_episode_file(directory: Path, season: int, episode: int) -> Path | None:
    matches: list[Path] = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if matches_episode_filename(name, season, episode):
            if _is_video_file(path) or path.suffix.lower() == ".m3u8":
                matches.append(path)
            continue
        if path.suffix.lower() == ".m3u8" and matches_episode_filename(
            path.parent.name, season, episode
        ):
            matches.append(path)

    if matches:
        m3u8 = [p for p in matches if p.suffix.lower() == ".m3u8"]
        if m3u8:
            return m3u8[0]
        videos = [p for p in matches if _is_video_file(p)]
        return max(videos, key=lambda p: p.stat().st_size)

    hls = _find_hls_manifest(directory)
    if hls:
        return hls
    return None


def _resolve_series_directories(
    series_id: str, series_title: str, root: Path
) -> list[Path]:
    dirs: list[Path] = []
    aliases = _load_media_aliases()

    alias = aliases.get(series_id)
    if alias:
        alias_path = Path(alias)
        if not alias_path.is_absolute():
            alias_path = root / alias
        if alias_path.is_dir():
            dirs.append(alias_path)

    for series_name in _slug_folder_names(series_id, series_title):
        series_dir = root / series_name
        if series_dir.is_dir() and series_dir not in dirs:
            dirs.append(series_dir)

    tokens = _title_tokens(series_title)
    if tokens:
        for child in root.iterdir():
            if not child.is_dir() or child in dirs:
                continue
            name_norm = _normalize_for_match(child.name)
            if all(token in name_norm for token in tokens):
                dirs.append(child)

    return dirs


def _search_in_series_dirs(
    series_dirs: list[Path], season: int, episode: int
) -> Path | None:
    for series_dir in series_dirs:
        for season_name in _season_dir_names(season):
            season_dir = series_dir / season_name
            if season_dir.is_dir():
                found = _pick_episode_file(season_dir, season, episode)
                if found:
                    return found

        found = _pick_episode_file(series_dir, season, episode)
        if found:
            return found
    return None


def _search_local_library(
    series_id: str,
    series_title: str,
    season: int,
    episode: int,
) -> Path | None:
    index = get_series_episode_index(series_id, series_title)
    indexed = index.get((season, episode))
    if indexed and indexed.is_file():
        return indexed

    root = Path(settings.media_root)
    if not root.is_dir():
        return None

    series_dirs = _resolve_series_directories(series_id, series_title, root)
    found = _search_in_series_dirs(series_dirs, season, episode)
    if found:
        clear_series_index_cache(series_id)
        return found

    pattern = re.compile(rf"(?i)s0?{season}[ ._-]?e0?{episode}\b")
    title_tokens = _title_tokens(series_title)
    search_roots = series_dirs or [root]
    for search_root in search_roots:
        for path in search_root.rglob("*"):
            if not path.is_file():
                continue
            name = path.name
            if path.suffix.lower() == ".m3u8":
                if pattern.search(name):
                    return path
                continue
            if not _is_video_file(path):
                continue
            if not matches_episode_filename(name, season, episode):
                continue
            lower = name.lower()
            if title_tokens and not all(token in lower for token in title_tokens[:2]):
                continue
            return path

    return None


def find_subtitle_for_video(video_path: Path) -> str | None:
    stem = video_path.stem
    parent = video_path.parent
    for ext in SUBTITLE_EXTENSIONS:
        for candidate in (
            parent / f"{stem}{ext}",
            parent / f"{stem}.es{ext}",
            parent / f"{stem}.spa{ext}",
        ):
            if candidate.is_file():
                return str(candidate)
    for sub in parent.glob("*.srt"):
        if sub.is_file():
            return str(sub)
    return None


def _remote_candidates(series_id: str, series_title: str, season: int, episode: int) -> list[str]:
    base = settings.media_url_base.rstrip("/")
    if not base:
        return []

    sxe = f"S{season:02d}E{episode:02d}"
    paths = [
        f"{series_id}/Season {season:02d}/{sxe}.m3u8",
        f"{series_id}/Season {season:02d}/{sxe}.mp4",
        f"{series_title}/Season {season:02d}/{sxe}.m3u8",
        f"{series_title}/Season {season:02d}/{sxe}.mp4",
        f"{series_id}/{sxe}.m3u8",
        f"{series_id}/{sxe}.mp4",
    ]
    return [f"{base}/{quote(path, safe='/')}" for path in paths]


def _classify_media_path(path: Path) -> tuple[str, str]:
    if path.suffix.lower() == ".m3u8":
        return str(path), "hls"
    return str(path), "file"


def resolve_episode_media(
    *,
    series_id: str,
    series_title: str,
    season: int,
    episode: int,
    stored_path: str | None = None,
) -> tuple[str | None, str]:
    """Devuelve (ruta_absoluta_o_url, tipo: file|hls|url)."""
    if stored_path:
        path = Path(stored_path)
        if path.is_file():
            return _classify_media_path(path)
        if stored_path.startswith(("http://", "https://")):
            if stored_path.lower().endswith(".m3u8"):
                return stored_path, "url_hls"
            return stored_path, "url"

    local = _search_local_library(series_id, series_title, season, episode)
    if local:
        return _classify_media_path(local)

    for remote in _remote_candidates(series_id, series_title, season, episode):
        return remote, "url_hls" if remote.lower().endswith(".m3u8") else "url"

    label = f"S{season:02d}E{episode:02d}"
    if stored_path and not Path(stored_path).is_file():
        return None, f"No local media file for {label} (archivo movido o eliminado)"
    return None, f"No local media file for {label}"


def probe_episode_media(
    *,
    series_id: str,
    series_title: str,
    season: int,
    episode: int,
    stored_path: str | None = None,
) -> dict[str, Any]:
    aliases = _load_media_aliases()
    root = Path(settings.media_root)
    series_dirs = (
        _resolve_series_directories(series_id, series_title, root)
        if root.is_dir()
        else []
    )
    source, media_type = resolve_episode_media(
        series_id=series_id,
        series_title=series_title,
        season=season,
        episode=episode,
        stored_path=stored_path,
    )
    subtitle_path = None
    if source and media_type == "file":
        subtitle_path = find_subtitle_for_video(Path(source))

    return {
        "series_id": series_id,
        "season": season,
        "episode": episode,
        "found": source is not None,
        "source_path": source,
        "media_type": media_type if source else None,
        "subtitle_path": subtitle_path,
        "alias": aliases.get(series_id),
        "series_directories": [str(d) for d in series_dirs],
        "stored_path_valid": bool(stored_path and Path(stored_path).is_file()),
    }


def resolve_movie_media(
    *,
    title_id: str,
    title: str,
    stored_path: str | None = None,
) -> tuple[str | None, str]:
    if stored_path:
        path = Path(stored_path)
        if path.is_file():
            return _classify_media_path(path)
        if stored_path.startswith(("http://", "https://")):
            if stored_path.lower().endswith(".m3u8"):
                return stored_path, "url_hls"
            return stored_path, "url"

    root = Path(settings.media_root)
    if root.is_dir():
        for movie_dir in _resolve_series_directories(title_id, title, root):
            hls = _find_hls_manifest(movie_dir)
            if hls:
                return str(hls), "hls"
            videos = [p for p in movie_dir.iterdir() if p.is_file() and _is_video_file(p)]
            if videos:
                return str(max(videos, key=lambda p: p.stat().st_size)), "file"

        for name in _slug_folder_names(title_id, title):
            for ext in VIDEO_EXTENSIONS | {".m3u8"}:
                direct = root / f"{name}{ext}"
                if direct.is_file():
                    return str(direct), "hls" if ext == ".m3u8" else "file"

    base = settings.media_url_base.rstrip("/")
    if base:
        for name in _slug_folder_names(title_id, title):
            for suffix in (".m3u8", ".mp4", ".mkv"):
                url = f"{base}/{quote(f'{name}{suffix}', safe='/')}"
                return url, "url_hls" if suffix == ".m3u8" else "url"

    return None, "No local media file for movie"


def build_media_manifest_url(source_path: str) -> str:
    """Convierte ruta bajo media_root en URL pública servida por nginx."""
    root = Path(settings.media_root).resolve()
    path = Path(source_path).resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return source_path
    return f"/api/media/{quote(relative, safe='/')}"
