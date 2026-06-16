"""Telemetría específica del Skill #2."""

from __future__ import annotations

import sys
from pathlib import Path

_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from prometheus_client import Counter, Gauge, Histogram  # noqa: E402

from telemetry import MetricsRegistry, get_logger, setup_logging  # noqa: E402

from config import settings  # noqa: E402

setup_logging(settings.skill_name, settings.log_level)
log = get_logger("storage-hls")

metrics = MetricsRegistry("hls")

jobs_active = Gauge(
    "hls_jobs_active",
    "Active HLS transcode jobs",
)

segments_uploaded_total = Counter(
    "hls_segments_uploaded_total",
    "HLS segments uploaded to S3",
)

transcode_duration_seconds = Histogram(
    "hls_transcode_duration_seconds",
    "Total transcode job duration",
    buckets=[30, 60, 300, 600, 1800, 3600],
)


def record_error(error_type: str) -> None:
    metrics.record_error(error_type)
