"""Cliente TMDB para enriquecimiento de metadatos."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from config import settings
from errors import UpstreamError
from skill_telemetry import log, record_error

TMDB_BASE = "https://api.themoviedb.org/3"


def _result_year(result: dict[str, Any], content_type: str) -> int | None:
    date = (
        result.get("release_date")
        if content_type == "movie"
        else result.get("first_air_date")
    ) or ""
    return int(date[:4]) if len(date) >= 4 else None


def _pick_search_result(
    results: list[dict[str, Any]], content_type: str, year: int | None
) -> dict[str, Any] | None:
    if not results:
        return None
    if year:
        for result in results:
            if _result_year(result, content_type) == year:
                return result
        for result in results:
            result_year = _result_year(result, content_type)
            if result_year and abs(result_year - year) <= 1:
                return result
    return results[0]


class TmdbClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=TMDB_BASE,
            timeout=20.0,
            params={"api_key": settings.tmdb_api_key, "language": settings.tmdb_language},
        )

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self._client:
            raise UpstreamError("TMDB client not initialized")

        for attempt in range(6):
            resp = await self._client.request(method, path, **kwargs)
            if resp.status_code == 429:
                delay = min(30.0, 2.0 ** attempt)
                log.warning("tmdb_rate_limited", path=path, delay=delay)
                await asyncio.sleep(delay)
                continue
            return resp
        return resp

    async def search(
        self,
        title: str,
        content_type: str,
        *,
        year: int | None = None,
        tmdb_id: int | None = None,
    ) -> dict[str, Any] | None:
        if not settings.tmdb_api_key:
            return None
        if not self._client:
            raise UpstreamError("TMDB client not initialized")

        if tmdb_id:
            return {"id": tmdb_id}

        endpoint = "/search/movie" if content_type == "movie" else "/search/tv"
        try:
            resp = await self._request("GET", endpoint, params={"query": title})
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return _pick_search_result(results, content_type, year)
        except httpx.HTTPError as exc:
            record_error("tmdb_error")
            log.warning("tmdb_search_failed", title=title[:40], error=str(exc))
            return None

    async def get_details(
        self, tmdb_id: int, content_type: str
    ) -> dict[str, Any] | None:
        if not self._client:
            raise UpstreamError("TMDB client not initialized")

        endpoint = f"/movie/{tmdb_id}" if content_type == "movie" else f"/tv/{tmdb_id}"
        credits_ep = f"{endpoint}/credits"

        try:
            detail = (await self._request("GET", endpoint)).json()
            credits = (await self._request("GET", credits_ep)).json()
        except httpx.HTTPError as exc:
            record_error("tmdb_error")
            return None

        cast = [
            c.get("name", "")
            for c in credits.get("cast", [])[:5]
            if c.get("name")
        ]
        genres = [g.get("name", "") for g in detail.get("genres", []) if g.get("name")]

        year = None
        if content_type == "movie":
            date = detail.get("release_date") or ""
            year = int(date[:4]) if len(date) >= 4 else None
        else:
            date = detail.get("first_air_date") or ""
            year = int(date[:4]) if len(date) >= 4 else None

        poster = detail.get("poster_path")
        backdrop = detail.get("backdrop_path")
        img_base = settings.tmdb_image_base.rstrip("/")

        return {
            "tmdb_id": tmdb_id,
            "title": detail.get("title") or detail.get("name"),
            "year": year,
            "overview": detail.get("overview"),
            "poster_url": f"{img_base}{poster}" if poster else None,
            "backdrop_url": f"{img_base}{backdrop}" if backdrop else None,
            "genres": genres,
            "cast": cast,
            "runtime_minutes": detail.get("runtime") if content_type == "movie" else None,
            "number_of_seasons": detail.get("number_of_seasons"),
        }

    async def get_tv_detail(self, tmdb_id: int) -> dict[str, Any] | None:
        return await self.get_details(tmdb_id, "series")

    async def get_season_episodes(
        self, tmdb_id: int, season_number: int
    ) -> list[dict[str, Any]]:
        if not settings.tmdb_api_key:
            return []
        if not self._client:
            raise UpstreamError("TMDB client not initialized")

        try:
            resp = await self._request(
                "GET", f"/tv/{tmdb_id}/season/{season_number}"
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            record_error("tmdb_error")
            log.warning(
                "tmdb_season_failed",
                tmdb_id=tmdb_id,
                season=season_number,
                error=str(exc),
            )
            return []

        img_base = settings.tmdb_image_base.rstrip("/")
        episodes: list[dict[str, Any]] = []
        for ep in data.get("episodes", []):
            still = ep.get("still_path")
            episodes.append(
                {
                    "season_number": season_number,
                    "episode_number": ep.get("episode_number"),
                    "title": ep.get("name"),
                    "overview": ep.get("overview"),
                    "runtime_minutes": ep.get("runtime"),
                    "tmdb_episode_id": ep.get("id"),
                    "still_url": f"{img_base}{still}" if still else None,
                }
            )
        return episodes

    async def search_results(
        self,
        query: str,
        content_type: str | None = None,
        *,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        if not settings.tmdb_api_key:
            return []
        if not self._client:
            raise UpstreamError("TMDB client not initialized")

        types = (
            [content_type]
            if content_type in ("movie", "series")
            else ["movie", "series"]
        )
        img_base = settings.tmdb_image_base.rstrip("/")
        merged: list[dict[str, Any]] = []

        for ct in types:
            endpoint = "/search/movie" if ct == "movie" else "/search/tv"
            try:
                resp = await self._request("GET", endpoint, params={"query": query})
                resp.raise_for_status()
                results = resp.json().get("results", [])[:limit]
            except httpx.HTTPError as exc:
                log.warning("tmdb_search_failed", query=query[:40], type=ct, error=str(exc))
                continue

            for result in results:
                poster = result.get("poster_path")
                backdrop = result.get("backdrop_path")
                merged.append(
                    {
                        "tmdb_id": int(result["id"]),
                        "content_type": ct,
                        "title": result.get("title") or result.get("name") or "",
                        "year": _result_year(result, ct),
                        "overview": result.get("overview"),
                        "poster_url": f"{img_base}{poster}" if poster else None,
                        "backdrop_url": f"{img_base}{backdrop}" if backdrop else None,
                    }
                )

        return merged[:limit]


_client: TmdbClient | None = None


def get_tmdb_client() -> TmdbClient:
    global _client
    if _client is None:
        _client = TmdbClient()
    return _client
