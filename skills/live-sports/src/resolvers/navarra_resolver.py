"""Resuelve streams en vivo de Navarra Televisión."""

from __future__ import annotations

from typing import Any

from resolvers._scrape_utils import resolve_scrape_channel
from resolvers.types import StreamResult

_NTV_STATIC = (
    "http://nws.nice264.com/SmilLive/getLiveIOS.smil?"
    "stream=NTV_livenatvmb&system=NTV&protocol=http_cupertino/playlist.m3u8"
)

_NICE264_CDN = (
    "http://cdn.s3.eu.nice264.com:1935/niceLiveServer/"
    "NTV_livenatvmb_MB_478/live.m3u8"
)

_NATV_PLAY = (
    "https://www.natvplay.es/player/navarra-television/"
    "navarra-television-live"
)

_FALLBACKS = [_NICE264_CDN, _NTV_STATIC]

_PAGE_URLS = (
    _NATV_PLAY,
    "https://www.navarratelevision.es/",
)


async def resolve_navarra_channel(channel: dict[str, Any]) -> StreamResult:
    headers = {"Referer": "https://www.natvplay.es/"}
    page_urls: list[str] = []
    if channel.get("page_url"):
        page_urls.append(str(channel["page_url"]).strip())
    page_urls.extend(_PAGE_URLS)

    seen_pages: set[str] = set()
    last_error = "Stream no disponible (mantenimiento o geo-block)"

    for page_url in page_urls:
        if page_url in seen_pages:
            continue
        seen_pages.add(page_url)
        result = await resolve_scrape_channel(
            channel,
            page_url=page_url,
            headers=headers,
            fallback_urls=_FALLBACKS if page_url == page_urls[0] else None,
        )
        if result.ok:
            return result
        if result.error:
            last_error = result.error

    return StreamResult(error=last_error)
