"""Comprobación de estado VPN (gluetun)."""

from __future__ import annotations

import httpx

from config import settings
from skill_telemetry import log


async def is_vpn_up() -> bool:
    if not settings.vpn_required:
        return True

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(settings.vpn_health_url)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("status") == "running" or data.get("vpn") is True
    except httpx.HTTPError as exc:
        log.warning("vpn_health_check_failed", error=str(exc))
    return False
