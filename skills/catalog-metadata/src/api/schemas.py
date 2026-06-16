"""Esquemas API Skill #6."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ImportRequest(BaseModel):
    source: str = "seed"


class ImportResponse(BaseModel):
    inserted: int
    skipped_duplicates: int
    skipped_invalid: int


class CocktailItem(BaseModel):
    id: str
    title_id: str
    name: str
    ingredients: list[str] = []
    recipe: list[str] = []
    timestamp_seconds: float | None = None
    scene: str | None = None


def _normalize_manifest(v: str | None) -> str | None:
    from url_utils import normalize_manifest_url

    return normalize_manifest_url(v)


class CatalogItem(BaseModel):
    id: str
    content_type: str
    origin: str
    title: str
    tags: list[str] = []
    priority: int = 0
    notes: str | None = None
    tmdb_id: int | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    genres: list[str] = []
    cast: list[str] = []
    runtime_minutes: int | None = None
    tmdb_status: str | None = None
    magnet_status: str
    pipeline_status: str
    manifest_url: str | None = None
    ingest_mode: str | None = None
    error_message: str | None = None

    @field_validator("manifest_url", mode="before")
    @classmethod
    def normalize_manifest(cls, v: str | None) -> str | None:
        return _normalize_manifest(v)


class CatalogListResponse(BaseModel):
    items: list[CatalogItem]
    total: int
    limit: int
    offset: int


class MagnetOverride(BaseModel):
    magnet_uri: str = Field(..., min_length=10)


class ResolveRequest(BaseModel):
    priority_only: bool = True
    limit: int = 42


class BatchIngestRequest(BaseModel):
    priority_only: bool = True
    limit: int = 5
    concurrency: int = 2


class EnrichMetadataRequest(BaseModel):
    priority_only: bool = False
    limit: int = 100
    title_ids: list[str] | None = None
    force_reenrich: bool = False


class BatchResult(BaseModel):
    success: int = 0
    failed: int = 0
    processed: int = 0
    resolved: int | None = None
    inserted: int | None = None
    updated: int | None = None
    skipped: int | None = None


class EpisodeItem(BaseModel):
    id: str
    series_id: str
    season_number: int
    episode_number: int
    title: str | None = None
    overview: str | None = None
    runtime_minutes: int | None = None
    magnet_status: str
    pipeline_status: str
    manifest_url: str | None = None
    ingest_mode: str | None = None
    error_message: str | None = None
    has_local_media: bool = False
    still_url: str | None = None
    subtitle_path: str | None = None

    @field_validator("manifest_url", mode="before")
    @classmethod
    def normalize_manifest(cls, v: str | None) -> str | None:
        return _normalize_manifest(v)


class EpisodeListResponse(BaseModel):
    items: list[EpisodeItem]
    total: int
    season: int | None = None


class SeasonSummary(BaseModel):
    season_number: int
    episode_count: int
    ready_count: int
    magnets_resolved: int


class EpisodePlayResponse(BaseModel):
    episode_id: str
    pipeline_status: str
    manifest_url: str | None = None
    transcode_job_id: str | None = None
    message: str | None = None
    stage: str | None = None
    torrent_title: str | None = None
    torrent_size_gb: float | None = None
    seeders: int | None = None

    @field_validator("manifest_url", mode="before")
    @classmethod
    def normalize_manifest(cls, v: str | None) -> str | None:
        return _normalize_manifest(v)


class EpisodeAcquireResponse(EpisodePlayResponse):
    pass


class TitlePlayResponse(BaseModel):
    title_id: str
    pipeline_status: str
    manifest_url: str | None = None
    transcode_job_id: str | None = None
    message: str | None = None

    @field_validator("manifest_url", mode="before")
    @classmethod
    def normalize_manifest(cls, v: str | None) -> str | None:
        return _normalize_manifest(v)


class TitleStatusResponse(BaseModel):
    title_id: str
    pipeline_status: str
    manifest_url: str | None = None
    transcode_job_id: str | None = None
    error_message: str | None = None

    @field_validator("manifest_url", mode="before")
    @classmethod
    def normalize_manifest(cls, v: str | None) -> str | None:
        return _normalize_manifest(v)


class SystemStatusResponse(BaseModel):
    acquire_ready: bool
    media_source_mode: str
    checks: dict[str, bool]
    messages: list[str]
    hints: dict[str, str]


class EpisodeStatusResponse(BaseModel):
    episode_id: str
    pipeline_status: str
    magnet_status: str
    manifest_url: str | None = None
    transcode_job_id: str | None = None
    error_message: str | None = None
    stage: str | None = None
    message: str | None = None
    download_progress: float | None = None
    download_speed_mbps: float | None = None

    @field_validator("manifest_url", mode="before")
    @classmethod
    def normalize_manifest(cls, v: str | None) -> str | None:
        return _normalize_manifest(v)


class ResolveSeasonRequest(BaseModel):
    season_number: int | None = None
    limit: int = 42
