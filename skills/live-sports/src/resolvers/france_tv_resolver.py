"""Resolver France.tv — token HLS vía hdfauth."""

from __future__ import annotations

import time
from typing import Any

import httpx

from config import settings
from resolvers.types import StreamResult
from skill_telemetry import log

HDFAUTH_BASE = "https://hdfauth.ftven.fr/uri/TOKEN"

_cache: dict[str, tuple[float, str]] = {}


async def resolve_france_tv_channel(channel: dict[str, Any]) -> StreamResult:
    uuid = (channel.get("channel_uuid") or "").strip()
    if not uuid:
        return StreamResult(error="Canal France.tv sin channel_uuid")

    cached = _cache.get(uuid)
    if cached and time.monotonic() - cached[0] < settings.resolver_cache_ttl_seconds:
        return StreamResult(manifest_url=cached[1])

    headers = {"User-Agent": settings.user_agent}
    if settings.france_tv_cookies:
        headers["Cookie"] = settings.france_tv_cookies

    url = f"{HDFAUTH_BASE}/{uuid}"
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=False,
            headers=headers,
        ) as client:
            resp = await client.get(url)
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("location", "").strip()
                if location.startswith(("http://", "https://")):
                    _cache[uuid] = (time.monotonic(), location)
                    return StreamResult(manifest_url=location)
            if resp.status_code == 200 and resp.text.strip().startswith("#EXTM3U"):
                _cache[uuid] = (time.monotonic(), url)
                return StreamResult(manifest_url=url)
    except httpx.HTTPError as exc:
        log.warning("france_tv_fetch_failed", uuid=uuid, error=str(exc))
        return StreamResult(error="No se pudo contactar con France.tv")

    return StreamResult(error="France.tv no devolvió URL de stream")
