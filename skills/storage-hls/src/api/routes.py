"""Rutas HTTP del Skill #2."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
from prometheus_client import generate_latest

_shared = Path(__file__).resolve().parents[4] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from api.schemas import JobStatusResponse, TranscodeRequest, TranscodeResponse  # noqa: E402
from config import settings  # noqa: E402
from job_manager import get_manager  # noqa: E402
from s3_client import get_object_stream  # noqa: E402
from skill_telemetry import log  # noqa: E402

router = APIRouter()
health_router = APIRouter()

_SEGMENT_MEDIA_TYPE = "video/mp2t"


@health_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "skill": settings.skill_name}


@health_router.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.post("/transcode", response_model=TranscodeResponse)
async def transcode(request: TranscodeRequest) -> TranscodeResponse:
    manager = get_manager()
    job = await manager.create_job(
        session_id=request.session_id,
        source_url=request.source_url,
        source_type=request.source_type,
        season_number=request.season_number,
        episode_number=request.episode_number,
    )
    manifest_url = f"{settings.public_api_base.rstrip('/')}/api/v1/manifest/{job.job_id}"
    log.info("transcode_requested", job_id=job.job_id)
    return TranscodeResponse(
        job_id=job.job_id,
        state=job.state.value,
        manifest_url=manifest_url,
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def job_status(job_id: str) -> JobStatusResponse:
    manager = get_manager()
    data = await manager.get_status(job_id)
    return JobStatusResponse(**data)


@router.get("/manifest/{job_id}")
async def get_manifest(job_id: str) -> Response:
    manager = get_manager()
    content = await manager.get_manifest_from_s3(job_id)
    return Response(
        content=content,
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/segments/{job_id}/{filename}")
async def get_segment(job_id: str, filename: str, request: Request) -> StreamingResponse:
    manager = get_manager()
    s3_key = await manager.get_segment_s3_key(job_id, filename)
    range_header = request.headers.get("range")
    body, _content_type, content_length, content_range = get_object_stream(
        s3_key,
        byte_range=range_header,
    )

    def iter_body():
        try:
            while chunk := body.read(256 * 1024):
                yield chunk
        finally:
            body.close()

    headers = {
        "Cache-Control": "public, max-age=86400, immutable",
        "Access-Control-Allow-Origin": "*",
        "Accept-Ranges": "bytes",
        "Content-Type": _SEGMENT_MEDIA_TYPE,
    }

    if range_header and content_range:
        headers["Content-Range"] = content_range
        headers["Content-Length"] = str(content_length)
        return StreamingResponse(
            iter_body(),
            status_code=206,
            media_type=_SEGMENT_MEDIA_TYPE,
            headers=headers,
        )

    headers["Content-Length"] = str(content_length)
    return StreamingResponse(
        iter_body(),
        media_type=_SEGMENT_MEDIA_TYPE,
        headers=headers,
    )
