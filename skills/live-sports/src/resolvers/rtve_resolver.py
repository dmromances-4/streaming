"""Resuelve streams HLS en vivo de RTVE Play."""

from __future__ import annotations

import json
import re
import time
from html import unescape
from typing import Any
from urllib.parse import quote

import httpx

from config import settings
from resolvers.types import StreamResult
from skill_telemetry import log

RTVE_DIRECT_BASE = "https://www.rtve.es/play/videos/directo/canales-lineales"
M3U8_TEMPLATE = "https://ztnr.rtve.es/ztnr/{asset_id}.m3u8"

_cache: dict[str, tuple[float, str]] = {}


async def resolve_rtve_channel(slug: str) -> StreamResult:
    page_url = f"{RTVE_DIRECT_BASE}/{quote(slug)}/"
    cached = _cache.get(slug)
    if cached and time.monotonic() - cached[0] < settings.resolver_cache_ttl_seconds:
        return StreamResult(manifest_url=cached[1])

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        ) as client:
            resp = await client.get(page_url)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as exc:
        log.warning("rtve_fetch_failed", slug=slug, error=str(exc))
        return StreamResult(error="No se pudo contactar con RTVE")

    asset_id = _extract_asset_id(html)
    if not asset_id:
        return StreamResult(error="Canal no disponible (geo-block o mantenimiento RTVE)")

    m3u8 = M3U8_TEMPLATE.format(asset_id=asset_id)
    _cache[slug] = (time.monotonic(), m3u8)
    return StreamResult(manifest_url=m3u8)


def _extract_asset_id(html: str) -> str | None:
    for pattern in (
        r'data-setup="([^"]+)"',
        r"data-setup='([^']+)'",
    ):
        match = re.search(pattern, html)
        if not match:
            continue
        raw = unescape(match.group(1))
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            continue
        asset_id = data.get("idAsset") or data.get("idasset")
        is_live = data.get("isLive") or data.get("islive")
        if asset_id and (is_live is True or str(is_live).lower() == "true"):
            return str(asset_id)
    return None
