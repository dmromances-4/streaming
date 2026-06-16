"""Resolvers de streams en vivo."""

from resolvers.registry import resolve_channel
from resolvers.static_resolver import resolve_static_channel
from resolvers.types import DrmInfo, StreamResult

__all__ = ["DrmInfo", "StreamResult", "resolve_channel", "resolve_static_channel"]
