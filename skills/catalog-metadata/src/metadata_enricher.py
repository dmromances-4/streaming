"""Enriquecimiento batch de metadatos TMDB."""

from __future__ import annotations

import time

from db.repository import CatalogRepository
from skill_telemetry import log
from tmdb_client import get_tmdb_client


class MetadataEnricher:
    def __init__(self, repo: CatalogRepository) -> None:
        self.repo = repo

    async def _apply_tmdb_details(
        self, title_id: str, hit: dict, content_type: str
    ) -> bool:
        tmdb = get_tmdb_client()
        details = await tmdb.get_details(hit["id"], content_type)
        if not details:
            await self.repo.update_title(
                title_id,
                tmdb_status="failed",
                error_message="TMDB: details fetch failed",
            )
            return False

        await self.repo.update_title(
            title_id,
            tmdb_status="resolved",
            tmdb_id=details["tmdb_id"],
            year=details["year"],
            overview=details["overview"],
            poster_url=details["poster_url"],
            backdrop_url=details["backdrop_url"],
            genres=details["genres"],
            cast=details["cast"],
            runtime_minutes=details["runtime_minutes"],
            error_message=None,
        )
        log.info("tmdb_enriched", title_id=title_id, tmdb_id=details["tmdb_id"])
        return True

    async def enrich_by_ids(
        self,
        title_ids: list[str],
        *,
        force_reenrich: bool = False,
    ) -> dict[str, int]:
        tmdb = get_tmdb_client()
        resolved = 0
        failed = 0

        for title_id in title_ids:
            title = await self.repo.get_title(title_id)
            if not title:
                failed += 1
                continue
            if title.get("tmdb_id") and not force_reenrich:
                resolved += 1
                continue

            hit = await tmdb.search(
                title["title"],
                title["content_type"],
                year=title.get("year"),
                tmdb_id=title.get("tmdb_id"),
            )
            if not hit:
                await self.repo.update_title(
                    title_id,
                    tmdb_status="failed",
                    error_message="TMDB: no match",
                )
                failed += 1
                continue

            if await self._apply_tmdb_details(
                title_id, hit, title["content_type"]
            ):
                resolved += 1
            else:
                failed += 1

        return {"resolved": resolved, "failed": failed, "processed": len(title_ids)}

    async def enrich_batch(
        self,
        *,
        limit: int = 100,
        priority_only: bool = False,
    ) -> dict[str, int]:
        tmdb = get_tmdb_client()
        titles = await self.repo.get_pending_tmdb(
            priority_only=priority_only, limit=limit
        )

        resolved = 0
        failed = 0

        for title in titles:
            hit = await tmdb.search(
                title["title"],
                title["content_type"],
                year=title.get("year"),
                tmdb_id=title.get("tmdb_id"),
            )
            if not hit:
                await self.repo.update_title(
                    title["id"],
                    tmdb_status="failed",
                    error_message="TMDB: no match",
                )
                failed += 1
                continue

            if await self._apply_tmdb_details(
                title["id"], hit, title["content_type"]
            ):
                resolved += 1
            else:
                failed += 1

        await self.repo.record_tmdb_sync_run(resolved, failed, len(titles))
        return {"resolved": resolved, "failed": failed, "processed": len(titles)}

    async def enrich_series(self, series_id: str) -> bool:
        series = await self.repo.get_title(series_id)
        if not series:
            from errors import NotFoundError

            raise NotFoundError(f"Series {series_id} not found")
        if series.get("tmdb_id"):
            return True

        tmdb = get_tmdb_client()
        hit = await tmdb.search(
            series["title"],
            series["content_type"],
            year=series.get("year"),
            tmdb_id=series.get("tmdb_id"),
        )
        if not hit:
            await self.repo.update_title(
                series_id,
                tmdb_status="failed",
                error_message="TMDB: no match",
            )
            return False

        return await self._apply_tmdb_details(
            series_id, hit, series["content_type"]
        )


_enricher: MetadataEnricher | None = None


def get_enricher(repo: CatalogRepository) -> MetadataEnricher:
    global _enricher
    if _enricher is None:
        _enricher = MetadataEnricher(repo)
    return _enricher
