"""Búsqueda pública de torrents de películas vía YTS (sin API key)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import httpx

from config import settings
from skill_telemetry import log
from torznab_client import _normalize_title_text, is_safe_torrent_title, normalize_search_title

YTS_MIRRORS = (
    "https://yts.am/api/v2",
    "https://yts.lt/api/v2",
    "https://yts.mx/api/v2",
)


class YtsClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._base_url: str = YTS_MIRRORS[0]

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(25.0),
            headers={"User-Agent": "streaming-catalog/1.0"},
            follow_redirects=True,
        )

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_movie_best(
        self,
        movie_title: str,
        year: int | None = None,
        *,
        extra_queries: list[str] | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not settings.torrent_enable_yts_fallback:
            return None, "YTS fallback desactivado"

        clean = normalize_search_title(movie_title) or movie_title
        queries: list[str] = []
        seen: set[str] = set()

        def add(q: str) -> None:
            q = q.strip()
            if not q or q in seen:
                return
            seen.add(q)
            queries.append(q)

        for q in extra_queries or []:
            add(q)
        add(clean)
        if year:
            add(f"{clean} {year}")

        best_item: dict[str, Any] | None = None
        best_score = -1.0
        last_err = "Sin resultados en YTS"

        for query in queries:
            item, err = await self._search_one(query, clean, year)
            if item:
                score = float(item.get("_score", 0))
                if score > best_score:
                    best_score = score
                    best_item = item
            if err:
                last_err = err

        if best_item:
            best_item.pop("_score", None)
            log.info(
                "yts_movie_found",
                movie=clean[:40],
                torrent=best_item["title"][:80],
                seeders=best_item.get("seeders"),
            )
            return best_item, None
        return None, last_err

    async def _search_one(
        self,
        query: str,
        clean_title: str,
        year: int | None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not self._client:
            return None, "Cliente YTS no inicializado"

        last_err = "Sin resultados en YTS"
        for base in YTS_MIRRORS:
            try:
                resp = await self._client.get(
                    f"{base}/list_movies.json",
                    params={"query_term": query, "limit": 20},
                )
                resp.raise_for_status()
                payload = resp.json()
                self._base_url = base
            except httpx.HTTPError as exc:
                last_err = f"YTS error ({base}): {exc}"
                continue

            movies = (payload.get("data") or {}).get("movies") or []
            if not movies:
                last_err = f"YTS sin resultados para {query}"
                continue

            title_norm = _normalize_title_text(clean_title)
            best: dict[str, Any] | None = None
            best_score = -1.0

            for movie in movies:
                movie_title = movie.get("title") or ""
                movie_year = movie.get("year")
                if year and movie_year and abs(int(movie_year) - year) > 1:
                    continue
                torrents = movie.get("torrents") or []
                for torrent in torrents:
                    quality = (torrent.get("quality") or "").lower()
                    seeds = int(torrent.get("seeds") or 0)
                    if seeds < max(1, settings.torrent_min_seeders // 2):
                        continue
                    info_hash = (torrent.get("hash") or "").strip()
                    if not info_hash:
                        continue
                    label = f"{movie_title} {quality} {movie_year or ''}".strip()
                    if not is_safe_torrent_title(label):
                        continue
                    score = seeds * 10.0
                    if quality == "1080p":
                        score += 50
                    elif quality == "720p":
                        score += 20
                    if title_norm and title_norm in _normalize_title_text(movie_title):
                        score += 120
                    if year and movie_year == year:
                        score += 40
                    if score > best_score:
                        size_bytes = int(torrent.get("size_bytes") or 0)
                        if not size_bytes:
                            size_str = torrent.get("size") or ""
                            m = re.search(r"([\d.]+)\s*GB", str(size_str), re.I)
                            if m:
                                size_bytes = int(float(m.group(1)) * 1024**3)
                        best_score = score
                        best = {
                            "title": label,
                            "magnet": (
                                f"magnet:?xt=urn:btih:{info_hash}"
                                f"&dn={quote(movie_title)}"
                            ),
                            "size": size_bytes,
                            "seeders": seeds,
                            "_score": score,
                        }

            if best:
                return best, None

        return None, last_err


_client: YtsClient | None = None


def get_yts_client() -> YtsClient:
    global _client
    if _client is None:
        _client = YtsClient()
    return _client
