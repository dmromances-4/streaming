"""Cliente HTTP upstream para el proxy live."""

from __future__ import annotations

import time
from typing import Any

import httpx

from config import settings
from errors import ProxyTimeoutError, UpstreamError, VPNNotReadyError
from m3u8_rewriter import detect_content_type, rewrite_playlist
from skill_telemetry import log, proxy_duration_seconds, proxy_requests_total, record_error
from url_validator import validate_target_url
from vpn_check import is_vpn_up

# Headers a no reenviar al cliente
_STRIP_RESPONSE_HEADERS = {
    "transfer-encoding",
    "connection",
    "keep-alive",
    "content-encoding",
    "access-control-allow-origin",
    "access-control-allow-methods",
    "access-control-allow-headers",
}

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Expose-Headers": "Content-Length, Content-Type",
}


async def _validate_redirect(request: httpx.Request) -> None:
    validate_target_url(str(request.url), block_private=settings.block_private_ips)


class LiveProxyClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=settings.max_redirects,
            timeout=httpx.Timeout(settings.proxy_timeout_seconds),
            headers={"User-Agent": settings.user_agent},
            event_hooks={"request": [_validate_redirect]},
        )
        log.info("proxy_client_started")

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        log.info("proxy_client_stopped")

    async def fetch(
        self,
        url: str,
        *,
        extra_headers: dict[str, str] | None = None,
        channel_id: str | None = None,
    ) -> tuple[bytes, str, dict[str, str]]:
        if settings.vpn_required and not await is_vpn_up():
            raise VPNNotReadyError("VPN tunnel not ready")

        validate_target_url(url, block_private=settings.block_private_ips)

        if not self._client:
            raise UpstreamError("Proxy client not initialized")

        start = time.monotonic()
        try:
            response = await self._client.get(url, headers=extra_headers or None)
        except httpx.TimeoutException as exc:
            record_error("proxy_timeout")
            raise ProxyTimeoutError(f"Upstream timeout: {url[:80]}") from exc
        except httpx.HTTPError as exc:
            record_error("upstream_error")
            raise UpstreamError(str(exc)) from exc

        proxy_duration_seconds.observe(time.monotonic() - start)

        if response.status_code >= 400:
            record_error("upstream_error")
            raise UpstreamError(
                f"Upstream returned {response.status_code}",
                details={"status": response.status_code, "url": url[:120]},
            )

        body = response.content
        header_ct = response.headers.get("content-type", "").split(";")[0].strip()
        content_type = detect_content_type(url, body, header_ct or None)

        if content_type == "application/vnd.apple.mpegurl":
            text = body.decode("utf-8", errors="replace")
            body = rewrite_playlist(text, url, channel_id=channel_id).encode("utf-8")
            content_type = "application/vnd.apple.mpegurl"

        proxy_requests_total.labels(content_type=content_type).inc()

        headers = dict(_CORS_HEADERS)
        headers["Content-Type"] = content_type
        headers["Cache-Control"] = "no-cache" if "mpegurl" in content_type else "public, max-age=60"
        headers["Content-Length"] = str(len(body))

        log.debug("proxy_fetch_ok", url=url[:80], content_type=content_type, bytes=len(body))
        return body, content_type, headers


_client: LiveProxyClient | None = None


def get_proxy_client() -> LiveProxyClient:
    global _client
    if _client is None:
        _client = LiveProxyClient()
    return _client
