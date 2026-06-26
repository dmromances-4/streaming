#!/usr/bin/env python3
"""Build watchlist.json from agent transcript user message."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPT = Path(
    r"C:\Users\Administrator\.cursor\projects\empty-window\agent-transcripts"
    r"\f9f048bc-1cd6-4423-90aa-9a74ded48744\f9f048bc-1cd6-4423-90aa-9a74ded48744.jsonl"
)
OUT = ROOT / "catalog" / "data" / "watchlist.json"

CAT_ALIASES: dict[str, list[str]] = {
    "Pa negre": ["Pa negre", "Black Bread"],
    "Estiu 1993": ["Estiu 1993", "Verano 1993"],
    "Alcarràs": ["Alcarras 2022"],
    "El fotógrafo de Mauthausen": ["El fotografo de Mauthausen"],
    "Incerta Glòria": ["Incerta gloria"],
    "Barcelona, nit d'estiu": ["Barcelona nit d estiu"],
    "Barcelona, nit d'hivern": ["Barcelona nit d hivern"],
    "La propera pell": ["La propera pell"],
    "Els dies que vindran": ["Els dies que vindran"],
    "Libertad": ["Libertad 2021 Clara Roquet"],
    "Creatura": ["Creatura 2023"],
    "Saben aquell": ["Saben aquell 2023"],
    "Casa en flames": ["Casa en flames 2024"],
    "El bosc": ["El bosc 2012"],
    "Fènix 11*23": ["Fenix 11 23"],
    "Segon origen": ["Segon origen"],
    "El camí més llarg per tornar a casa": ["El cami mes llarg per tornar a casa"],
    "Fill de Caín": ["Fill de Cain"],
    "Jean-François i el sentit de la vida": ["Jean-Francois i el sentit de la vida"],
    "Suro": ["Suro 2022"],
    "Las niñas": ["Las ninas 2020 Inicia Films"],
    "La Maternal": ["La Maternal 2022"],
    "One Year, One Night": ["One Year One Night", "Un ano una noche"],
    "Una pistola en cada mano": ["Una pistola en cada mano"],
    "En la ciudad": ["En la ciudad Cesc Gay"],
    "Ficció": ["Ficcio Cesc Gay"],
    "Sentimental": ["Sentimental 2020"],
    "Krámpack": ["Krampack"],
    "V.O.S.": ["VOS Cesc Gay"],
    "Truman": ["Truman Cesc Gay"],
    "Tres dies amb la família": ["Tres dies amb la familia"],
    "Tots volem el mejor per a ella": ["Tots volem el millor per a ella"],
    "Blog": ["Blog Elena Trape"],
    "Las distancias": ["Las distancias Elena Trape"],
    "Els encantats": ["Els encantats"],
    "Júlia ist": ["Julia ist"],
}

SECTIONS = {
    "series-american": "1. Series Americanas",
    "series-european": "2. Series Europeas",
    "series-spanish": "3. Series Españolas",
    "series-catalan": "4. Series Catalanas",
    "movies-american": "1. Películas Americanas",
    "movies-european": "2. Películas Europeas",
    "movies-spanish": "3. Películas Españolas",
    "movies-catalan": "4. Películas Catalanas",
}


def clean_title(line: str) -> str:
    t = re.sub(r"\s*\[COCTELERÍA\].*", "", line, flags=re.IGNORECASE)
    t = re.sub(r"\s*\[COCTELERIA\].*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def load_transcript_text() -> str:
    if not TRANSCRIPT.is_file():
        raise FileNotFoundError(TRANSCRIPT)
    for line in TRANSCRIPT.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = obj.get("message", {}).get("content", [])
        for block in content:
            if block.get("type") == "text" and "PARTE 1" in block.get("text", ""):
                return block["text"]
    raise RuntimeError("Watchlist text not found in transcript")


def parse_section(text: str, marker: str) -> list[dict]:
    lines = text.splitlines()
    in_section = False
    items: list[dict] = []
    for line in lines:
        s = line.strip()
        if marker in s:
            in_section = True
            continue
        if in_section and re.match(r"^\d+\.\s", s) and marker not in s:
            break
        if in_section and s.startswith("PARTE "):
            break
        if not in_section or not s:
            continue
        if s.startswith("-") or s.startswith("PARTE"):
            continue
        coct = "cocteleria" in line.lower()
        title = clean_title(s)
        if len(title) < 2:
            continue
        entry: dict = {"title": title}
        if coct:
            entry["tags"] = ["cocteleria"]
        items.append(entry)
    return items


def dedupe(entries: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for entry in entries:
        key = entry["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def apply_catalan_aliases(entries: list[dict]) -> None:
    for entry in entries:
        title = entry["title"]
        base = title.split("(")[0].strip()
        for key, queries in CAT_ALIASES.items():
            if key.lower() in title.lower() or key.lower() == base.lower():
                entry["search_queries"] = queries
                break


def main() -> int:
    text = load_transcript_text()
    out: dict[str, list[dict]] = {}
    for key, marker in SECTIONS.items():
        entries = dedupe(parse_section(text, marker))
        if key == "movies-catalan":
            apply_catalan_aliases(entries)
        out[key] = entries
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in out.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
