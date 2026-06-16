"""Tests de selección de archivo por episodio."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_src = Path(__file__).resolve().parents[1] / "src"
_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
for p in (str(_src), str(_shared)):
    if p not in sys.path:
        sys.path.insert(0, p)

libtorrent = pytest.importorskip("libtorrent", reason="libtorrent required — use Docker")

from episode_utils import matches_episode_filename  # noqa: E402


def test_matches_episode_filename_patterns():
    assert matches_episode_filename("Breaking.Bad.S01E02.720p.mkv", 1, 2)
    assert matches_episode_filename("breaking bad 1x02.mp4", 1, 2)
    assert not matches_episode_filename("Breaking.Bad.S01E03.mkv", 1, 2)
