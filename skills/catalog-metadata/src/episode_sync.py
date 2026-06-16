"""Sincronización de episodios desde TMDB."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from episode_utils import make_episode_id  # noqa: E402

from db.repository import CatalogRepository  # noqa: E402
from errors import InvalidInputError, NotFoundError  # noqa: E402
from skill_telemetry import log  # noqa: E402
from tmdb_client import get_tmdb_client  # noqa: E402


class EpisodeSync:
    def __init__(self, repo: CatalogRepository) -> None:
        self.repo = repo

    async def sync_series_episodes(self, series_id: str) -> dict[str, int]:
        series = await self.repo.get_title(series_id)
        if not series:
            raise NotFoundError(f"Series {series_id} not found")
        if series.get("content_type") != "series":
            raise InvalidInputError("Title is not a series")

        tmdb_id = series.get("tmdb_id")
        if not tmdb_id:
            raise InvalidInputError(
                "Series has no tmdb_id — run enrich-metadata first"
            )

        tmdb = get_tmdb_client()
        detail = await tmdb.get_tv_detail(tmdb_id)
        if not detail:
            raise InvalidInputError("Could not fetch series detail from TMDB")

        seasons = detail.get("number_of_seasons") or 0
        inserted = 0
        updated = 0
        skipped = 0

        for season_num in range(1, seasons + 1):
            eps = await tmdb.get_season_episodes(tmdb_id, season_num)
            for ep in eps:
                ep_num = ep.get("episode_number")
                if not ep_num:
                    skipped += 1
                    continue
                row = {
                    "id": make_episode_id(series_id, season_num, ep_num),
                    "series_id": series_id,
                    "season_number": season_num,
                    "episode_number": ep_num,
                    "title": ep.get("title"),
                    "overview": ep.get("overview"),
                    "runtime_minutes": ep.get("runtime_minutes"),
                    "tmdb_episode_id": ep.get("tmdb_episode_id"),
                    "still_url": ep.get("still_url"),
                }
                if await self.repo.upsert_episode(row):
                    inserted += 1
                else:
                    updated += 1

        log.info(
            "episodes_synced",
            series_id=series_id,
            inserted=inserted,
            updated=updated,
            skipped=skipped,
        )
        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "processed": inserted + updated + skipped,
        }

    async def ensure_series_episodes(self, series_id: str) -> dict[str, Any]:
        from metadata_enricher import get_enricher

        series = await self.repo.get_title(series_id)
        if not series:
            raise NotFoundError(f"Series {series_id} not found")
        if series.get("content_type") != "series":
            raise InvalidInputError("Title is not a series")

        enriched = False
        if not series.get("tmdb_id"):
            enricher = get_enricher(self.repo)
            enriched = await enricher.enrich_series(series_id)

        existing = await self.repo.count_episodes(series_id)
        if existing > 0 and not enriched:
            return {
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "processed": existing,
                "already_synced": True,
            }

        result = await self.sync_series_episodes(series_id)
        result["already_synced"] = False
        return result


_sync: EpisodeSync | None = None


def get_episode_sync(repo: CatalogRepository) -> EpisodeSync:
    global _sync
    if _sync is None:
        _sync = EpisodeSync(repo)
    return _sync
