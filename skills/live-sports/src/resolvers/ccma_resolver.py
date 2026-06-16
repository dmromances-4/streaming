"""Resuelve streams en vivo de CCMA / 3Cat (Cataluña)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from config import settings
from resolvers.types import StreamResult
from skill_telemetry import log

CCMA_API = "https://api-media.ccma.cat/pvideo/media.jsp"
_GEO_PRIORITY = ("ESPANYA", "TOTS", "CATALUNYA")

_cache: dict[str, tuple[float, str]] = {}


def _pick_hls_url(media: list[dict[str, Any]]) -> str | None:
    hls = [m for m in media if (m.get("format") or "").upper() == "HLS" and m.get("url")]
    if not hls:
        hls = [m for m in media if m.get("url")]
    if not hls:
        return None
    by_geo = {str(m.get("geo", "")).upper(): str(m["url"]) for m in hls}
    for geo in _GEO_PRIORITY:
        if geo in by_geo:
            return by_geo[geo]
    return str(hls[0]["url"])


async def resolve_ccma_channel(channel: dict[str, Any]) -> StreamResult:
    ccma_id = (channel.get("ccma_id") or channel.get("slug") or "").strip()
    if not ccma_id:
        return StreamResult(error="Canal CCMA sin ccma_id")

    cached = _cache.get(ccma_id)
    if cached and time.monotonic() - cached[0] < settings.resolver_cache_ttl_seconds:
        return StreamResult(manifest_url=cached[1])

    params = {"media": "video", "idint": ccma_id, "format": "hls"}
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        ) as client:
            resp = await client.get(CCMA_API, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        log.warning("ccma_fetch_failed", ccma_id=ccma_id, error=str(exc))
        return StreamResult(error="No se pudo contactar con CCMA")
    except ValueError:
        return StreamResult(error="Respuesta inválida de CCMA")

    media = data.get("media")
    if not isinstance(media, list):
        return StreamResult(error="Canal no disponible (geo-block o mantenimiento CCMA)")

    manifest = _pick_hls_url(media)
    if not manifest:
        return StreamResult(error="Sin stream HLS en CCMA")

    _cache[ccma_id] = (time.monotonic(), manifest)
    return StreamResult(manifest_url=manifest)
