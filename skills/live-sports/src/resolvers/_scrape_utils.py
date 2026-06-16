"""Utilidades compartidas para resolvers basados en scrape HTTP."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from config import settings
from resolvers.types import StreamResult
from skill_telemetry import log

_M3U8_RE = re.compile(
    r"https?://[^\s\"'<>\\]+\.m3u8[^\s\"'<>\\]*",
    re.IGNORECASE,
)

_JSON_M3U8_ATTR_RE = re.compile(
    r'"(?:sourceURL|sourceUrl|hlsUrl|hls_url|streamUrl|stream_url|manifestUrl|manifest_url|src|url)"\s*:\s*"([^"]+\.m3u8[^"]*)"',
    re.IGNORECASE,
)

_cache: dict[str, tuple[float, str]] = {}


def _client_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    return {"User-Agent": settings.user_agent, **(extra or {})}


async def fetch_text(url: str, headers: dict[str, str] | None = None) -> str | None:
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers=_client_headers(headers),
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPError as exc:
        log.warning("scrape_fetch_failed", url=url, error=str(exc))
        return None


async def probe_manifest(url: str, headers: dict[str, str] | None = None) -> bool:
    """Valida URL de manifest con HEAD/GET; no exige #EXTM3U en páginas HTML."""
    hdrs = _client_headers(headers)
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=hdrs,
        ) as client:
            for method in ("head", "get"):
                try:
                    if method == "head":
                        resp = await client.head(url)
                    else:
                        resp = await client.get(url)
                except httpx.HTTPError:
                    continue
                if resp.status_code != 200:
                    continue
                if method == "head":
                    return True
                body = resp.text
                ct = (resp.headers.get("content-type") or "").lower()
                if "mpegurl" in ct or url.lower().endswith(".m3u8"):
                    return "#EXTM3U" in body or len(body) < 8000
                return True
    except httpx.HTTPError as exc:
        log.warning("probe_manifest_failed", url=url, error=str(exc))
    return False


def extract_m3u8_urls(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _M3U8_RE.findall(text):
        url = match.rstrip("\\")
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _walk_json_for_m3u8(node: Any, out: list[str], seen: set[str]) -> None:
    if isinstance(node, str) and ".m3u8" in node.lower():
        if node not in seen:
            seen.add(node)
            out.append(node)
        return
    if isinstance(node, dict):
        for value in node.values():
            _walk_json_for_m3u8(value, out, seen)
        return
    if isinstance(node, list):
        for item in node:
            _walk_json_for_m3u8(item, out, seen)


def extract_m3u8_from_json(text: str) -> list[str]:
    """Extrae URLs m3u8 de JSON embebido en scripts o atributos del player."""
    seen: set[str] = set()
    out: list[str] = []

    for match in _JSON_M3U8_ATTR_RE.findall(text):
        if match not in seen:
            seen.add(match)
            out.append(match)

    for block in re.findall(
        r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        _walk_json_for_m3u8(data, out, seen)

    for blob in re.findall(r"\{[^{}]{0,2000}\.m3u8[^{}]{0,2000}\}", text):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        _walk_json_for_m3u8(data, out, seen)

    return out


def pick_best_m3u8(urls: list[str]) -> str | None:
    if not urls:
        return None
    scored: list[tuple[int, str]] = []
    for url in urls:
        lower = url.lower()
        score = 0
        if "master" in lower:
            score += 10
        if "live" in lower or "direct" in lower:
            score += 5
        if "playlist" in lower:
            score += 3
        if "bitrate" in lower:
            score -= 2
        scored.append((score, url))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][1]


async def resolve_scrape_channel(
    channel: dict[str, Any],
    *,
    page_url: str,
    headers: dict[str, str] | None = None,
    fallback_urls: list[str] | None = None,
) -> StreamResult:
    cache_key = channel.get("id") or page_url
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < settings.resolver_cache_ttl_seconds:
        return StreamResult(manifest_url=cached[1])

    for url in fallback_urls or []:
        if await probe_manifest(url, headers=headers):
            _cache[cache_key] = (time.monotonic(), url)
            return StreamResult(manifest_url=url)

    html = await fetch_text(page_url, headers=headers)
    if not html:
        return StreamResult(error="No se pudo contactar con el emisor")

    urls = extract_m3u8_urls(html)
    urls.extend(extract_m3u8_from_json(html))
    manifest = pick_best_m3u8(urls)
    if not manifest:
        return StreamResult(error="Stream no disponible (mantenimiento o geo-block)")

    if not await probe_manifest(manifest, headers=headers):
        return StreamResult(error="Manifest no accesible (geo-block o caducado)")

    _cache[cache_key] = (time.monotonic(), manifest)
    return StreamResult(manifest_url=manifest)
