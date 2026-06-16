"""Compat: re-exporta Torznab client (antes Jackett-only)."""

from torznab_client import (  # noqa: F401
    TorznabClient,
    build_search_query,
    get_torznab_client,
)

# Alias legacy
JackettClient = TorznabClient
get_jackett_client = get_torznab_client
