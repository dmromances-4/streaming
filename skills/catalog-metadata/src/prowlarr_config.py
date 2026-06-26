"""Lee la API key local de Prowlarr desde config.xml (sin registro externo)."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

from skill_telemetry import log

_API_KEY_RE = re.compile(r"<ApiKey>([^<]+)</ApiKey>")


def _config_paths() -> list[Path]:
    paths: list[Path] = []
    env_path = os.environ.get("PROWLARR_CONFIG_PATH", "").strip()
    if env_path:
        paths.append(Path(env_path))
    paths.extend(
        [
            Path("/prowlarr-config/config.xml"),
            Path("/config/config.xml"),
        ]
    )
    return paths


@lru_cache(maxsize=1)
def get_prowlarr_api_key_from_config() -> str:
    for path in _config_paths():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        match = _API_KEY_RE.search(text)
        if match:
            key = match.group(1).strip()
            if key:
                log.info("prowlarr_api_key_loaded", source=str(path))
                return key
    return ""


def resolve_indexer_api_key(env_key: str) -> str:
    if env_key and env_key.strip():
        return env_key.strip()
    return get_prowlarr_api_key_from_config()


def reload_prowlarr_config() -> None:
    get_prowlarr_api_key_from_config.cache_clear()
