"""Configuración del Skill #2."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8002
    skill_name: str = "storage-hls"
    log_level: str = "INFO"

    # FFmpeg / jobs
    hls_work_dir: str = "/tmp/hls-jobs"
    jobs_db_path: str = "/data/hls-jobs.db"
    hls_segment_duration: int = 6
    ffmpeg_threads: int = 2
    max_concurrent_jobs: int = 2
    job_timeout_seconds: int = 7200

    # S3 / MinIO / R2
    s3_endpoint: str = "http://minio:9000"
    s3_bucket: str = "streaming-hls"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = "minioadmin"
    aws_secret_access_key: str = "minioadmin"
    s3_public_base_url: str = ""  # vacío = proxy vía API

    # Skill #1 integration
    ingestion_base_url: str = "http://ingestion-torrent:8001"

    # Manifest URL base expuesta al cliente (vía nginx)
    public_api_base: str = "/api/hls"


settings = Settings()
