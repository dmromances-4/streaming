"""Resuelve streams en vivo de CRTVG / TVG (Galicia)."""

from __future__ import annotations

from typing import Any

from resolvers._scrape_utils import fetch_text, resolve_scrape_channel
from resolvers.types import StreamResult

_KNOWN = [
    "https://crtvg-hls-live.flumotion.com/playlist.m3u8",
    "https://crtvg-rrtv-live.flumotion.com/playlist.m3u8",
    "https://crtvg-europa.flumotion.cloud/playlist.m3u8",
]


async def resolve_tvg_channel(channel: dict[str, Any]) -> StreamResult:
    for url in _KNOWN:
        body = await fetch_text(url)
        if body and "#EXTM3U" in body:
            return StreamResult(manifest_url=url)

    page_url = (channel.get("page_url") or "https://www.crtvg.es/").strip()
    return await resolve_scrape_channel(
        channel,
        page_url=page_url,
        headers={"Referer": "https://www.crtvg.es/"},
    )
