"""Configuración del Skill #1."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8001
    torrent_cache_dir: str = "/tmp/torrent-cache"
    max_concurrent_sessions: int = 3
    max_buffer_mb: int = 64
    peer_timeout_seconds: int = 120
    download_rate_limit_kb: int = 0
    log_level: str = "INFO"
    skill_name: str = "ingestion-torrent"


settings = Settings()
