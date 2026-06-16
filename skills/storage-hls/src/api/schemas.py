"""Esquemas Pydantic para Skill #2."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TranscodeRequest(BaseModel):
    session_id: str | None = Field(None, description="Session ID from Skill #1")
    source_url: str | None = Field(
        None, description="Direct stream URL or local file path"
    )
    source_type: Literal["stream", "file"] = "stream"
    season_number: int | None = Field(None, ge=1)
    episode_number: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def require_source(self) -> TranscodeRequest:
        if not self.session_id and not self.source_url:
            raise ValueError("Either session_id or source_url is required")
        return self


class TranscodeResponse(BaseModel):
    job_id: str
    state: str
    manifest_url: str


class JobStatusResponse(BaseModel):
    job_id: str
    session_id: str | None
    state: str
    source_url: str
    transcode_mode: str | None = None
    segments_count: int = 0
    manifest_url: str
    error: str | None = None
    created_at: float
    finished_at: float | None = None
