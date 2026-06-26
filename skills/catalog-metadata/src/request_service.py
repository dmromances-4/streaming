"""Alta de títulos bajo demanda desde TMDB."""

from __future__ import annotations

from db.repository import CatalogRepository
from episode_sync import get_episode_sync
from errors import InvalidInputError, NotFoundError, UpstreamError
from metadata_enricher import get_enricher
from skill_telemetry import log
from text_utils import make_slug, normalize_title
from tmdb_client import get_tmdb_client


async def request_title_from_tmdb(
    repo: CatalogRepository,
    *,
    tmdb_id: int,
    content_type: str,
) -> dict:
    if content_type not in ("movie", "series"):
        raise InvalidInputError(f"Invalid content_type: {content_type}")

    existing = await repo.get_title_by_tmdb_id(tmdb_id, content_type)
    if existing:
        return existing

    tmdb = get_tmdb_client()
    details = await tmdb.get_details(tmdb_id, content_type)
    if not details or not details.get("title"):
        raise NotFoundError(f"TMDB {content_type} {tmdb_id} not found")

    display_title = details["title"]
    title_id = make_slug(content_type, "request", display_title)
    if await repo.get_title(title_id):
        title_id = f"{title_id}-tmdb{tmdb_id}"[:120]

    row = {
        "id": title_id,
        "content_type": content_type,
        "origin": "request",
        "title": display_title,
        "title_normalized": normalize_title(display_title),
        "tags": ["requested"],
        "priority": 0,
        "notes": f"Requested via TMDB {tmdb_id}",
    }
    inserted = await repo.insert_title(row)
    if not inserted:
        existing = await repo.get_title_by_tmdb_id(tmdb_id, content_type)
        if existing:
            return existing
        raise UpstreamError("Could not insert requested title")

    enricher = get_enricher(repo)
    await enricher.enrich_by_ids([title_id])

    if content_type == "series":
        sync = get_episode_sync(repo)
        await sync.ensure_series_episodes(title_id)

    item = await repo.get_title(title_id)
    if not item:
        raise UpstreamError("Title missing after request")
    log.info("title_requested", title_id=title_id, tmdb_id=tmdb_id)
    return item
