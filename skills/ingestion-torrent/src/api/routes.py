"""Rutas HTTP del Skill #1."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi import APIRouter, Header, Query, Request, Response
from fastapi.responses import StreamingResponse
from prometheus_client import generate_latest

# Paths para imports compartidos
_shared = Path(__file__).resolve().parents[4] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from errors import NotFoundError, SkillError  # noqa: E402

from api.schemas import (  # noqa: E402
    ErrorResponse,
    IngestRequest,
    IngestResponse,
    StatusResponse,
)
from config import settings  # noqa: E402
from skill_telemetry import ingest_duration_seconds, log, record_error  # noqa: E402
from stream_reader import SequentialStreamReader, parse_range_header  # noqa: E402
from torrent_engine import get_engine  # noqa: E402

router = APIRouter()
health_router = APIRouter()


@health_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "skill": settings.skill_name}


@health_router.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest) -> IngestResponse:
    engine = get_engine()
    start = time.monotonic()

    try:
        session = await engine.create_session(
            request.magnet_uri,
            season_number=request.season_number,
            episode_number=request.episode_number,
        )
    except SkillError:
        raise

    info_hash = None
    if session.handle.is_valid():
        info_hash = str(session.handle.info_hash())

    log.info(
        "ingest_started",
        session_id=session.session_id,
        magnet=request.magnet_uri[:80],
    )

    # Esperar metadata brevemente (no bloqueante para respuesta)
    name = "pending_metadata"
    size_bytes = 0
    if session.handle.has_metadata():
        ti = session.handle.torrent_file()
        name = session.handle.name()
        size_bytes = sum(ti.file_size(i) for i in range(ti.num_files()))

    ingest_duration_seconds.observe(time.monotonic() - start)

    return IngestResponse(
        session_id=session.session_id,
        name=name,
        size_bytes=size_bytes,
        info_hash=info_hash,
    )


@router.get("/status/{session_id}", response_model=StatusResponse)
async def status(session_id: str) -> StatusResponse:
    engine = get_engine()
    data = await engine.get_status(session_id)
    return StatusResponse(
        session_id=data["session_id"],
        name=data["name"],
        state=data["state"],
        progress=data["progress"],
        download_rate_bps=data["download_rate_bps"],
        upload_rate_bps=data.get("upload_rate_bps", 0),
        num_peers=data.get("num_peers", 0),
        size_bytes=data["size_bytes"],
        bytes_streamed=data["bytes_streamed"],
        files=data.get("files", []),
    )


@router.get("/stream/{session_id}")
async def stream(
    session_id: str,
    request: Request,
    range_header: str | None = Header(None, alias="Range"),
    season: int | None = Query(None, ge=1),
    episode: int | None = Query(None, ge=1),
) -> StreamingResponse:
    engine = get_engine()
    session = await engine.get_session(session_id)

    # Esperar metadata si aún no está
    if not session.handle.has_metadata():
        try:
            await session._wait_metadata()
        except Exception as exc:
            record_error("metadata_timeout")
            raise

    file_index = engine.pick_file_for_session(
        session, season=season, episode=episode
    )
    reader = SequentialStreamReader(
        session,
        file_index,
        peer_timeout_seconds=settings.peer_timeout_seconds,
    )

    file_size = reader.file_size
    if file_size == 0:
        record_error("empty_file")
        raise NotFoundError("No streamable file yet")

    byte_range = parse_range_header(range_header, file_size)
    status_code = 200
    content_length: int | None = file_size
    headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Content-Type": reader.mime_type,
        "Content-Disposition": f'inline; filename="{reader.file_name}"',
    }

    start = 0
    end = file_size - 1

    if byte_range:
        start, end = byte_range
        status_code = 206
        content_length = end - start + 1
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        headers["Content-Length"] = str(content_length)
        reader.seek(start)
    else:
        headers["Content-Length"] = str(file_size)

    async def generate():
        try:
            async for chunk in reader.read_chunks(start=start, end=end):
                if await request.is_disconnected():
                    log.info("client_disconnected", session_id=session_id)
                    break
                yield chunk
        finally:
            reader.close()

    log.info(
        "stream_started",
        session_id=session_id,
        file=reader.file_name,
        range=f"{start}-{end}",
    )

    return StreamingResponse(
        generate(),
        status_code=status_code,
        headers=headers,
        media_type=reader.mime_type,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str) -> Response:
    engine = get_engine()
    await engine.remove_session(session_id)
    log.info("session_deleted", session_id=session_id)
    return Response(status_code=204)
