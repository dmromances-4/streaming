"""Telemetría compartida: logging estructurado y helpers Prometheus."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from prometheus_client import Counter, Gauge, Histogram, generate_latest


def setup_logging(skill_name: str, level: str = "INFO") -> None:
    """Configura structlog con salida JSON en stdout."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(skill=skill_name)


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name)


class MetricsRegistry:
    """Registro mínimo de métricas reutilizable por Skill."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.errors_total = Counter(
            f"{prefix}_errors_total",
            "Total errors by type",
            ["error_type"],
        )
        self.requests_total = Counter(
            f"{prefix}_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )

    def record_error(self, error_type: str) -> None:
        self.errors_total.labels(error_type=error_type).inc()

    def record_request(self, method: str, endpoint: str, status: int) -> None:
        self.requests_total.labels(
            method=method, endpoint=endpoint, status=str(status)
        ).inc()

    def export(self) -> bytes:
        return generate_latest()


def histogram(name: str, description: str, labels: list[str] | None = None) -> Histogram:
    return Histogram(name, description, labels or [])


def gauge(name: str, description: str, labels: list[str] | None = None) -> Gauge:
    return Gauge(name, description, labels or [])


def counter(name: str, description: str, labels: list[str] | None = None) -> Counter:
    return Counter(name, description, labels or [])
