"""Punto de entrada — Skill #6 Catalog Metadata."""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

_src = Path(__file__).resolve().parent
_shared = _src.parents[2] / "shared" / "python"
for p in (str(_src), str(_shared)):
    if p not in sys.path:
        sys.path.insert(0, p)

from errors import SkillError  # noqa: E402

from api.routes import health_router, router  # noqa: E402
from config import settings  # noqa: E402
from db.repository import get_repository  # noqa: E402
from episode_sync import get_episode_sync  # noqa: E402
from ingest_orchestrator import get_orchestrator  # noqa: E402
from qbittorrent_client import get_qbittorrent_client  # noqa: E402
from skill_telemetry import log, record_error  # noqa: E402
from tmdb_client import get_tmdb_client  # noqa: E402
from torznab_client import get_torznab_client  # noqa: E402
from yts_client import get_yts_client  # noqa: E402


async def _library_bootstrap_task(repo, orch) -> None:
    series_ids = settings.bootstrap_series_id_list
    if not series_ids:
        return
    sync = get_episode_sync(repo)
    for series_id in series_ids:
        try:
            await sync.ensure_series_episodes(series_id)
            await orch.scan_series_library(series_id)
            log.info("library_bootstrap_done", series_id=series_id)
        except Exception as exc:
            log.warning(
                "library_bootstrap_failed",
                series_id=series_id,
                error=str(exc),
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo = get_repository()
    await repo.init()
    torznab = get_torznab_client()
    await torznab.start()
    tmdb = get_tmdb_client()
    await tmdb.start()
    yts = get_yts_client()
    await yts.start()
    qbit = get_qbittorrent_client()
    await qbit.start()
    orch = get_orchestrator(repo)
    await orch.start()
    if settings.bootstrap_series_id_list:
        asyncio.create_task(_library_bootstrap_task(repo, orch))
    log.info("skill_started", port=settings.port, indexer=settings.indexer_provider)
    yield
    await orch.stop()
    await qbit.stop()
    await yts.stop()
    await tmdb.stop()
    await torznab.stop()
    log.info("skill_stopped")


app = FastAPI(
    title="SKILL #6 — Catalog Metadata",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(router, prefix="/api/v1")


@app.exception_handler(SkillError)
async def skill_error_handler(request: Request, exc: SkillError) -> JSONResponse:
    record_error(exc.error_type)
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error": exc.message,
            "error_type": exc.error_type,
            "details": exc.details,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port)
