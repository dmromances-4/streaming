"""Tests unitarios Skill #6."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_src = Path(__file__).resolve().parents[1] / "src"
_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
for p in (str(_src), str(_shared)):
    if p not in sys.path:
        sys.path.insert(0, p)


def test_strip_cocteleria():
    from text_utils import strip_markup

    title, notes, tags = strip_markup(
        "Mad Men [COCTELERÍA] (Esencial: Old Fashioned)"
    )
    assert title == "Mad Men"
    assert "cocteleria" in tags
    assert notes is not None


def test_normalize_and_slug():
    from text_utils import make_slug, normalize_title

    assert normalize_title("El Padrino") == "el padrino"
    slug = make_slug("movie", "american", "Pulp Fiction")
    assert slug.startswith("movie-american-")


def test_build_search_query():
    from torznab_client import build_search_query

    assert "S01" in build_search_query("Breaking Bad", "series")
    assert "1080p" in build_search_query("Casablanca", "movie")
    assert "1960" in build_search_query("Casablanca", "movie", year=1960)


def test_parse_entry():
    from seed_importer import _parse_entry

    row = _parse_entry("Boardwalk Empire [COCTELERÍA]", "series", "american")
    assert row is not None
    assert row["priority"] == 1
    assert "cocteleria" in row["tags"]


def test_indexer_url_prowlarr():
    from config import Settings

    s = Settings(indexer_provider="prowlarr", indexer_url="http://prowlarr:9696")
    assert "prowlarr" in s.effective_indexer_url


def test_build_episode_query():
    from torznab_client import build_episode_query, build_episode_query_variants

    q = build_episode_query("Breaking Bad", 1, 3, year=2008)
    assert "S01E03" in q
    assert "Breaking Bad" in q
    assert "2008" not in q

    variants = build_episode_query_variants("La Casa de Papel", 2, 5)
    assert variants[0] == "La Casa de Papel S02E05"
    assert any("S02E05" in v for v in variants)
    assert variants[-1] == "La Casa de Papel S02E05 x265"

    with_year = build_episode_query_variants("Breaking Bad", 1, 2, year=2008)
    assert with_year[0] == "Breaking Bad S01E02"
    assert with_year[-1] == "Breaking Bad 2008 S01E02 1080p"


def test_episode_filename_matching():
    import sys
    from pathlib import Path

    shared = Path(__file__).resolve().parents[3] / "shared" / "python"
    if str(shared) not in sys.path:
        sys.path.insert(0, str(shared))

    from episode_utils import make_episode_id, matches_episode_filename

    assert matches_episode_filename("Show.S01E03.1080p.mkv", 1, 3)
    assert matches_episode_filename("Show.1x03.WEB-DL.mp4", 1, 3)
    assert not matches_episode_filename("Show.S02E03.1080p.mkv", 1, 3)
    assert make_episode_id("series-spanish-la-casa", 1, 3) == "series-spanish-la-casa-s01e03"


def test_score_episode_item():
    from torznab_client import _score_episode_item

    high = _score_episode_item("Show.S01E03.1080p.WEB-DL", 900_000_000, 50, 1, 3)
    low = _score_episode_item("Show.Complete.Season.1.1080p", 5_000_000_000, 50, 1, 3)
    assert high > low

    breaking_bad = _score_episode_item(
        "Breaking Bad S01E02 Cats in the Bag 1080p WEB-DL",
        900_000_000,
        10,
        1,
        2,
        series_title="Breaking Bad",
    )
    wrong_show = _score_episode_item(
        "The Bad Guys Breaking In S01E02 1080p WEB-DL",
        900_000_000,
        50,
        1,
        2,
        series_title="Breaking Bad",
    )
    assert breaking_bad > wrong_show
    assert breaking_bad > 0

    no_episode_match = _score_episode_item(
        "Breaking Bad Complete Season 1 1080p",
        900_000_000,
        0,
        1,
        2,
        series_title="Breaking Bad",
    )
    assert no_episode_match <= 0
    assert breaking_bad > no_episode_match
