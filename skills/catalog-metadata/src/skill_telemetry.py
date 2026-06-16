"""Telemetría del Skill #6."""

from __future__ import annotations

import sys
from pathlib import Path

_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from prometheus_client import Counter, Gauge  # noqa: E402

from telemetry import MetricsRegistry, get_logger, setup_logging  # noqa: E402

from config import settings  # noqa: E402

setup_logging(settings.skill_name, settings.log_level)
log = get_logger("catalog-metadata")

metrics = MetricsRegistry("catalog")

titles_ready = Gauge("catalog_titles_ready", "Titles with pipeline_status=ready")
titles_priority = Gauge("catalog_titles_priority", "Priority (cocteleria) titles")
batch_ingest_total = Counter(
    "catalog_batch_ingest_total",
    "Batch ingest outcomes",
    ["result"],
)
resolve_magnets_total = Counter(
    "catalog_resolve_magnets_total",
    "Magnet resolve outcomes",
    ["result"],
)


def record_error(error_type: str) -> None:
    metrics.record_error(error_type)
