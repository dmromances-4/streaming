"""Reescritura de playlists M3U8 para proxy CORS."""

from __future__ import annotations

import re
from urllib.parse import quote, urljoin

from config import settings

_URI_ATTR_RE = re.compile(r'URI="([^"]+)"', re.IGNORECASE)


def is_playlist_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def resolve_url(base_url: str, reference: str) -> str:
    return urljoin(base_url, reference)


def proxy_url(target: str, channel_id: str | None = None) -> str:
    encoded = quote(target, safe="")
    base = settings.public_api_base.rstrip("/")
    out = f"{base}/api/v1/fetch?url={encoded}"
    if channel_id:
        out += f"&channel_id={quote(channel_id, safe='')}"
    return out


def _absolute_url(reference: str, base: str) -> str:
    if reference.startswith("http://") or reference.startswith("https://"):
        return reference
    return resolve_url(base, reference)


def rewrite_tag_line(line: str, base: str, channel_id: str | None = None) -> str:
    """Reescribe URI=\"...\" en etiquetas #EXT-X-* (audio, subtítulos, etc.)."""

    def replace_uri(match: re.Match[str]) -> str:
        absolute = _absolute_url(match.group(1), base)
        return f'URI="{proxy_url(absolute, channel_id=channel_id)}"'

    return _URI_ATTR_RE.sub(replace_uri, line)


def rewrite_playlist(
    content: str,
    source_url: str,
    channel_id: str | None = None,
) -> str:
    """Reescribe URIs en M3U8 para pasar por el proxy."""
    base = source_url
    if not base.endswith("/"):
        base = base.rsplit("/", 1)[0] + "/"

    lines_out: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") and 'URI="' in stripped:
            lines_out.append(rewrite_tag_line(line, base, channel_id=channel_id))
            continue
        if not is_playlist_line(stripped):
            lines_out.append(line)
            continue

        absolute = _absolute_url(stripped, base)
        lines_out.append(proxy_url(absolute, channel_id=channel_id))

    return "\n".join(lines_out) + "\n"


def detect_content_type(url: str, body: bytes, header_ct: str | None) -> str:
    if header_ct and "mpegurl" in header_ct.lower():
        return "application/vnd.apple.mpegurl"
    if url.lower().endswith(".m3u8") or b"#EXTM3U" in body[:64]:
        return "application/vnd.apple.mpegurl"
    if header_ct:
        return header_ct
    if url.lower().endswith(".ts"):
        return "video/mp2t"
    return "application/octet-stream"
