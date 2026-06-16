"""Proxy de licencias Widevine hacia upstream."""

from __future__ import annotations

import httpx

from config import settings
from drm_license_store import get_license_context
from errors import InvalidInputError, NotFoundError, UpstreamError
from skill_telemetry import log
from vpn_check import is_vpn_up


async def proxy_widevine_license(
    provider: str,
    channel_id: str,
    challenge: bytes,
) -> tuple[bytes, dict[str, str]]:
    if not channel_id:
        raise InvalidInputError("channel_id requerido")

    ctx = get_license_context(channel_id, provider)
    if not ctx:
        raise NotFoundError(f"Sin contexto DRM para {channel_id}")

    if settings.vpn_required and not await is_vpn_up():
        from errors import VPNNotReadyError

        raise VPNNotReadyError("VPN tunnel not ready")

    headers = {
        "User-Agent": settings.user_agent,
        "Content-Type": "application/octet-stream",
        **ctx.headers,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.post(
                ctx.license_url,
                content=challenge,
                headers=headers,
            )
            if resp.status_code == 401:
                raise UpstreamError(
                    "Cookies BBC inválidas o caducadas — actualiza BBC_IPLAYER_COOKIES"
                )
            resp.raise_for_status()
            return resp.content, {
                "Content-Type": resp.headers.get(
                    "content-type", "application/octet-stream"
                ),
            }
    except httpx.HTTPError as exc:
        log.warning(
            "drm_license_proxy_failed",
            provider=provider,
            channel_id=channel_id,
            error=str(exc),
        )
        raise UpstreamError(f"License server error: {exc}") from exc
