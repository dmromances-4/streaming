"""Resuelve streams Brightcove Live/VOD vía Playback API."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from config import settings
from resolvers.types import StreamResult
from skill_telemetry import log

_policy_cache: dict[str, tuple[float, str]] = {}
_playback_cache: dict[str, tuple[float, str]] = {}


async def _fetch_policy_key(account_id: str, player_id: str) -> str | None:
    cache_key = f"{account_id}:{player_id}"
    cached = _policy_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < settings.resolver_cache_ttl_seconds:
        return cached[1]

    config_url = (
        f"https://players.brightcove.net/{account_id}/"
        f"{player_id}_default/config.json"
    )
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        ) as client:
            resp = await client.get(config_url)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        log.warning("brightcove_config_failed", url=config_url, error=str(exc))
        return None

    policy = _policy_key_from_config(data)
    if not policy:
        return None
    _policy_cache[cache_key] = (time.monotonic(), policy)
    return policy


def _policy_key_from_config(data: dict[str, Any]) -> str | None:
    video_cloud = data.get("video_cloud") or {}
    policy = data.get("policy_key") or video_cloud.get("policy_key")
    return policy or None


def _video_path_from_ref(ref_id: str) -> str:
    if ref_id.startswith("ref:"):
        return ref_id
    if ref_id.isdigit():
        return ref_id
    return f"ref:{ref_id}"


def _pick_hls_source(sources: list[dict[str, Any]]) -> str | None:
    for item in sources:
        src = item.get("src") or ""
        typ = (item.get("type") or "").lower()
        if ".m3u8" in src.lower() or "mpegurl" in typ:
            return src
    return None


async def resolve_brightcove_channel(channel: dict[str, Any]) -> StreamResult:
    account_id = str(channel.get("brightcove_account") or "").strip()
    ref_id = str(channel.get("brightcove_ref") or "").strip()
    player_id = str(channel.get("brightcove_player") or "default").strip()

    if not account_id or not ref_id:
        return StreamResult(error="Brightcove: faltan account/ref")

    cache_key = f"{account_id}:{ref_id}"
    cached = _playback_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < settings.resolver_cache_ttl_seconds:
        return StreamResult(manifest_url=cached[1])

    policy_key = await _fetch_policy_key(account_id, player_id)
    if not policy_key:
        return StreamResult(error="Brightcove: policy key no disponible")

    ref = ref_id if ref_id.startswith("ref:") else f"ref:{ref_id}"
    api_url = (
        f"https://edge.api.brightcove.com/playback/v1/accounts/"
        f"{account_id}/videos/{ref}"
    )
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": f"application/json;pk={policy_key}",
    }
    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(api_url)
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        log.warning("brightcove_playback_failed", url=api_url, error=str(exc))
        return StreamResult(error="Stream no disponible (Brightcove)")

    manifest = _pick_hls_source(payload.get("sources") or [])
    if not manifest:
        return StreamResult(error="Stream no disponible (sin HLS)")

    _playback_cache[cache_key] = (time.monotonic(), manifest)
    return StreamResult(manifest_url=manifest)
