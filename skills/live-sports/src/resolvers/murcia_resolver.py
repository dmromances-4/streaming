"""Resuelve streams en vivo de 7 Región de Murcia."""

from __future__ import annotations

from typing import Any

from resolvers._scrape_utils import resolve_scrape_channel
from resolvers.types import StreamResult


async def resolve_murcia_channel(channel: dict[str, Any]) -> StreamResult:
    page_url = (
        channel.get("page_url") or "https://www.7tvregiondemurcia.es/directo/"
    ).strip()
    return await resolve_scrape_channel(
        channel,
        page_url=page_url,
        headers={"Referer": "https://www.7tvregiondemurcia.es/"},
    )
