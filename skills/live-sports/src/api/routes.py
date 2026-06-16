"""Rutas HTTP del Skill #3."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import Response as FastAPIResponse
from prometheus_client import generate_latest

_shared = Path(__file__).resolve().parents[4] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from channel_catalog import (  # noqa: E402
    filter_channels,
    list_channels_grouped,
    list_countries,
    load_channels,
    proxy_headers_for_channel,
    resolve_channel_stream,
)
from config import settings  # noqa: E402
from drm_license_proxy import proxy_widevine_license  # noqa: E402
from proxy_client import get_proxy_client  # noqa: E402
from skill_telemetry import log  # noqa: E402
from url_validator import validate_target_url  # noqa: E402
from vpn_check import is_vpn_up  # noqa: E402

router = APIRouter()
health_router = APIRouter()

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}


@health_router.get("/health")
async def health() -> dict[str, str | bool]:
    vpn_ok = await is_vpn_up()
    if settings.vpn_required and not vpn_ok:
        from errors import VPNNotReadyError

        raise VPNNotReadyError("VPN tunnel required but not active")
    return {
        "status": "ok",
        "skill": settings.skill_name,
        "vpn_required": settings.vpn_required,
        "vpn_up": vpn_ok,
    }


@health_router.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.options("/fetch")
@router.options("/proxy")
async def cors_preflight() -> Response:
    return Response(status_code=204, headers=_CORS)


@router.get("/channels")
async def list_channels(
    country: str | None = Query(None, min_length=2, max_length=2),
    q: str | None = Query(None, min_length=1, max_length=80),
    tag: str | None = Query(None, min_length=1, max_length=40),
) -> dict:
    channels = filter_channels(country=country, query=q, tag=tag)
    return {
        "total": len(channels) if (country or q or tag) else len(load_channels()),
        "countries": list_countries(),
        "groups": list_channels_grouped(country=country, query=q, tag=tag),
        "channels": channels,
    }


@router.get("/auth/status")
async def auth_status() -> dict:
    vpn_ok = await is_vpn_up()
    return {
        "bbc_configured": bool(settings.bbc_iplayer_cookies),
        "france_tv_configured": bool(settings.france_tv_cookies),
        "vpn_required": settings.vpn_required,
        "vpn_up": vpn_ok,
    }


@router.get("/channels/health")
async def channels_health() -> dict:
    from resolvers.registry import resolve_channel

    samples = [
        ("ES", "rtve-la1"),
        ("DE", "de-daserste"),
        ("FR", "fr-france2"),
        ("IT", "it-rai1"),
    ]
    by_country: dict[str, dict[str, int | bool]] = {}
    for code, channel_id in samples:
        ch = next((c for c in load_channels() if c.get("id") == channel_id), None)
        ok = False
        if ch:
            result = await resolve_channel(ch)
            ok = result.ok
        entry = by_country.setdefault(code, {"ok": 0, "fail": 0, "healthy": True})
        if ok:
            entry["ok"] = int(entry["ok"]) + 1
        else:
            entry["fail"] = int(entry["fail"]) + 1
            entry["healthy"] = False
    overall = all(v.get("healthy") for v in by_country.values())
    return {"ok": overall, "by_country": by_country, "total_channels": len(load_channels())}


@router.get("/channels/{channel_id}/stream")
async def channel_stream(channel_id: str) -> dict:
    return await resolve_channel_stream(channel_id)


@router.options("/drm/license/{provider}")
async def drm_license_preflight() -> Response:
    return Response(status_code=204, headers=_CORS)


@router.post("/drm/license/{provider}")
async def drm_license(
    provider: str,
    request: Request,
    channel_id: str = Query(..., min_length=2),
) -> Response:
    body = await request.body()
    if not body:
        from errors import InvalidInputError

        raise InvalidInputError("License challenge vacío")
    license_bytes, headers = await proxy_widevine_license(provider, channel_id, body)
    return Response(
        content=license_bytes,
        headers={**_CORS, **headers},
    )


@router.get("/proxy")
async def proxy_playlist(
    url: str = Query(..., min_length=8),
    channel_id: str | None = Query(None, min_length=2, max_length=80),
) -> Response:
    """Proxy principal para playlists M3U8 externas (deportes en vivo)."""
    validate_target_url(url, block_private=settings.block_private_ips)
    client = get_proxy_client()
    body, _, headers = await client.fetch(
        url,
        extra_headers=proxy_headers_for_channel(channel_id),
        channel_id=channel_id,
    )
    log.info("proxy_playlist", url=url[:80], channel_id=channel_id)
    return Response(content=body, headers=headers)


@router.get("/fetch")
async def proxy_fetch(
    url: str = Query(..., min_length=8),
    channel_id: str | None = Query(None, min_length=2, max_length=80),
) -> Response:
    """Proxy genérico para segmentos .ts y sub-playlists."""
    validate_target_url(url, block_private=settings.block_private_ips)
    client = get_proxy_client()
    body, _, headers = await client.fetch(
        url,
        extra_headers=proxy_headers_for_channel(channel_id),
        channel_id=channel_id,
    )
    return Response(content=body, headers=headers)
