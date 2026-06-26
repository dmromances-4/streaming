"""Rutas HTTP Skill #6."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Query, Response
from prometheus_client import generate_latest

_shared = Path(__file__).resolve().parents[4] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from api.schemas import (  # noqa: E402
    BatchIngestRequest,
    BatchResult,
    CatalogItem,
    CatalogListResponse,
    CocktailItem,
    EnrichMetadataRequest,
    EpisodeItem,
    EpisodeListResponse,
    EpisodeAcquireResponse,
    EpisodePlayResponse,
    EpisodeStatusResponse,
    TitleAcquireResponse,
    TitlePlayResponse,
    TitleStatusResponse,
    ImportRequest,
    ImportResponse,
    MagnetOverride,
    ResolveRequest,
    ResolveSeasonRequest,
    SeasonSummary,
    SystemStatusResponse,
    RequestTitleBody,
    TmdbSearchResponse,
    TmdbSearchResult,
    BulkAcquireRequest,
    BulkAcquireResponse,
    BulkAcquireStatusResponse,
)
from bulk_watchlist_agent import get_bulk_agent  # noqa: E402
from cocktail_importer import import_cocktails_dir  # noqa: E402
from config import settings  # noqa: E402
from db.repository import get_repository  # noqa: E402
from errors import NotFoundError  # noqa: E402
from episode_sync import get_episode_sync  # noqa: E402
from ingest_orchestrator import get_orchestrator  # noqa: E402
from media_library import build_media_manifest_url, probe_episode_media  # noqa: E402
from metadata_enricher import get_enricher  # noqa: E402
from request_service import request_title_from_tmdb  # noqa: E402
from seed_importer import import_seed_dir  # noqa: E402
from tmdb_client import get_tmdb_client  # noqa: E402
from skill_telemetry import log, titles_priority, titles_ready  # noqa: E402
from system_status import get_system_status  # noqa: E402

router = APIRouter()
health_router = APIRouter()


@health_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "skill": settings.skill_name}


@health_router.get("/metrics")
async def metrics() -> Response:
    repo = get_repository()
    stats = await repo.get_stats()
    titles_ready.set(stats.get("ready", 0))
    titles_priority.set(stats.get("cocteleria", 0))
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/search/tmdb", response_model=TmdbSearchResponse)
async def search_tmdb(
    q: str = Query(..., min_length=2),
    type: str | None = Query(None, alias="type"),
) -> TmdbSearchResponse:
    content_type = type if type in ("movie", "series") else None
    tmdb = get_tmdb_client()
    results = await tmdb.search_results(q, content_type, limit=12)
    items = [TmdbSearchResult(**r) for r in results]
    return TmdbSearchResponse(items=items, total=len(items))


@router.post("/request", response_model=CatalogItem)
async def request_title(body: RequestTitleBody) -> CatalogItem:
    repo = get_repository()
    item = await request_title_from_tmdb(
        repo,
        tmdb_id=body.tmdb_id,
        content_type=body.content_type,
    )
    return CatalogItem(**item)


@router.post("/import", response_model=ImportResponse)
async def import_seed(request: ImportRequest) -> ImportResponse:
    repo = get_repository()
    if request.source != "seed":
        from errors import InvalidInputError

        raise InvalidInputError(f"Unknown source: {request.source}")

    result = await import_seed_dir(repo)
    await import_cocktails_dir(repo)
    log.info("catalog_imported", **result)
    return ImportResponse(**result)


def _subtitle_url(subtitle_path: str | None) -> str | None:
    if not subtitle_path:
        return None
    return build_media_manifest_url(subtitle_path)


def _episode_to_item(episode: dict) -> EpisodeItem:
    return EpisodeItem(
        id=episode["id"],
        series_id=episode["series_id"],
        season_number=episode["season_number"],
        episode_number=episode["episode_number"],
        title=episode.get("title"),
        overview=episode.get("overview"),
        runtime_minutes=episode.get("runtime_minutes"),
        magnet_status=episode["magnet_status"],
        pipeline_status=episode["pipeline_status"],
        manifest_url=episode.get("manifest_url"),
        ingest_mode=episode.get("ingest_mode"),
        error_message=episode.get("error_message"),
        has_local_media=bool(episode.get("source_path")),
        still_url=episode.get("still_url"),
        subtitle_path=_subtitle_url(episode.get("subtitle_path")),
    )


@router.post("/enrich-metadata", response_model=BatchResult)
async def enrich_metadata(body: EnrichMetadataRequest) -> BatchResult:
    repo = get_repository()
    enricher = get_enricher(repo)
    if body.title_ids:
        result = await enricher.enrich_by_ids(
            body.title_ids,
            force_reenrich=body.force_reenrich,
        )
    else:
        result = await enricher.enrich_batch(
            limit=body.limit,
            priority_only=body.priority_only,
        )
    return BatchResult(
        resolved=result["resolved"],
        failed=result["failed"],
        processed=result["processed"],
    )


@router.get("/system/status", response_model=SystemStatusResponse)
async def system_status() -> SystemStatusResponse:
    result = await get_system_status()
    return SystemStatusResponse(**result)


@router.get("/catalog/local-library", response_model=CatalogListResponse)
async def list_local_library(
    limit: int = Query(20, ge=1, le=100),
) -> CatalogListResponse:
    repo = get_repository()
    items = await repo.list_titles_with_local_media(limit=limit)
    return CatalogListResponse(
        items=[CatalogItem(**i) for i in items],
        total=len(items),
        limit=limit,
        offset=0,
    )


@router.get("/catalog/genres/top")
async def top_genres(limit: int = Query(6, ge=1, le=20)) -> dict[str, list[str]]:
    repo = get_repository()
    return {"genres": await repo.list_top_genres(limit=limit)}


@router.get("/catalog", response_model=CatalogListResponse)
async def list_catalog(
    type: str | None = Query(None, alias="type"),
    origin: str | None = None,
    cocteleria: int | None = Query(None),
    status: str | None = Query(None, alias="status"),
    ingredient: str | None = None,
    genre: str | None = None,
    without_local: int | None = Query(None),
    q: str | None = Query(None, min_length=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> CatalogListResponse:
    repo = get_repository()

    if ingredient:
        items = await repo.list_titles_by_ingredient(ingredient, limit=limit)
        total = len(items)
    else:
        items = await repo.list_titles(
            content_type=type,
            origin=origin,
            cocteleria=bool(cocteleria) if cocteleria else None,
            pipeline_status=status,
            query=q,
            genre=genre,
            without_local=bool(without_local) if without_local else None,
            limit=limit,
            offset=offset,
        )
        total = await repo.count_titles(
            content_type=type,
            origin=origin,
            cocteleria=bool(cocteleria) if cocteleria else None,
            pipeline_status=status,
            query=q,
            genre=genre,
            without_local=bool(without_local) if without_local else None,
        )

    return CatalogListResponse(
        items=[CatalogItem(**i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/catalog/{title_id}", response_model=CatalogItem)
async def get_catalog_item(title_id: str) -> CatalogItem:
    repo = get_repository()
    item = await repo.get_title(title_id)
    if not item:
        raise NotFoundError(f"Title {title_id} not found")
    return CatalogItem(**item)


@router.get("/catalog/{title_id}/similar", response_model=CatalogListResponse)
async def similar_titles(
    title_id: str,
    limit: int = Query(12, ge=1, le=30),
) -> CatalogListResponse:
    repo = get_repository()
    if not await repo.get_title(title_id):
        raise NotFoundError(f"Title {title_id} not found")
    items = await repo.find_similar_titles(title_id, limit=limit)
    return CatalogListResponse(
        items=[CatalogItem(**i) for i in items],
        total=len(items),
        limit=limit,
        offset=0,
    )


@router.get("/downloads/active")
async def active_downloads() -> dict:
    repo = get_repository()
    items = await repo.list_active_downloads()
    return {"items": items, "total": len(items)}


@router.get("/catalog/{title_id}/cocktails", response_model=list[CocktailItem])
async def get_title_cocktails(title_id: str) -> list[CocktailItem]:
    repo = get_repository()
    item = await repo.get_title(title_id)
    if not item:
        raise NotFoundError(f"Title {title_id} not found")
    cocktails = await repo.get_cocktails_for_title(title_id)
    return [CocktailItem(**c) for c in cocktails]


@router.get("/cocktails", response_model=list[CocktailItem])
async def list_cocktails(
    ingredient: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[CocktailItem]:
    repo = get_repository()
    items = await repo.list_cocktails_by_ingredient(ingredient, limit=limit)
    return [CocktailItem(**c) for c in items]


@router.get("/cocktails/ingredients")
async def list_ingredients() -> dict[str, list[str]]:
    repo = get_repository()
    return {"ingredients": await repo.list_cocktail_ingredients()}


@router.post("/catalog/{title_id}/magnet")
async def set_magnet(title_id: str, body: MagnetOverride) -> dict[str, str]:
    repo = get_repository()
    item = await repo.get_title(title_id)
    if not item:
        raise NotFoundError(f"Title {title_id} not found")

    await repo.update_title(
        title_id,
        magnet_uri=body.magnet_uri,
        magnet_status="resolved",
        magnet_source="manual",
        pipeline_status="catalog",
        error_message=None,
    )
    return {"status": "ok", "title_id": title_id}


@router.post("/resolve-magnets", response_model=BatchResult)
async def resolve_magnets(body: ResolveRequest) -> BatchResult:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.resolve_magnets(
        priority_only=body.priority_only,
        limit=body.limit,
    )
    return BatchResult(**result)


@router.post("/batch-ingest", response_model=BatchResult)
async def batch_ingest(body: BatchIngestRequest) -> BatchResult:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.batch_ingest(
        priority_only=body.priority_only,
        limit=body.limit,
        concurrency=body.concurrency,
    )
    return BatchResult(**result)


@router.post("/bulk-acquire", response_model=BulkAcquireResponse)
async def bulk_acquire(body: BulkAcquireRequest) -> BulkAcquireResponse:
    repo = get_repository()
    orch = get_orchestrator(repo)
    agent = get_bulk_agent(repo, orch)

    enrich_result = None
    if body.enrich_first and not body.dry_run and body.content_type == "movie":
        enrich_result = await agent.enrich_all_movies()

    if body.content_type != "movie":
        from errors import InvalidInputError

        raise InvalidInputError("Only movie bulk acquire is supported in phase 1")

    result = await agent.acquire_movies(
        origin=body.origin,
        limit=body.limit,
        concurrency=body.concurrency,
        dry_run=body.dry_run,
    )
    if enrich_result:
        result["enrich"] = enrich_result
    return BulkAcquireResponse(**result)


@router.get("/bulk-acquire/status", response_model=BulkAcquireStatusResponse)
async def bulk_acquire_status(
    run_id: int | None = Query(None),
) -> BulkAcquireStatusResponse:
    repo = get_repository()
    orch = get_orchestrator(repo)
    agent = get_bulk_agent(repo, orch)
    status = await agent.get_status(run_id=run_id)
    return BulkAcquireStatusResponse(**status)


@router.get("/stats")
async def stats() -> dict:
    repo = get_repository()
    return await repo.get_stats()


@router.post("/catalog/{series_id}/sync-episodes", response_model=BatchResult)
async def sync_episodes(series_id: str) -> BatchResult:
    repo = get_repository()
    sync = get_episode_sync(repo)
    result = await sync.sync_series_episodes(series_id)
    return BatchResult(
        inserted=result["inserted"],
        updated=result["updated"],
        skipped=result["skipped"],
        processed=result["processed"],
    )


@router.post("/catalog/{series_id}/ensure-episodes", response_model=BatchResult)
async def ensure_episodes(series_id: str) -> BatchResult:
    repo = get_repository()
    sync = get_episode_sync(repo)
    result = await sync.ensure_series_episodes(series_id)
    return BatchResult(
        inserted=result.get("inserted"),
        updated=result.get("updated"),
        skipped=result.get("skipped"),
        processed=result.get("processed", 0),
    )


@router.get("/catalog/{series_id}/seasons", response_model=list[SeasonSummary])
async def list_seasons(series_id: str) -> list[SeasonSummary]:
    repo = get_repository()
    item = await repo.get_title(series_id)
    if not item:
        raise NotFoundError(f"Series {series_id} not found")
    summaries = await repo.list_season_summaries(series_id)
    return [SeasonSummary(**s) for s in summaries]


@router.get("/catalog/{series_id}/episodes", response_model=EpisodeListResponse)
async def list_episodes(
    series_id: str,
    season: int | None = Query(None),
) -> EpisodeListResponse:
    repo = get_repository()
    item = await repo.get_title(series_id)
    if not item:
        raise NotFoundError(f"Series {series_id} not found")
    episodes = await repo.list_episodes(series_id, season_number=season)
    total = await repo.count_episodes(series_id, season_number=season)
    return EpisodeListResponse(
        items=[_episode_to_item(e) for e in episodes],
        total=total,
        season=season,
    )


@router.get("/episodes/{episode_id}", response_model=EpisodeItem)
async def get_episode(episode_id: str) -> EpisodeItem:
    repo = get_repository()
    episode = await repo.get_episode(episode_id)
    if not episode:
        raise NotFoundError(f"Episode {episode_id} not found")
    return _episode_to_item(episode)


@router.post("/episodes/{episode_id}/resolve-magnet")
async def resolve_episode_magnet(episode_id: str) -> dict[str, str]:
    repo = get_repository()
    orch = get_orchestrator(repo)
    return await orch.resolve_episode_magnet(episode_id)


@router.post("/catalog/{series_id}/resolve-episodes", response_model=BatchResult)
async def resolve_episodes_batch(
    series_id: str, body: ResolveSeasonRequest
) -> BatchResult:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.resolve_episodes_batch(
        series_id=series_id,
        season_number=body.season_number,
        limit=body.limit,
    )
    return BatchResult(**result)


@router.post("/episodes/{episode_id}/play", response_model=EpisodePlayResponse)
async def play_episode(episode_id: str) -> EpisodePlayResponse:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.play_episode(episode_id)
    return EpisodePlayResponse(**result)


@router.post("/episodes/{episode_id}/acquire", response_model=EpisodeAcquireResponse)
async def acquire_episode(episode_id: str) -> EpisodeAcquireResponse:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.acquire_episode(episode_id)
    return EpisodeAcquireResponse(**result)


@router.post("/catalog/{title_id}/acquire", response_model=TitleAcquireResponse)
async def acquire_title(title_id: str) -> TitleAcquireResponse:
    repo = get_repository()
    orch = get_orchestrator(repo)
    title = await repo.get_title(title_id)
    if not title:
        raise NotFoundError(f"Title {title_id} not found")
    if title.get("content_type") == "movie":
        result = await orch.acquire_movie(title_id)
    else:
        from errors import InvalidInputError

        raise InvalidInputError("Use /episodes/{id}/acquire for series episodes")
    return TitleAcquireResponse(**result)


@router.post("/catalog/{series_id}/request-season", response_model=BatchResult)
async def request_season(
    series_id: str,
    season: int = Query(..., ge=1),
) -> BatchResult:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.request_season(series_id, season)
    return BatchResult(**result)


@router.post("/catalog/{title_id}/play", response_model=TitlePlayResponse)
async def play_title(title_id: str) -> TitlePlayResponse:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.play_movie(title_id)
    return TitlePlayResponse(**result)


@router.get("/catalog/{title_id}/status", response_model=TitleStatusResponse)
async def title_status(title_id: str) -> TitleStatusResponse:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.get_title_status(title_id)
    return TitleStatusResponse(**result)


@router.post("/catalog/{series_id}/scan-library", response_model=BatchResult)
async def scan_series_library(series_id: str) -> BatchResult:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.scan_series_library(series_id)
    return BatchResult(**result)


@router.post("/catalog/{title_id}/scan-movie", response_model=BatchResult)
async def scan_movie_library(title_id: str) -> BatchResult:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.scan_movie_library(title_id)
    return BatchResult(**result)


@router.post("/catalog/scan-all-library", response_model=BatchResult)
async def scan_all_library() -> BatchResult:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.scan_all_library()
    return BatchResult(**result)


@router.get("/catalog/{series_id}/episodes/{season}/{episode}/probe")
async def probe_episode(
    series_id: str,
    season: int,
    episode: int,
) -> dict:
    repo = get_repository()
    series = await repo.get_title(series_id)
    if not series:
        raise NotFoundError(f"Series {series_id} not found")
    from episode_utils import make_episode_id

    episode_id = make_episode_id(series_id, season, episode)
    ep = await repo.get_episode(episode_id)
    return probe_episode_media(
        series_id=series_id,
        series_title=series["title"],
        season=season,
        episode=episode,
        stored_path=ep.get("source_path") if ep else None,
    )


@router.get("/episodes/{episode_id}/status", response_model=EpisodeStatusResponse)
async def episode_status(episode_id: str) -> EpisodeStatusResponse:
    repo = get_repository()
    orch = get_orchestrator(repo)
    result = await orch.get_episode_status(episode_id)
    return EpisodeStatusResponse(**result)
