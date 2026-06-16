"""Catálogo de canales de TV gratuita."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

from config import settings
from resolvers.registry import resolve_channel

_channels: list[dict[str, Any]] | None = None

_COUNTRY_NAMES: dict[str, str] = {
    "AT": "Austria",
    "BE": "Bélgica",
    "BG": "Bulgaria",
    "CH": "Suiza",
    "CY": "Chipre",
    "CZ": "Chequia",
    "DE": "Alemania",
    "DK": "Dinamarca",
    "EE": "Estonia",
    "ES": "España",
    "EU": "Europa",
    "FI": "Finlandia",
    "FR": "Francia",
    "GB": "Reino Unido",
    "GR": "Grecia",
    "HR": "Croacia",
    "HU": "Hungría",
    "IE": "Irlanda",
    "IS": "Islandia",
    "IT": "Italia",
    "LT": "Lituania",
    "LU": "Luxemburgo",
    "LV": "Letonia",
    "MT": "Malta",
    "NL": "Países Bajos",
    "NO": "Noruega",
    "PL": "Polonia",
    "PT": "Portugal",
    "RO": "Rumanía",
    "SE": "Suecia",
    "SI": "Eslovenia",
    "SK": "Eslovaquia",
    "UK": "Reino Unido",
}


def _channels_root() -> Path:
    return Path(settings.live_channels_path).parent


def _channels_subdir() -> Path | None:
    candidates = [
        Path(settings.live_channels_dir),
        _channels_root() / "live-channels",
        Path(__file__).resolve().parents[3] / "catalog" / "data" / "live-channels",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return None


def _parse_channel_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []
    raw = data.get("channels") or []
    out: list[dict[str, Any]] = []
    for ch in raw:
        if not isinstance(ch, dict) or not ch.get("id"):
            continue
        if ch.get("enabled", True) is False:
            continue
        country = (ch.get("country") or "").upper()
        if country and not ch.get("country_name"):
            ch["country_name"] = _COUNTRY_NAMES.get(country, country)
        out.append(ch)
    return out


def load_channels() -> list[dict[str, Any]]:
    global _channels
    if _channels is not None:
        return _channels

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    legacy = Path(settings.live_channels_path)
    for ch in _parse_channel_file(legacy):
        cid = ch["id"]
        if cid not in seen:
            seen.add(cid)
            merged.append(ch)

    subdir = _channels_subdir()
    if subdir is not None:
        for path in sorted(subdir.glob("*.yaml")):
            for ch in _parse_channel_file(path):
                cid = ch["id"]
                if cid not in seen:
                    seen.add(cid)
                    merged.append(ch)

    _channels = merged
    return _channels


def reload_channels() -> list[dict[str, Any]]:
    global _channels
    _channels = None
    return load_channels()


def get_channel(channel_id: str) -> dict[str, Any] | None:
    for ch in load_channels():
        if ch.get("id") == channel_id:
            return ch
    return None


def _channel_public(ch: dict[str, Any]) -> dict[str, Any]:
    country = (ch.get("country") or "").upper()
    out: dict[str, Any] = {
        "id": ch["id"],
        "name": ch.get("name", ch["id"]),
        "country": country or None,
        "country_name": ch.get("country_name") or _COUNTRY_NAMES.get(country, country or None),
        "group": ch.get("group") or "General",
        "logo": ch.get("logo"),
        "tags": ch.get("tags") or [],
        "region": ch.get("region"),
    }
    if ch.get("drm"):
        out["drm"] = ch["drm"]
    if ch.get("requires_vpn"):
        out["requires_vpn"] = True
    if ch.get("geo_country"):
        out["geo_country"] = ch["geo_country"]
    if ch.get("auth_provider"):
        out["auth_provider"] = ch["auth_provider"]
    return out


def filter_channels(
    country: str | None = None,
    query: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    items = [_channel_public(ch) for ch in load_channels()]
    if country:
        code = country.upper()
        items = [c for c in items if (c.get("country") or "").upper() == code]
    if tag:
        t = tag.strip().lower()
        if t:
            items = [
                c
                for c in items
                if t in [x.lower() for x in (c.get("tags") or []) if isinstance(x, str)]
            ]
    if query:
        q = query.strip().lower()
        if q:
            items = [
                c
                for c in items
                if q in (c.get("name") or "").lower()
                or q in (c.get("country_name") or "").lower()
                or q in (c.get("group") or "").lower()
                or q in (c.get("region") or "").lower()
                or q in (c.get("id") or "").lower()
                or any(q in (t or "").lower() for t in (c.get("tags") or []))
            ]
    return items


def list_countries() -> list[dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = {}
    for ch in load_channels():
        code = (ch.get("country") or "XX").upper()
        name = ch.get("country_name") or _COUNTRY_NAMES.get(code, code)
        if code not in counts:
            counts[code] = {"code": code, "name": name, "count": 0}
        counts[code]["count"] += 1
    return sorted(counts.values(), key=lambda x: x["name"])


def list_channels_grouped(
    country: str | None = None,
    query: str | None = None,
    tag: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in filter_channels(country=country, query=query, tag=tag):
        country_name = item.get("country_name") or "Internacional"
        group_label = f"{country_name} · {item.get('group') or 'General'}"
        grouped.setdefault(group_label, []).append(item)
    return grouped


def proxy_headers_for_channel(channel_id: str | None) -> dict[str, str]:
    if not channel_id:
        return {}
    ch = get_channel(channel_id)
    if not ch:
        return {}
    raw = ch.get("proxy_headers") or {}
    return {str(k): str(v) for k, v in raw.items() if v}


async def resolve_channel_stream(channel_id: str) -> dict[str, Any]:
    ch = get_channel(channel_id)
    if not ch:
        from errors import NotFoundError

        raise NotFoundError(f"Channel {channel_id} not found")

    result = await resolve_channel(ch)
    if not result.ok:
        from errors import UpstreamError

        raise UpstreamError(result.error or "Stream no disponible")

    base = settings.public_api_base.rstrip("/")
    proxied = (
        f"{base}/api/v1/proxy?url={quote(result.manifest_url or '', safe='')}"
        f"&channel_id={quote(channel_id, safe='')}"
    )
    payload: dict[str, Any] = {
        "channel_id": channel_id,
        "name": ch.get("name"),
        "country": ch.get("country"),
        "country_name": ch.get("country_name"),
        "stream_url": result.manifest_url,
        "proxied_url": proxied,
        "manifest_type": result.manifest_type,
    }
    requirements = dict(result.requirements)
    if ch.get("requires_vpn"):
        requirements["vpn"] = True
    if ch.get("auth_provider"):
        requirements["auth"] = ch["auth_provider"]
    if ch.get("geo_country"):
        requirements["geo_country"] = ch["geo_country"]
    if requirements:
        payload["requirements"] = requirements
    if result.drm:
        provider = ch.get("auth_provider") or "widevine"
        payload["drm"] = {
            "scheme": result.drm.scheme,
            "license_proxy": (
                f"{base}/api/v1/drm/license/{provider}"
                f"?channel_id={quote(channel_id)}"
            ),
        }
    return payload
