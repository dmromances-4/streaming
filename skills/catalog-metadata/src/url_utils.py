"""Utilidades de URLs públicas (manifest HLS)."""

from __future__ import annotations

import re

from config import settings

_MANIFEST_PATH_RE = re.compile(
    r"(?:https?://[^/]+)?(/api/hls/api/v1/manifest/[^?\s]+)"
)


def build_manifest_url(job_id: str) -> str:
    base = settings.public_hls_base.rstrip("/")
    if not base or base.startswith("/"):
        return f"{base or '/api/hls'}/api/v1/manifest/{job_id}"
    return f"{base}/api/v1/manifest/{job_id}"


def normalize_manifest_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    match = _MANIFEST_PATH_RE.search(url)
    if match:
        return match.group(1)
    if url.startswith("/api/hls/"):
        return url
    return url
