"""Telemetría específica del Skill #1."""

from __future__ import annotations

import sys
from pathlib import Path

# Añadir shared/python al path
_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from prometheus_client import Counter, Gauge, Histogram  # noqa: E402

from telemetry import MetricsRegistry, get_logger, setup_logging  # noqa: E402

from config import settings  # noqa: E402

setup_logging(settings.skill_name, settings.log_level)
log = get_logger("ingestion-torrent")

metrics = MetricsRegistry("torrent")

sessions_active = Gauge(
    "torrent_sessions_active",
    "Number of active torrent ingestion sessions",
)

bytes_streamed_total = Counter(
    "torrent_bytes_streamed_total",
    "Total bytes streamed to clients",
)

ingest_duration_seconds = Histogram(
    "torrent_ingest_duration_seconds",
    "Time from session create to first byte streamed",
    buckets=[1, 5, 15, 30, 60, 120, 300],
)

ingest_errors_total = Counter(
    "torrent_ingest_errors_total",
    "Ingestion errors by type",
    ["error_type"],
)


def record_error(error_type: str) -> None:
    ingest_errors_total.labels(error_type=error_type).inc()
    metrics.record_error(error_type)
