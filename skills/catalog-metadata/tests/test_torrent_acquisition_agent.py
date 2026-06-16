"""Tests del agente de adquisición torrent."""

from __future__ import annotations

import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1] / "src"
_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
for p in (str(_src), str(_shared)):
    if p not in sys.path:
        sys.path.insert(0, p)

from torrent_acquisition_agent import TorrentCandidate, format_acquire_response
from torznab_client import (
    _score_episode_item,
    is_safe_torrent_title,
    normalize_search_title,
)


def test_normalize_search_title_strips_accents():
    assert normalize_search_title("Córdoba") == "Cordoba"
    assert normalize_search_title("Niño") == "Nino"
    assert "Boardwalk" in normalize_search_title("Boardwalk Empire")


def test_is_safe_torrent_rejects_exe_and_cam():
    assert not is_safe_torrent_title("Show.S01E01.setup.exe")
    assert not is_safe_torrent_title("Show.S01E01.CAMRip.1080p.mkv")
    assert not is_safe_torrent_title("Show.S01E01.TELESYNC.720p.mkv")
    assert not is_safe_torrent_title("Show.S01E01.720p.zip")


def test_is_safe_torrent_accepts_video_release():
    assert is_safe_torrent_title("Boardwalk.Empire.S01E05.1080p.WEB-DL.x264.mkv")


def test_score_episode_rejects_low_seeders():
    title = "Boardwalk Empire S01E05 1080p WEB-DL x264.mkv"
    low = _score_episode_item(
        title, 800_000_000, 3, 1, 5, series_title="Boardwalk Empire", min_seeders=10
    )
    high = _score_episode_item(
        title, 800_000_000, 15, 1, 5, series_title="Boardwalk Empire", min_seeders=10
    )
    assert low < 0
    assert high > 0


def test_score_episode_prefers_1080p_over_cam():
    good = "Boardwalk Empire S01E05 1080p WEB-DL x265.mkv"
    bad = "Boardwalk Empire S01E05 CAMRip.mkv"
    good_score = _score_episode_item(
        good, 900_000_000, 20, 1, 5, series_title="Boardwalk Empire"
    )
    bad_score = _score_episode_item(
        bad, 900_000_000, 50, 1, 5, series_title="Boardwalk Empire"
    )
    assert good_score > bad_score


def test_torrent_candidate_user_message():
    c = TorrentCandidate(
        title="Test S01E01 1080p.mkv",
        magnet="magnet:?xt=urn:btih:abc",
        size_bytes=1_073_741_824,
        seeders=25,
    )
    msg = c.user_message()
    assert "Descargando" in msg
    assert "1.00 GB" in msg
    assert "25" in msg


def test_format_acquire_response():
    c = TorrentCandidate(
        title="Test S01E01",
        magnet="magnet:?xt=urn:btih:abc",
        size_bytes=500_000_000,
        seeders=12,
    )
    resp = format_acquire_response(c)
    assert resp["torrent_title"] == "Test S01E01"
    assert resp["seeders"] == 12
    assert "message" in resp
