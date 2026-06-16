"""Punto de entrada — Skill #3 Live Sports Proxy."""

from __future__ import annotations

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
from proxy_client import get_proxy_client  # noqa: E402
from skill_telemetry import log, record_error  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = get_proxy_client()
    await client.start()
    log.info("skill_started", port=settings.port)
    yield
    await client.stop()
    log.info("skill_stopped")


app = FastAPI(
    title="SKILL #3 — Live Sports Proxy",
    version="0.1.0",
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
