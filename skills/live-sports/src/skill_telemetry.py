"""Telemetría del Skill #3."""

from __future__ import annotations

import sys
from pathlib import Path

_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from prometheus_client import Counter, Histogram  # noqa: E402

from telemetry import MetricsRegistry, get_logger, setup_logging  # noqa: E402

from config import settings  # noqa: E402

setup_logging(settings.skill_name, settings.log_level)
log = get_logger("live-sports")

metrics = MetricsRegistry("live")

proxy_requests_total = Counter(
    "live_proxy_requests_total",
    "Proxied requests",
    ["content_type"],
)

proxy_duration_seconds = Histogram(
    "live_proxy_duration_seconds",
    "Upstream fetch duration",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)


def record_error(error_type: str) -> None:
    metrics.record_error(error_type)
