"""Registry de resolvers de canales en vivo."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Union

from resolvers.bbc_iplayer_resolver import resolve_bbc_iplayer_channel
from resolvers.brightcove_resolver import resolve_brightcove_channel
from resolvers.ccma_resolver import resolve_ccma_channel
from resolvers.clm_resolver import resolve_clm_channel
from resolvers.cyltv_resolver import resolve_cyltv_channel
from resolvers.france_tv_resolver import resolve_france_tv_channel
from resolvers.ib3_resolver import resolve_ib3_channel
from resolvers.murcia_resolver import resolve_murcia_channel
from resolvers.navarra_resolver import resolve_navarra_channel
from resolvers.rai_resolver import resolve_rai_channel
from resolvers.rtve_resolver import resolve_rtve_channel
from resolvers.static_resolver import resolve_static_channel
from resolvers.tpa_resolver import resolve_tpa_channel
from resolvers.trc_resolver import resolve_trc_channel
from resolvers.tvg_resolver import resolve_tvg_channel
from resolvers.types import StreamResult

ResolverFn = Callable[[dict[str, Any]], Union[Awaitable[StreamResult], StreamResult]]

_RESOLVERS: dict[str, ResolverFn] = {
    "static": resolve_static_channel,
    "rtve": resolve_rtve_channel,
    "france_tv": resolve_france_tv_channel,
    "rai": resolve_rai_channel,
    "bbc_iplayer": resolve_bbc_iplayer_channel,
    "brightcove": resolve_brightcove_channel,
    "ccma": resolve_ccma_channel,
    "ib3": resolve_ib3_channel,
    "tvg": resolve_tvg_channel,
    "cyltv": resolve_cyltv_channel,
    "murcia": resolve_murcia_channel,
    "navarra": resolve_navarra_channel,
    "tpa": resolve_tpa_channel,
    "trc": resolve_trc_channel,
    "clm": resolve_clm_channel,
}


async def resolve_channel(channel: dict[str, Any]) -> StreamResult:
    name = channel.get("resolver", "static")
    if name == "rtve":
        slug = channel.get("slug", "")
        if not slug:
            return StreamResult(error="Canal RTVE sin slug")
        return await resolve_rtve_channel(slug)

    resolver = _RESOLVERS.get(name)
    if not resolver:
        return StreamResult(error=f"Resolver no soportado: {name}")

    result = resolver(channel)
    if hasattr(result, "__await__"):
        return await result
    return result
