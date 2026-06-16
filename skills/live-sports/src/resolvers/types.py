"""Tipos compartidos para resolvers de canales en vivo."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DrmInfo:
    scheme: str
    license_url: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class StreamResult:
    manifest_url: str | None = None
    error: str | None = None
    manifest_type: str = "hls"
    drm: DrmInfo | None = None
    requirements: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.manifest_url) and not self.error
