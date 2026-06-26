#!/usr/bin/env python3
"""Genera catalog/data/seed/*.yaml desde catalog/data/watchlist.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WATCHLIST = ROOT / "catalog" / "data" / "watchlist.json"
SEED_DIR = ROOT / "catalog" / "data" / "seed"
ALIASES = ROOT / "catalog" / "data" / "torrent-search-aliases.yaml"


def entry_to_yaml(entry: str | dict) -> str:
    if isinstance(entry, str):
        return f"- {json.dumps(entry, ensure_ascii=False)}"
    title = entry["title"]
    parts = [f"title: {json.dumps(title, ensure_ascii=False)}"]
    if entry.get("tags"):
        tags = ", ".join(json.dumps(t, ensure_ascii=False) for t in entry["tags"])
        parts.append(f"tags: [{tags}]")
    if entry.get("search_queries"):
        qs = ", ".join(json.dumps(q, ensure_ascii=False) for q in entry["search_queries"])
        parts.append(f"search_queries: [{qs}]")
    return "-\n  " + "\n  ".join(parts)


def write_seed_file(key: str, entries: list) -> int:
    if key.startswith("series-"):
        filename = f"{key}.yaml"
    elif key.startswith("movies-"):
        filename = f"{key}.yaml"
    else:
        raise ValueError(key)
    path = SEED_DIR / filename
    body = "\n".join(entry_to_yaml(e) for e in entries) + "\n"
    path.write_text(body, encoding="utf-8")
    return len(entries)


def write_aliases(data: dict) -> int:
    aliases: dict[str, list[str]] = {}
    for key, entries in data.items():
        if not key.startswith("movies-"):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            queries = entry.get("search_queries") or []
            if not queries:
                continue
            origin = key.replace("movies-", "")
            title = entry["title"]
            slug = title.lower()
            for ch in "àáâãäåèéêëìíîïòóôõöùúûüñç":
                slug = slug.replace(ch, "")
            slug = "".join(c if c.isalnum() else "-" for c in slug)
            slug = "-".join(p for p in slug.split("-") if p)
            title_id = f"movie-{origin}-{slug}"
            aliases[title_id] = list(dict.fromkeys(queries))

    lines: list[str] = []
    for title_id in sorted(aliases):
        lines.append(f"{title_id}:")
        for q in aliases[title_id]:
            lines.append(f"  - {json.dumps(q, ensure_ascii=False)}")
    ALIASES.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(aliases)


def main() -> int:
    if not WATCHLIST.is_file():
        print(f"Missing {WATCHLIST}", file=sys.stderr)
        return 1
    data = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    counts = {}
    for key, entries in data.items():
        counts[key] = write_seed_file(key, entries)
    alias_count = write_aliases(data)
    print(json.dumps({"seed_files": counts, "aliases": alias_count}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
