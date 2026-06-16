"""Resuelve streams en vivo de CyLTV / La 7 (Castilla y León)."""

from __future__ import annotations

from typing import Any

from resolvers._scrape_utils import fetch_text, resolve_scrape_channel
from resolvers.types import StreamResult

_LA7_STATIC = (
    "http://la7-vh.akamaihd.net/i/content/entry/data/0/299/"
    "0_b7o9lvba_0_kyyr8vxz_1.mp4/master.m3u8"
)
_LA7_PLAYER = (
    "https://www.cyltvplay.es/player/d3badef6-d229-4a27-9609-03df3d17ca3/la7/la7"
)


async def resolve_cyltv_channel(channel: dict[str, Any]) -> StreamResult:
    slug = (channel.get("cyltv_slug") or "la7").strip().lower()
    if slug == "la7":
        body = await fetch_text(_LA7_STATIC)
        if body and "#EXTM3U" in body:
            return StreamResult(manifest_url=_LA7_STATIC)

    page_url = (channel.get("page_url") or _LA7_PLAYER).strip()
    return await resolve_scrape_channel(
        channel,
        page_url=page_url,
        headers={"Referer": "https://www.cyltv.es/"},
    )
