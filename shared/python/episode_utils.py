"""Utilidades compartidas para identificar episodios en nombres de archivo."""

from __future__ import annotations

import re


def episode_patterns(season: int, episode: int) -> list[re.Pattern[str]]:
    s = season
    e = episode
    return [
        re.compile(rf"(?i)s0?{s}[ ._-]?e0?{e}\b"),
        re.compile(rf"(?i)\b{s}x0?{e}\b"),
        re.compile(
            rf"(?i)season[ ._-]?0?{s}[ ._-]?(?:episode|ep)[ ._-]?0?{e}\b"
        ),
    ]


def matches_episode_filename(name: str, season: int, episode: int) -> bool:
    return any(p.search(name) for p in episode_patterns(season, episode))


def is_season_pack_filename(name: str, season: int) -> bool:
    lower = name.lower()
    if matches_episode_filename(name, season, 1) and not re.search(
        rf"(?i)s0?{season}[ ._-]?e\d{{2,}}\b", name
    ):
        return False
    pack_markers = [
        rf"(?i)\bs0?{season}\b(?!e)",
        rf"(?i)\bseason[ ._-]?0?{season}\b",
        rf"(?i)\bcomplete[ ._-]?season[ ._-]?0?{season}\b",
    ]
    return any(re.search(m, lower) for m in pack_markers)


def make_episode_id(series_id: str, season: int, episode: int) -> str:
    return f"{series_id}-s{season:02d}e{episode:02d}"
