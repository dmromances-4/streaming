"""Importación de YAML semilla al catálogo SQLite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config import settings
from db.repository import CatalogRepository
from skill_telemetry import log
from text_utils import make_slug, normalize_title, strip_markup


def _parse_entry(
    entry: Any,
    content_type: str,
    origin: str,
) -> dict[str, Any] | None:
    if isinstance(entry, str):
        title_raw = entry
        extra_tags: list[str] = []
        extra_notes = None
        extra_queries: list[str] = []
    elif isinstance(entry, dict) and "title" in entry:
        title_raw = entry["title"]
        extra_tags = entry.get("tags", [])
        extra_notes = entry.get("notes")
        extra_queries = entry.get("search_queries", []) or []
    else:
        return None

    title, notes, tags = strip_markup(title_raw)
    if not title or len(title) < 2:
        return None

    if extra_tags:
        tags = list(set(tags + extra_tags))
    if extra_notes and not notes:
        notes = extra_notes

    priority = 1 if "cocteleria" in tags else 0

    return {
        "id": make_slug(content_type, origin, title),
        "content_type": content_type,
        "origin": origin,
        "title": title,
        "title_normalized": normalize_title(title),
        "tags": tags,
        "priority": priority,
        "notes": notes,
        "search_queries": [str(q) for q in extra_queries if q],
    }


def _file_meta(filename: str) -> tuple[str, str] | None:
    name = filename.replace(".yaml", "").replace(".yml", "")
    parts = name.split("-", 1)
    if len(parts) != 2:
        return None
    content_type, origin = parts
    if content_type not in ("series", "movies"):
        return None
    ct = "movie" if content_type == "movies" else "series"
    if origin not in ("american", "european", "spanish", "catalan"):
        return None
    return ct, origin


async def import_seed_dir(
    repo: CatalogRepository,
    seed_dir: str | None = None,
) -> dict[str, int]:
    path = Path(seed_dir or settings.seed_dir)
    if not path.is_dir():
        raise FileNotFoundError(f"Seed directory not found: {path}")

    inserted = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    seen_global: set[str] = set()

    for yaml_file in sorted(path.glob("*.yaml")):
        meta = _file_meta(yaml_file.name)
        if not meta:
            log.warning("skip_seed_file", file=yaml_file.name)
            continue

        content_type, origin = meta
        entries = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or []

        for entry in entries:
            row = _parse_entry(entry, content_type, origin)
            if not row:
                skipped_invalid += 1
                continue

            dedup_key = f"{row['content_type']}:{row['origin']}:{row['title_normalized']}"
            if dedup_key in seen_global:
                skipped_duplicates += 1
                continue
            seen_global.add(dedup_key)

            ok = await repo.insert_title(row)
            if ok:
                inserted += 1
            else:
                skipped_duplicates += 1

        log.info(
            "seed_file_imported",
            file=yaml_file.name,
            entries=len(entries),
        )

    await repo.record_import_run("seed", inserted, skipped_duplicates, skipped_invalid)
    return {
        "inserted": inserted,
        "skipped_duplicates": skipped_duplicates,
        "skipped_invalid": skipped_invalid,
    }
