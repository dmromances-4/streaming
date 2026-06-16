"""Normalización de títulos y generación de slugs."""

from __future__ import annotations

import re
import unicodedata

COCTELERIA_RE = re.compile(r"\[COCTELERÍA\]", re.IGNORECASE)
PARENS_RE = re.compile(r"\s*\(([^)]*)\)\s*")
BRACKET_NOTE_RE = re.compile(r"\s*\[([^\]]*)\]\s*")


def strip_markup(raw: str) -> tuple[str, str | None, list[str]]:
    """Extrae título limpio, notas y tags de una línea."""
    tags: list[str] = []
    notes: str | None = None

    if COCTELERIA_RE.search(raw):
        tags.append("cocteleria")
    raw = COCTELERIA_RE.sub("", raw).strip()

    paren = PARENS_RE.search(raw)
    if paren:
        notes = paren.group(1).strip()
        raw = PARENS_RE.sub(" ", raw).strip()

    bracket = BRACKET_NOTE_RE.search(raw)
    if bracket and not notes:
        notes = bracket.group(1).strip()
    raw = BRACKET_NOTE_RE.sub(" ", raw).strip()

    return raw.strip(), notes or None, tags


def normalize_title(title: str) -> str:
    t = unicodedata.normalize("NFKD", title)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().strip()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def make_slug(content_type: str, origin: str, title: str) -> str:
    norm = normalize_title(title)
    slug = re.sub(r"[^a-z0-9]+", "-", norm).strip("-")
    return f"{content_type}-{origin}-{slug}"[:120]
