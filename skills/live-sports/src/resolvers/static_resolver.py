"""Resolver para canales con URL HLS fija en el catálogo."""

from __future__ import annotations

from typing import Any

from resolvers.types import StreamResult


def resolve_static_channel(channel: dict[str, Any]) -> StreamResult:
    url = (channel.get("stream_url") or "").strip()
    if not url:
        return StreamResult(error="Canal sin stream_url configurada")
    if not url.startswith(("http://", "https://")):
        return StreamResult(error="stream_url inválida")
    return StreamResult(manifest_url=url)
