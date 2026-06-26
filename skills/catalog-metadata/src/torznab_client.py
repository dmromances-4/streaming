"""Cliente Torznab genérico (Jackett / Prowlarr)."""

from __future__ import annotations

import re
import sys
import unicodedata
from typing import Any
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import httpx

_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from episode_utils import (  # noqa: E402
    is_season_pack_filename,
    matches_episode_filename,
)

from config import settings
from errors import UpstreamError
from skill_telemetry import log, record_error


def build_search_query(title: str, content_type: str, year: int | None = None) -> str:
    year_part = f" {year}" if year else ""
    if content_type == "series":
        return f"{title}{year_part} S01 1080p"
    return f"{title}{year_part} 1080p"


def build_episode_query(
    series_title: str, season: int, episode: int, year: int | None = None
) -> str:
    del year  # year kept for API compatibility; broad queries omit it
    return f"{series_title} S{season:02d}E{episode:02d} 1080p"


def build_episode_query_variants(
    series_title: str, season: int, episode: int, year: int | None = None
) -> list[str]:
    sxe = f"S{season:02d}E{episode:02d}"
    queries = [
        f"{series_title} {sxe}",
        f"{series_title} {sxe} 1080p",
        f"{series_title} {sxe} WEB-DL",
        f"{series_title} {season}x{episode:02d}",
        f"{series_title} {sxe} x265",
    ]
    if year:
        queries.append(f"{series_title} {year} {sxe} 1080p")
    return queries


def normalize_search_title(text: str) -> str:
    """Limpia título para búsqueda: sin acentos ni caracteres especiales."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", " ", ascii_text).strip()


def _normalize_title_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


_BLOCKED_EXTENSIONS = (".exe", ".scr", ".bat", ".zip", ".rar", ".lnk")
_BLOCKED_QUALITY = (
    "camrip",
    "telesync",
    "hdcam",
    "workprint",
    " hdcam",
    " cam ",
    " ts ",
    "tsrip",
)
_VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".m4v", ".webm", ".mov", ".ts")


def is_safe_torrent_title(title: str) -> bool:
    t = title.lower()
    for ext in _BLOCKED_EXTENSIONS:
        if ext in t:
            return False
    for bad in _BLOCKED_QUALITY:
        if bad in t:
            return False
    if "cam" in t and "camera" not in t:
        if re.search(r"\bcam\b", t) or "camrip" in t:
            return False
    has_video_ext = any(ext in t for ext in _VIDEO_EXTENSIONS)
    has_quality_tag = any(
        tag in t
        for tag in ("1080p", "720p", "2160p", "bluray", "web-dl", "webrip", "hdtv")
    )
    return has_video_ext or has_quality_tag or "s0" in t or "s1" in t or "e0" in t


def _series_title_in_torrent(torrent_title: str, series_title: str) -> bool:
    series_norm = _normalize_title_text(series_title)
    if not series_norm:
        return False
    torrent_norm = _normalize_title_text(torrent_title)
    return series_norm in torrent_norm


def _parse_size(text: str | None) -> int:
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _score_item(title: str, size: int, seeders: int, content_type: str) -> float:
    score = seeders * 10.0
    t = title.lower()
    if "1080p" in t or "webrip" in t or "web-dl" in t:
        score += 50
    if "h.264" in t or "x264" in t:
        score += 20
    if content_type == "movie" and 800_000_000 <= size <= 4_000_000_000:
        score += 30
    if content_type == "series" and 200_000_000 <= size <= 2_000_000_000:
        score += 30
    if "cam" in t or "ts " in t or "hdcam" in t:
        score -= 100
    return score


def _score_episode_item(
    title: str,
    size: int,
    seeders: int,
    season: int,
    episode: int,
    *,
    series_title: str | None = None,
    allow_season_pack: bool = False,
    prefer_hevc: bool | None = None,
    min_seeders: int | None = None,
) -> float:
    if not is_safe_torrent_title(title):
        return -1000.0

    min_seeders = min_seeders if min_seeders is not None else settings.torrent_min_seeders
    if seeders < min_seeders:
        return -1000.0

    prefer_hevc = (
        settings.torrent_prefer_hevc if prefer_hevc is None else prefer_hevc
    )
    score = seeders * 10.0
    t = title.lower()
    if matches_episode_filename(title, season, episode):
        if series_title and not _series_title_in_torrent(title, series_title):
            return -1000.0
        score += 200
        if series_title:
            score += 80
    elif allow_season_pack and is_season_pack_filename(title, season):
        if series_title and not _series_title_in_torrent(title, series_title):
            return -1000.0
        score += 40
    else:
        score -= 80
    if any(tag in t for tag in ("1080p", "720p", "2160p", "bluray", "web-dl", "webrip")):
        score += 50
    if prefer_hevc and ("x265" in t or "hevc" in t):
        score += 25
    elif "h.264" in t or "x264" in t:
        score += 20
    if 300_000_000 <= size <= 1_500_000_000:
        score += 30
    elif 100_000_000 <= size <= 3_000_000_000:
        score += 10
    return score


class TorznabClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _search_url(self, query: str) -> str:
        base = settings.effective_indexer_url.rstrip("/")
        api_key = settings.effective_indexer_api_key
        q = quote(query)

        if settings.indexer_provider == "prowlarr":
            # Aggregated Torznab feed (indexer id 0 = all indexers).
            return f"{base}/0/api?apikey={quote(api_key)}&t=search&q={q}"
        return (
            f"{base}/api/v2.0/indexers/all/results/torznab/api"
            f"?apikey={quote(api_key)}&t=search&q={q}"
        )

    def _magnet_from_prowlarr_result(self, result: dict[str, Any]) -> str | None:
        info_hash = result.get("infoHash")
        title = result.get("title") or result.get("fileName") or ""
        if info_hash:
            return f"magnet:?xt=urn:btih:{info_hash}&dn={quote(title)}"
        magnet_url = result.get("magnetUrl") or ""
        if isinstance(magnet_url, str) and magnet_url.startswith("magnet:"):
            return magnet_url
        return None

    async def _prowlarr_search_items(self, query: str) -> list[dict[str, Any]]:
        if not settings.effective_indexer_api_key:
            return []
        if not self._client:
            raise UpstreamError("Torznab client not initialized")

        base = settings.effective_indexer_url.rstrip("/")
        url = f"{base}/api/v1/search?query={quote(query)}&type=search"
        try:
            response = await self._client.get(
                url,
                headers={"X-Api-Key": settings.effective_indexer_api_key},
            )
            response.raise_for_status()
            results = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("prowlarr_search_failed", query=query[:80], error=str(exc))
            return []

        items: list[dict[str, Any]] = []
        for result in results:
            magnet = self._magnet_from_prowlarr_result(result)
            if not magnet:
                continue
            items.append(
                {
                    "title": (result.get("title") or "").strip(),
                    "magnet": magnet,
                    "size": int(result.get("size") or 0),
                    "seeders": int(result.get("seeders") or 0),
                }
            )
        return items

    async def search_magnet(
        self,
        title: str,
        content_type: str,
        year: int | None = None,
    ) -> tuple[str | None, str | None]:
        if not settings.effective_indexer_api_key:
            return None, "INDEXER_API_KEY not configured"

        if not self._client:
            raise UpstreamError("Torznab client not initialized")

        query = build_search_query(title, content_type, year)
        best_magnet: str | None = None
        best_score = -1.0

        try:
            raw_items = await self._search_items(query)
        except UpstreamError:
            raise
        except httpx.HTTPError as exc:
            record_error("torznab_error")
            return None, str(exc)

        for item in raw_items:
            score = _score_item(
                item["title"], item["size"], item["seeders"], content_type
            )
            if score > best_score:
                best_score = score
                best_magnet = item["magnet"]

        if best_magnet:
            log.info(
                "torznab_found",
                title=title[:60],
                query=query,
                provider=settings.indexer_provider,
            )
            return best_magnet, None

        return None, f"No results for query: {query}"

    async def _search_items(self, query: str) -> list[dict[str, Any]]:
        if not settings.effective_indexer_api_key:
            return []
        if not self._client:
            raise UpstreamError("Torznab client not initialized")

        if settings.indexer_provider == "prowlarr":
            return await self._prowlarr_search_items(query)

        url = self._search_url(query)
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except (httpx.HTTPError, ET.ParseError):
            return []

        ns = {"tor": "http://torznab.com/schemas/2015/feed"}
        items: list[dict[str, Any]] = []
        for item in root.findall(".//item"):
            magnet = None
            enclosure = item.find("enclosure")
            if enclosure is not None and enclosure.get("url", "").startswith("magnet:"):
                magnet = enclosure.get("url")
            link = item.find("link")
            if not magnet and link is not None and (link.text or "").startswith("magnet:"):
                magnet = link.text
            if not magnet:
                for attr in item.findall("tor:attr", ns):
                    if attr.get("name") == "magneturl":
                        magnet = attr.get("value")
                        break
            if not magnet:
                continue
            item_title = (item.findtext("title") or "").strip()
            size = 0
            seeders = 0
            for attr in item.findall("tor:attr", ns):
                name = attr.get("name", "")
                val = attr.get("value", "0")
                if name == "size":
                    size = _parse_size(val)
                elif name == "seeders":
                    try:
                        seeders = int(val)
                    except ValueError:
                        seeders = 0
            items.append(
                {
                    "title": item_title,
                    "magnet": magnet,
                    "size": size,
                    "seeders": seeders,
                }
            )
        return items

    async def search_episode_best(
        self,
        series_title: str,
        season: int,
        episode: int,
        year: int | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        clean_title = normalize_search_title(series_title) or series_title
        queries = build_episode_query_variants(clean_title, season, episode, year)
        best_item: dict[str, Any] | None = None
        best_score = -1.0
        last_query = queries[-1]
        total_raw = 0

        for idx, query in enumerate(queries):
            allow_pack = idx == len(queries) - 1
            items = await self._search_items(query)
            total_raw += len(items)
            for item in items:
                score = _score_episode_item(
                    item["title"],
                    item["size"],
                    item["seeders"],
                    season,
                    episode,
                    series_title=clean_title,
                    allow_season_pack=allow_pack,
                )
                if score > best_score:
                    best_score = score
                    best_item = item
                    last_query = query

        if best_item and best_score > 0:
            log.info(
                "torznab_episode_found",
                series=clean_title[:40],
                season=season,
                episode=episode,
                query=last_query,
                raw_count=total_raw,
                best_score=best_score,
            )
            return best_item, None

        label = f"S{season:02d}E{episode:02d}"
        if total_raw == 0:
            err = f"No indexer results for {label}"
        else:
            err = f"No matching episode torrent for {label}"

        log.warning(
            "torznab_episode_not_found",
            series=clean_title[:40],
            season=season,
            episode=episode,
            queries_tried=queries,
            raw_count=total_raw,
            best_score=best_score,
        )
        return None, err

    async def search_episode_magnet(
        self,
        series_title: str,
        season: int,
        episode: int,
        year: int | None = None,
    ) -> tuple[str | None, str | None]:
        best, err = await self.search_episode_best(
            series_title, season, episode, year=year
        )
        if best:
            return best["magnet"], None
        return None, err

    async def search_movie_best(
        self,
        movie_title: str,
        year: int | None = None,
        *,
        extra_queries: list[str] | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        clean_title = normalize_search_title(movie_title) or movie_title
        queries: list[str] = []
        seen_q: set[str] = set()

        def add_query(q: str) -> None:
            q = q.strip()
            if not q or q in seen_q:
                return
            seen_q.add(q)
            queries.append(q)

        for q in extra_queries or []:
            add_query(q)
        add_query(f"{clean_title} {year} 1080p" if year else f"{clean_title} 1080p")
        add_query(f"{clean_title} {year} WEB-DL" if year else f"{clean_title} WEB-DL")
        add_query(f"{clean_title} {year}" if year else clean_title)
        best_item: dict[str, Any] | None = None
        best_score = -1.0
        last_query = queries[-1]
        total_raw = 0

        for query in queries:
            items = await self._search_items(query)
            total_raw += len(items)
            for item in items:
                if not is_safe_torrent_title(item["title"]):
                    continue
                if item["seeders"] < settings.torrent_min_seeders:
                    continue
                score = _score_item(
                    item["title"], item["size"], item["seeders"], "movie"
                )
                title_norm = _normalize_title_text(clean_title)
                if title_norm and title_norm in _normalize_title_text(item["title"]):
                    score += 100
                if score > best_score:
                    best_score = score
                    best_item = item
                    last_query = query

        if best_item and best_score > 0:
            log.info(
                "torznab_movie_found",
                movie=clean_title[:40],
                query=last_query,
                raw_count=total_raw,
                best_score=best_score,
            )
            return best_item, None

        if total_raw == 0:
            err = f"No indexer results for {clean_title}"
        else:
            err = f"No matching movie torrent for {clean_title}"
        return None, err


_client: TorznabClient | None = None


def get_torznab_client() -> TorznabClient:
    global _client
    if _client is None:
        _client = TorznabClient()
    return _client
