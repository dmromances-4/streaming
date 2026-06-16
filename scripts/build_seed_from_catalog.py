#!/usr/bin/env python3
"""Build YAML seed files from catalog_data.CATALOG."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from catalog_data import CATALOG  # noqa: E402

COCTELERIA_RE = re.compile(r"\[COCTELERÍA\]", re.IGNORECASE)
PARENS_RE = re.compile(r"\s*\(([^)]*)\)\s*")
BRACKET_NOTE_RE = re.compile(r"\s*\[([^\]]*)\]\s*")

ROOT = SCRIPT_DIR.parent
SEED_DIR = ROOT / "catalog" / "data" / "seed"
REPORT_PATH = SEED_DIR / "report.json"


def parse_title(raw: str) -> dict:
    """Split markup into title, optional notes, and tags."""
    tags: list[str] = []
    notes: str | None = None

    if COCTELERIA_RE.search(raw):
        tags.append("cocteleria")
    cleaned = COCTELERIA_RE.sub("", raw).strip()

    paren = PARENS_RE.search(cleaned)
    if paren:
        notes = paren.group(1).strip()
        cleaned = PARENS_RE.sub(" ", cleaned).strip()

    bracket = BRACKET_NOTE_RE.search(cleaned)
    if bracket and not notes:
        note_text = bracket.group(1).strip()
        if note_text.upper() != "COCTELERÍA":
            notes = note_text
    cleaned = BRACKET_NOTE_RE.sub(" ", cleaned).strip()

    entry: dict = {"title": cleaned.strip()}
    if tags:
        entry["tags"] = tags
    if notes:
        entry["notes"] = notes
    return entry


def normalize_key(title: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFKD", title.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def dump_yaml(entries: list[dict]) -> str:
    lines: list[str] = []
    for entry in entries:
        lines.append("- title: " + json.dumps(entry["title"], ensure_ascii=False))
        if "tags" in entry:
            tags = ", ".join(entry["tags"])
            lines.append(f"  tags: [{tags}]")
        if "notes" in entry:
            lines.append("  notes: " + json.dumps(entry["notes"], ensure_ascii=False))
    return "\n".join(lines) + "\n"


def dedupe_entries(entries: list[dict]) -> tuple[list[dict], int]:
    seen: set[str] = set()
    deduped: list[dict] = []
    removed = 0
    for entry in entries:
        key = normalize_key(entry["title"])
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped, removed


def main() -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "files": {},
        "totals": {
            "entries": 0,
            "cocteleria": 0,
            "duplicates_removed": 0,
        },
    }

    for key, titles in CATALOG.items():
        parsed = [parse_title(t) for t in titles]
        entries, removed = dedupe_entries(parsed)
        cocteleria_count = sum(1 for e in entries if "cocteleria" in e.get("tags", []))

        out_path = SEED_DIR / f"{key}.yaml"
        out_path.write_text(dump_yaml(entries), encoding="utf-8")

        report["files"][key] = {
            "path": str(out_path.relative_to(ROOT)),
            "count": len(entries),
            "cocteleria": cocteleria_count,
            "duplicates_removed": removed,
        }
        report["totals"]["entries"] += len(entries)
        report["totals"]["cocteleria"] += cocteleria_count
        report["totals"]["duplicates_removed"] += removed

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
