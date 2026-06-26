"""Alias de búsqueda torrent por title_id (YAML)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from config import settings


@lru_cache(maxsize=1)
def load_torrent_search_aliases() -> dict[str, list[str]]:
    path = Path(settings.torrent_search_aliases_path)
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, str):
            out[str(key)] = [value]
        elif isinstance(value, list):
            out[str(key)] = [str(v) for v in value if v]
    return out


def get_search_queries_for_title(
    title_id: str,
    *,
    title: str | None = None,
    stored_queries: list[str] | None = None,
) -> list[str]:
    """Combina queries del seed, YAML global y título canónico."""
    seen: set[str] = set()
    queries: list[str] = []

    def add(q: str | None) -> None:
        if not q:
            return
        q = q.strip()
        if not q or q in seen:
            return
        seen.add(q)
        queries.append(q)

    for q in stored_queries or []:
        add(q)
    for q in load_torrent_search_aliases().get(title_id, []):
        add(q)
    add(title)
    return queries


def reload_torrent_search_aliases() -> None:
    load_torrent_search_aliases.cache_clear()
