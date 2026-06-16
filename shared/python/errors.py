"""Jerarquía de excepciones compartida entre Skills."""

from __future__ import annotations


class SkillError(Exception):
    """Base para errores de dominio en cualquier Skill."""

    http_status: int = 500
    error_type: str = "skill_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidInputError(SkillError):
    http_status = 400
    error_type = "invalid_input"


class NotFoundError(SkillError):
    http_status = 404
    error_type = "not_found"


class TimeoutError(SkillError):
    http_status = 504
    error_type = "timeout"


class StorageExhaustedError(SkillError):
    http_status = 507
    error_type = "storage_exhausted"


class RateLimitError(SkillError):
    http_status = 429
    error_type = "rate_limit"


# --- Skill #1 specific ---


class InvalidMagnetError(InvalidInputError):
    error_type = "invalid_magnet"


class SessionNotFoundError(NotFoundError):
    error_type = "session_not_found"


class PeerTimeoutError(TimeoutError):
    error_type = "peer_timeout"


class MaxSessionsError(RateLimitError):
    error_type = "max_sessions"


# --- Skill #2 specific ---


class JobNotFoundError(NotFoundError):
    error_type = "job_not_found"


class TranscodeError(SkillError):
    http_status = 500
    error_type = "transcode_error"


class S3ConnectionError(SkillError):
    http_status = 503
    error_type = "s3_connection_error"


class MaxJobsError(RateLimitError):
    error_type = "max_jobs"


# --- Skill #3 specific ---


class InvalidUrlError(InvalidInputError):
    error_type = "invalid_url"


class UpstreamError(SkillError):
    http_status = 502
    error_type = "upstream_error"


class ProxyTimeoutError(TimeoutError):
    error_type = "proxy_timeout"


class VPNNotReadyError(SkillError):
    http_status = 503
    error_type = "vpn_not_ready"
