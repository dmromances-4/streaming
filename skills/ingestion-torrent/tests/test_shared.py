"""Tests de módulos compartidos (sin libtorrent)."""

from __future__ import annotations

import sys
from pathlib import Path

_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))


def test_invalid_magnet_error():
    from errors import InvalidMagnetError

    exc = InvalidMagnetError("bad magnet")
    assert exc.http_status == 400
    assert exc.error_type == "invalid_magnet"


def test_session_not_found_error():
    from errors import SessionNotFoundError

    exc = SessionNotFoundError("missing")
    assert exc.http_status == 404
    assert exc.error_type == "session_not_found"


def test_metrics_registry():
    from telemetry import MetricsRegistry

    registry = MetricsRegistry("test_skill")
    registry.record_error("test_error")
    registry.record_request("GET", "/health", 200)
    exported = registry.export().decode()
    assert "test_skill_errors_total" in exported
    assert "test_skill_requests_total" in exported


def test_parse_range_header():
    _src = Path(__file__).resolve().parents[1] / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

    from stream_reader import parse_range_header

    assert parse_range_header("bytes=0-1023", 5000) == (0, 1023)
    assert parse_range_header("bytes=100-", 5000) == (100, 4999)
    assert parse_range_header("bytes=-500", 5000) == (4500, 4999)
    assert parse_range_header(None, 5000) is None
