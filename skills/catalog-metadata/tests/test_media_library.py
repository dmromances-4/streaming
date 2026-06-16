"""Tests de resolución de biblioteca local."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_src = Path(__file__).resolve().parents[1] / "src"
_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
for p in (str(_src), str(_shared)):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def media_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    from config import Settings

    monkeypatch.setattr(
        "media_library.settings",
        Settings(
            media_root=str(tmp_path),
            media_url_base="",
            media_aliases_path=str(tmp_path / "media-aliases.yaml"),
        ),
    )
    from media_library import clear_series_index_cache, reload_media_aliases

    reload_media_aliases()
    clear_series_index_cache()
    return tmp_path


def _write_aliases(media_root: Path, mapping: dict[str, str]) -> None:
    import yaml

    path = media_root / "media-aliases.yaml"
    path.write_text(yaml.dump(mapping), encoding="utf-8")
    from media_library import reload_media_aliases

    reload_media_aliases()


def test_resolve_episode_in_season_folder(media_root: Path):
    from media_library import resolve_episode_media

    season_dir = media_root / "series-american-breaking-bad" / "Season 01"
    season_dir.mkdir(parents=True)
    video = season_dir / "Breaking.Bad.S01E02.1080p.mkv"
    video.write_bytes(b"fake")

    source, media_type = resolve_episode_media(
        series_id="series-american-breaking-bad",
        series_title="Breaking Bad",
        season=1,
        episode=2,
    )
    assert source == str(video)
    assert media_type == "file"


def test_series_episode_index(media_root: Path):
    from media_library import get_series_episode_index

    folder = "Boardwalk Empire 2010 Seasons 1 to 5 Complete 1080p BluRay x264 [i_c]"
    season_dir = media_root / folder / "Season 2"
    season_dir.mkdir(parents=True)
    video = season_dir / "Boardwalk Empire S02E03.mkv"
    video.write_bytes(b"fake")

    index = get_series_episode_index(
        "series-american-boardwalk-empire", "Boardwalk Empire"
    )
    assert index[(2, 3)] == video


def test_probe_episode_media(media_root: Path):
    from media_library import probe_episode_media

    folder = "Californication (2007) Season 1-7"
    _write_aliases(media_root, {"series-american-californication": folder})
    season_dir = media_root / folder / "Season 1"
    season_dir.mkdir(parents=True)
    video = season_dir / "Californication S01E02.mkv"
    video.write_bytes(b"fake")
    sub = season_dir / "Californication S01E02.srt"
    sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHola", encoding="utf-8")

    result = probe_episode_media(
        series_id="series-american-californication",
        series_title="Californication",
        season=1,
        episode=2,
    )
    assert result["found"] is True
    assert result["subtitle_path"] == str(sub)


def test_resolve_episode_hls_manifest(media_root: Path):
    from media_library import build_media_manifest_url, resolve_episode_media

    season_dir = media_root / "series-american-breaking-bad" / "Season 01"
    season_dir.mkdir(parents=True)
    manifest = season_dir / "index.m3u8"
    manifest.write_text("#EXTM3U\n", encoding="utf-8")

    source, media_type = resolve_episode_media(
        series_id="series-american-breaking-bad",
        series_title="Breaking Bad",
        season=1,
        episode=1,
    )
    assert source == str(manifest)
    assert media_type == "hls"
    assert build_media_manifest_url(source) == (
        "/api/media/series-american-breaking-bad/Season%2001/index.m3u8"
    )


def test_resolve_episode_missing(media_root: Path):
    from media_library import resolve_episode_media

    source, err = resolve_episode_media(
        series_id="series-american-breaking-bad",
        series_title="Breaking Bad",
        season=1,
        episode=9,
    )
    assert source is None
    assert "No local media file" in err


def test_resolve_episode_via_torrent_alias(media_root: Path):
    from media_library import resolve_episode_media

    folder = (
        "Californication (2007) Season 1-7 S01-S07 "
        "(1080p BluRay x265 HEVC 10bit AAC 5.1 BugsFunny) [UTR]"
    )
    _write_aliases(
        media_root,
        {"series-american-californication": folder},
    )
    season_dir = media_root / folder / "Season 1"
    season_dir.mkdir(parents=True)
    video = season_dir / "Californication S01E01 Pilot.mkv"
    video.write_bytes(b"fake")

    source, media_type = resolve_episode_media(
        series_id="series-american-californication",
        series_title="Californication",
        season=1,
        episode=1,
    )
    assert source == str(video)
    assert media_type == "file"


def test_resolve_episode_fuzzy_torrent_folder(media_root: Path):
    from media_library import resolve_episode_media

    folder = "Boardwalk Empire 2010 Seasons 1 to 5 Complete 1080p BluRay x264 [i_c]"
    series_dir = media_root / folder
    season_dir = series_dir / "Season 1"
    season_dir.mkdir(parents=True)
    video = season_dir / "Boardwalk Empire S01E01 Boardwalk Empire.mkv"
    video.write_bytes(b"fake")

    source, media_type = resolve_episode_media(
        series_id="series-american-boardwalk-empire",
        series_title="Boardwalk Empire",
        season=1,
        episode=1,
    )
    assert source == str(video)
    assert media_type == "file"


def test_series_episode_index(media_root: Path):
    from media_library import get_series_episode_index

    folder = "Boardwalk Empire 2010 Seasons 1 to 5 Complete 1080p BluRay x264 [i_c]"
    season_dir = media_root / folder / "Season 2"
    season_dir.mkdir(parents=True)
    video = season_dir / "Boardwalk Empire S02E03.mkv"
    video.write_bytes(b"fake")

    index = get_series_episode_index(
        "series-american-boardwalk-empire", "Boardwalk Empire"
    )
    assert index[(2, 3)] == video


def test_probe_episode_media(media_root: Path):
    from media_library import probe_episode_media

    folder = "Californication (2007) Season 1-7"
    _write_aliases(media_root, {"series-american-californication": folder})
    season_dir = media_root / folder / "Season 1"
    season_dir.mkdir(parents=True)
    video = season_dir / "Californication S01E02.mkv"
    video.write_bytes(b"fake")
    sub = season_dir / "Californication S01E02.srt"
    sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHola", encoding="utf-8")

    result = probe_episode_media(
        series_id="series-american-californication",
        series_title="Californication",
        season=1,
        episode=2,
    )
    assert result["found"] is True
    assert result["subtitle_path"] == str(sub)
