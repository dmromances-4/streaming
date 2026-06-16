"""Resolver BBC iPlayer — mediaselector + Widevine."""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote

import httpx

from config import settings
from drm_license_store import store_license_context
from resolvers.types import DrmInfo, StreamResult
from skill_telemetry import log
from vpn_check import is_vpn_up

MEDIASELECTOR = (
    "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/"
    "mediaset/pc/vpid/{vpid}/provision/iptv_all/formats/hls/"

)
BBC_NS = {"bbc": "http://www.bbc.co.uk/2008/MPD"}
DEFAULT_LICENSE = (
    "https://lic.drmtoday.com/licenseServerWidevineChallenge/?provisioner=bbc"
)

_cache: dict[str, tuple[float, StreamResult]] = {}


async def resolve_bbc_iplayer_channel(channel: dict[str, Any]) -> StreamResult:
    vpid = (channel.get("vpid") or "").strip()
    channel_id = channel.get("id", vpid)
    if not vpid:
        return StreamResult(error="Canal BBC sin vpid")

    if settings.vpn_required and not await is_vpn_up():
        return StreamResult(
            error="VPN UK requerida para BBC iPlayer",
            requirements={"vpn": True, "auth": "bbc"},
        )

    if not settings.bbc_iplayer_cookies:
        return StreamResult(
            error="Configura BBC_IPLAYER_COOKIES en el servidor",
            requirements={"vpn": True, "auth": "bbc"},
        )

    cached = _cache.get(vpid)
    if cached and time.monotonic() - cached[0] < settings.resolver_cache_ttl_seconds:
        return cached[1]

    headers = {
        "User-Agent": settings.user_agent,
        "Cookie": settings.bbc_iplayer_cookies,
    }

    url = MEDIASELECTOR.format(vpid=quote(vpid))
    try:
        async with httpx.AsyncClient(
            timeout=25.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            xml_body = resp.text
    except httpx.HTTPError as exc:
        log.warning("bbc_mediaselector_failed", vpid=vpid, error=str(exc))
        return StreamResult(
            error="No se pudo contactar con BBC iPlayer",
            requirements={"vpn": True, "auth": "bbc"},
        )

    manifest_url = _parse_manifest_href(xml_body)
    if not manifest_url:
        return StreamResult(
            error="BBC iPlayer no devolvió manifest",
            requirements={"vpn": True, "auth": "bbc"},
        )

    license_url, license_headers = await _resolve_license(
        manifest_url, headers, channel_id
    )

    drm = DrmInfo(
        scheme="widevine",
        license_url=license_url,
        headers={**headers, **license_headers},
    )
    store_license_context(channel_id, "bbc", drm)

    result = StreamResult(
        manifest_url=manifest_url,
        manifest_type="hls",
        drm=drm,
        requirements={"vpn": channel.get("requires_vpn", True), "auth": "bbc"},
    )
    _cache[vpid] = (time.monotonic(), result)
    return result


def _parse_manifest_href(xml_body: str) -> str | None:
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError:
        pass
    else:
        for conn in root.findall(".//bbc:connection", BBC_NS):
            href = conn.findtext("bbc:href", default="", namespaces=BBC_NS)
            if href and href.startswith(("http://", "https://")):
                return href.strip()
        for conn in root.findall(".//connection"):
            href = conn.findtext("href", default="")
            if href and href.startswith(("http://", "https://")):
                return href.strip()

    match = re.search(r"<href>(https?://[^<]+)</href>", xml_body)
    if match:
        return match.group(1).strip()
    return None


async def _resolve_license(
    manifest_url: str,
    headers: dict[str, str],
    channel_id: str,
) -> tuple[str, dict[str, str]]:
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(manifest_url)
            resp.raise_for_status()
            playlist = resp.text
    except httpx.HTTPError:
        return DEFAULT_LICENSE, {}

    for line in playlist.splitlines():
        if "SESSION-KEY" not in line and "EXT-X-KEY" not in line:
            continue
        uri_match = re.search(r'URI="([^"]+)"', line)
        if uri_match:
            uri = uri_match.group(1)
            if uri.startswith("http"):
                return uri, {}
            if uri.startswith("skd://"):
                return DEFAULT_LICENSE, {}

    return DEFAULT_LICENSE, {}
