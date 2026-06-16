"""Esquemas Pydantic para Skill #1."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    magnet_uri: str = Field(..., min_length=10, description="Magnet URI del torrent")
    season_number: int | None = Field(None, ge=1)
    episode_number: int | None = Field(None, ge=1)


class IngestResponse(BaseModel):
    session_id: str
    name: str
    size_bytes: int
    info_hash: str | None = None


class FileInfo(BaseModel):
    index: int
    name: str
    size: int


class StatusResponse(BaseModel):
    session_id: str
    name: str
    state: str
    progress: float
    download_rate_bps: int
    upload_rate_bps: int = 0
    num_peers: int = 0
    size_bytes: int
    bytes_streamed: int
    files: list[FileInfo] = []


class ErrorResponse(BaseModel):
    error: str
    error_type: str
    details: dict = {}
