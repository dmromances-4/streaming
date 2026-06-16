"""Utilidades para playlists HLS (sin dependencias pesadas)."""

from __future__ import annotations

import os
import re

SEGMENT_PATTERN = re.compile(r"segment_\d+\.ts$")


def validate_segment_filename(filename: str) -> bool:
    return bool(SEGMENT_PATTERN.fullmatch(filename))


def rewrite_manifest(
    content: str,
    job_id: str,
    public_api_base: str,
    s3_public_base: str = "",
    s3_prefix: str = "",
) -> str:
    """Reescribe URIs de segmentos para API proxy o CDN directo."""
    if s3_public_base and s3_prefix:
        base = f"{s3_public_base.rstrip('/')}/{s3_prefix}"
    else:
        base = f"{public_api_base.rstrip('/')}/api/v1/segments/{job_id}"
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and stripped.endswith(".ts"):
            filename = os.path.basename(stripped)
            lines.append(f"{base}/{filename}")
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"
