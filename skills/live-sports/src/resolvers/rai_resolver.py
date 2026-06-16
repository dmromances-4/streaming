"""Resolver RAI Play live — relinker mediapolis."""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import quote

import httpx

from config import settings
from resolvers.types import StreamResult
from skill_telemetry import log

RELINKER = "https://mediapolis.rai.it/relinker/relinkerServlet.htm"

# slug YAML -> cont ID RAI
_RAI_CONT: dict[str, str] = {
    "rai-1": "2606803",
    "rai-2": "2606804",
    "rai-3": "2606805",
    "rainews24": "2606807",
    "raisport": "358071",
    "raiscuola": "742953",
    "raistoria": "746992",
}

_cache: dict[str, tuple[float, str]] = {}


async def resolve_rai_channel(channel: dict[str, Any]) -> StreamResult:
    slug = (channel.get("slug") or "").strip().lower()
    cont = channel.get("rai_cont") or _RAI_CONT.get(slug)
    if not cont:
        return StreamResult(error="Canal RAI sin slug/cont configurado")

    cache_key = str(cont)
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < min(settings.resolver_cache_ttl_seconds, 120):
        return StreamResult(manifest_url=cached[1])

    params = f"cont={quote(str(cont))}&output=64"
    url = f"{RELINKER}?{params}"
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            body = resp.text
    except httpx.HTTPError as exc:
        log.warning("rai_fetch_failed", cont=cont, error=str(exc))
        return StreamResult(error="No se pudo contactar con RAI Play")

    m3u8 = _extract_m3u8_url(body)
    if not m3u8:
        return StreamResult(error="RAI Play no devolvió URL HLS")

    _cache[cache_key] = (time.monotonic(), m3u8)
    return StreamResult(manifest_url=m3u8)


def _extract_m3u8_url(body: str) -> str | None:
    for pattern in (
        r'<url[^>]*>(https?://[^<]+\.m3u8[^<]*)</url>',
        r'"(https?://[^"]+\.m3u8[^"]*)"',
        r"(https?://[^\s\"']+\.m3u8)",
    ):
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None
