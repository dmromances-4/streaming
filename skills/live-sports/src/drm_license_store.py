"""Cache de contexto DRM por canal (license URL + headers)."""

from __future__ import annotations

from dataclasses import dataclass, field

from resolvers.types import DrmInfo


@dataclass
class LicenseContext:
    provider: str
    channel_id: str
    license_url: str
    headers: dict[str, str] = field(default_factory=dict)


_contexts: dict[str, LicenseContext] = {}


def store_license_context(channel_id: str, provider: str, drm: DrmInfo) -> None:
    _contexts[_key(channel_id, provider)] = LicenseContext(
        provider=provider,
        channel_id=channel_id,
        license_url=drm.license_url,
        headers=dict(drm.headers),
    )


def get_license_context(channel_id: str, provider: str) -> LicenseContext | None:
    return _contexts.get(_key(channel_id, provider))


def _key(channel_id: str, provider: str) -> str:
    return f"{provider}:{channel_id}"
