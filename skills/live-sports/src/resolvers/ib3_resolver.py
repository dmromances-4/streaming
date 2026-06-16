"""Resuelve streams en vivo de IB3 (Illes Balears)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx

from config import settings
from resolvers._scrape_utils import (
    extract_m3u8_from_json,
    extract_m3u8_urls,
    pick_best_m3u8,
    probe_manifest,
    resolve_scrape_channel,
)
from resolvers.types import StreamResult
from skill_telemetry import log

_MEDIA_APP_KEY = "AX_dasdf-d09¡asdfki-eLdERl3$"
_MEDIA_APP_URL = (
    f"https://ib3.org/ib3/mediaAPP/live/?key={quote(_MEDIA_APP_KEY, safe='')}"
)

_FALLBACK = [
    "https://ibsatiphone.ib3tv.com/iphoneliveIB3/IB3/bitrate_2.m3u8",
    "https://ibsatiphone.ib3tv.com/iphoneliveIB3/IB3/bitrate_3.m3u8",
]

_DEFAULT_PAGES = (
    "https://totib3.org/play/tv",
    "https://ib3.org/directe?c=televisio",
)

_SLUG_CHANNEL = {
    "televisio": "TELEVISIÓ",
    "1": "TELEVISIÓ",
    "2": "IB3 2",
}


async def _resolve_from_media_app(slug: str) -> StreamResult | None:
    headers = {"Referer": "https://ib3.org/", "User-Agent": settings.user_agent}
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(_MEDIA_APP_URL)
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        log.warning("ib3_media_app_failed", error=str(exc))
        return None

    target = _SLUG_CHANNEL.get(slug, slug).upper()
    for item in payload.get("directes") or []:
        if (item.get("type") or "").upper() != "TV":
            continue
        channel_name = (item.get("channel") or "").upper()
        if target not in channel_name and slug not in channel_name.lower():
            continue
        stream_url = (item.get("streamingUrl") or "").strip()
        if ".m3u8" in stream_url.lower():
            if await probe_manifest(stream_url, headers=headers):
                return StreamResult(manifest_url=stream_url)
        urls = extract_m3u8_urls(stream_url)
        urls.extend(extract_m3u8_from_json(json.dumps(item)))
        manifest = pick_best_m3u8(urls)
        if manifest and await probe_manifest(manifest, headers=headers):
            return StreamResult(manifest_url=manifest)
    return None


async def resolve_ib3_channel(channel: dict[str, Any]) -> StreamResult:
    slug = (channel.get("ib3_slug") or "televisio").strip()
    headers = {"Referer": "https://ib3.org/"}

    media = await _resolve_from_media_app(slug)
    if media and media.ok:
        return media

    page_urls: list[str] = []
    if channel.get("page_url"):
        page_urls.append(str(channel["page_url"]).strip())
    if slug in ("televisio", "1"):
        page_urls.extend(_DEFAULT_PAGES)
    else:
        page_urls.append(f"https://ib3.org/directe?c={slug}")

    seen_pages: set[str] = set()
    fallbacks = _FALLBACK if slug in ("televisio", "1") else None
    last_error = "Stream no disponible (mantenimiento o geo-block)"

    for page_url in page_urls:
        if page_url in seen_pages:
            continue
        seen_pages.add(page_url)
        result = await resolve_scrape_channel(
            channel,
            page_url=page_url,
            headers=headers,
            fallback_urls=fallbacks if page_url == page_urls[0] else None,
        )
        if result.ok:
            return result
        if result.error:
            last_error = result.error

    return StreamResult(error=last_error)
