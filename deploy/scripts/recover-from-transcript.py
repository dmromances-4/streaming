#!/usr/bin/env python3
"""Rebuild Streaming project files from Cursor agent transcripts."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path("/Users/daniromances/Documents/Proyects/Streaming")
TRANSCRIPT_DIR = Path(
    "/Users/daniromances/.cursor/projects/"
    "Users-daniromances-Documents-Proyects-Streaming/agent-transcripts/"
    "1a21b2a0-6154-448e-8e9d-d871d13b5408"
)


@dataclass
class Stats:
    writes: int = 0
    str_replaces_ok: int = 0
    str_replaces_failed: int = 0
    skipped_paths: int = 0
    files_written: set[str] = field(default_factory=set)
    failed_ops: list[str] = field(default_factory=list)


def iter_ops(transcript_dir: Path):
    files = sorted(transcript_dir.rglob("*.jsonl"))
    for fp in files:
        for line_no, line in enumerate(fp.open(encoding="utf-8"), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message") or {}
            content = msg.get("content") or []
            if isinstance(content, str):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name")
                inp = block.get("input") or {}
                path = inp.get("path")
                if not path or not str(path).startswith(str(PROJECT_ROOT)):
                    continue
                yield fp.name, line_no, name, inp


def apply_write(path: Path, contents: str, files: dict[str, str]) -> None:
    rel = str(path.relative_to(PROJECT_ROOT))
    files[rel] = contents


def apply_str_replace(path: Path, old: str, new: str, files: dict[str, str], stats: Stats) -> None:
    rel = str(path.relative_to(PROJECT_ROOT))
    current = files.get(rel)
    if current is None and path.exists():
        current = path.read_text(encoding="utf-8")
        files[rel] = current
    if current is None:
        stats.str_replaces_failed += 1
        stats.failed_ops.append(f"{rel}: StrReplace before any Write")
        return
    if old not in current:
        stats.str_replaces_failed += 1
        stats.failed_ops.append(f"{rel}: old_string not found")
        return
    files[rel] = current.replace(old, new, 1)
    stats.str_replaces_ok += 1


def flush_files(files: dict[str, str], stats: Stats) -> None:
    for rel, contents in files.items():
        out = PROJECT_ROOT / rel
        if out.is_dir():
            import shutil

            shutil.rmtree(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(contents, encoding="utf-8")
        stats.files_written.add(rel)


def main() -> int:
    if not TRANSCRIPT_DIR.is_dir():
        print(f"Transcript dir missing: {TRANSCRIPT_DIR}", file=sys.stderr)
        return 1

    files: dict[str, str] = {}
    stats = Stats()

    for source, line_no, name, inp in iter_ops(TRANSCRIPT_DIR):
        path = Path(inp["path"])
        if name == "Write":
            apply_write(path, inp.get("contents", ""), files)
            stats.writes += 1
        elif name == "StrReplace":
            apply_str_replace(
                path,
                inp.get("old_string", ""),
                inp.get("new_string", ""),
                files,
                stats,
            )
        else:
            stats.skipped_paths += 1

    flush_files(files, stats)

    print("Recovery complete")
    print(f"  Write ops applied:     {stats.writes}")
    print(f"  StrReplace ok:         {stats.str_replaces_ok}")
    print(f"  StrReplace failed:     {stats.str_replaces_failed}")
    print(f"  Unique files restored: {len(stats.files_written)}")
    if stats.failed_ops:
        print("\nFailed StrReplace (first 20):")
        for item in stats.failed_ops[:20]:
            print(f"  - {item}")
        if len(stats.failed_ops) > 20:
            print(f"  ... and {len(stats.failed_ops) - 20} more")

    return 0 if stats.str_replaces_failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
