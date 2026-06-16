"""Configuración del Skill #6."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8004
    skill_name: str = "catalog-metadata"
    log_level: str = "INFO"

    database_path: str = "/data/catalog.db"
    seed_dir: str = "/app/catalog/data/seed"
    cocktails_dir: str = "/app/catalog/data/cocktails"

    # Indexer (Torznab — Jackett o Prowlarr)
    indexer_provider: Literal["jackett", "prowlarr"] = "prowlarr"
    indexer_url: str = "http://prowlarr:9696"
    indexer_api_key: str = ""
    # Legacy aliases
    jackett_url: str = "http://jackett:9117"
    jackett_api_key: str = ""

    # TMDB
    tmdb_api_key: str = ""
    tmdb_language: str = "es-ES"
    tmdb_image_base: str = "https://image.tmdb.org/t/p/w500"

    # Fuente de medios: torrent, library o hybrid (biblioteca + adquisición torrent)
    media_source_mode: Literal["torrent", "library", "hybrid"] = "hybrid"
    torrent_min_seeders: int = 10
    torrent_prefer_hevc: bool = False
    auto_acquire_on_play: bool = True
    media_root: str = "/media"
    media_url_base: str = ""
    media_aliases_path: str = "/app/catalog/data/media-aliases.yaml"
    library_bootstrap_series_ids: str = ""

    @property
    def bootstrap_series_id_list(self) -> list[str]:
        if not self.library_bootstrap_series_ids.strip():
            return []
        return [
            s.strip()
            for s in self.library_bootstrap_series_ids.split(",")
            if s.strip()
        ]

    # Ingesta híbrida
    ingest_mode: Literal["qbittorrent", "stream", "auto"] = "auto"
    qbittorrent_url: str = "http://qbittorrent:8080"
    qbittorrent_user: str = "admin"
    qbittorrent_pass: str = "adminadmin"
    qbittorrent_download_path: str = "/downloads"
    qbittorrent_timeout_seconds: int = 7200

    ingestion_base_url: str = "http://ingestion-torrent:8001"
    storage_hls_base_url: str = "http://storage-hls:8002"
    public_hls_base: str = "/api/hls"

    batch_concurrency: int = 2
    transcode_poll_interval: float = 5.0
    transcode_timeout_seconds: int = 7200
    resolve_limit_default: int = 42
    ingest_limit_default: int = 5
    episode_resolve_limit: int = 42
    episode_play_concurrency: int = 1

    @property
    def effective_indexer_url(self) -> str:
        if self.indexer_api_key or self.indexer_provider == "prowlarr":
            return self.indexer_url
        return self.jackett_url or self.indexer_url

    @property
    def effective_indexer_api_key(self) -> str:
        return self.indexer_api_key or self.jackett_api_key


settings = Settings()
