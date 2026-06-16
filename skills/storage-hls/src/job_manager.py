"""Gestor de jobs HLS: transcode + upload S3."""

from __future__ import annotations

import asyncio
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from config import settings
from errors import JobNotFoundError, MaxJobsError, TranscodeError
from job_store import get_job_store
from ffmpeg_runner import run_ffmpeg
from manifest_utils import rewrite_manifest, validate_segment_filename
from s3_client import download_bytes, ensure_bucket, upload_file
from skill_telemetry import (
    jobs_active,
    log,
    segments_uploaded_total,
    transcode_duration_seconds,
)


class JobState(str, Enum):
    PENDING = "pending"
    TRANSCODING = "transcoding"
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"


@dataclass
class HlsJob:
    job_id: str
    source_url: str
    session_id: str | None = None
    source_type: str = "stream"
    state: JobState = JobState.PENDING
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    error: str | None = None
    transcode_mode: str | None = None
    segments_count: int = 0
    s3_prefix: str = ""
    _task: asyncio.Task[None] | None = field(default=None, repr=False)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, HlsJob] = {}
        self._lock = asyncio.Lock()
        os.makedirs(settings.hls_work_dir, exist_ok=True)

    async def start(self) -> None:
        ensure_bucket()
        store = get_job_store()
        await store.init()
        for row in await store.load_all():
            job = HlsJob(
                job_id=row["job_id"],
                source_url=row["source_url"],
                session_id=row.get("session_id"),
                source_type=row.get("source_type", "stream"),
                state=JobState(row["state"]),
                transcode_mode=row.get("transcode_mode"),
                segments_count=row.get("segments_count", 0),
                s3_prefix=row["s3_prefix"],
                error=row.get("error"),
                created_at=row.get("created_at", time.time()),
                finished_at=row.get("finished_at"),
            )
            self._jobs[job.job_id] = job
        log.info("job_manager_started", restored=len(self._jobs))

    async def stop(self) -> None:
        async with self._lock:
            for job in self._jobs.values():
                if job._task and not job._task.done():
                    job._task.cancel()
        log.info("job_manager_stopped")

    def _build_source_url(
        self,
        session_id: str | None,
        source_url: str | None,
        source_type: str,
        *,
        season_number: int | None = None,
        episode_number: int | None = None,
    ) -> str:
        if source_url and source_type == "file":
            return source_url
        if source_url:
            return source_url
        if session_id:
            base = (
                f"{settings.ingestion_base_url.rstrip('/')}"
                f"/api/v1/stream/{session_id}"
            )
            if season_number is not None and episode_number is not None:
                return f"{base}?season={season_number}&episode={episode_number}"
            return base
        raise ValueError("session_id or source_url required")

    async def create_job(
        self,
        *,
        session_id: str | None = None,
        source_url: str | None = None,
        source_type: str = "stream",
        season_number: int | None = None,
        episode_number: int | None = None,
    ) -> HlsJob:
        url = self._build_source_url(
            session_id,
            source_url,
            source_type,
            season_number=season_number,
            episode_number=episode_number,
        )

        async with self._lock:
            active = sum(
                1
                for j in self._jobs.values()
                if j.state in (JobState.PENDING, JobState.TRANSCODING, JobState.UPLOADING)
            )
            if active >= settings.max_concurrent_jobs:
                raise MaxJobsError(
                    f"Maximum {settings.max_concurrent_jobs} concurrent jobs"
                )

            job_id = str(uuid.uuid4())
            s3_prefix = f"jobs/{job_id}"
            job = HlsJob(
                job_id=job_id,
                source_url=url,
                session_id=session_id,
                source_type=source_type,
                s3_prefix=s3_prefix,
            )
            self._jobs[job_id] = job
            jobs_active.set(active + 1)
            await self._persist(job)
            job._task = asyncio.create_task(self._run_job(job))
            log.info("job_created", job_id=job_id, source_url=url[:80], source_type=source_type)
            return job

    async def _persist(self, job: HlsJob) -> None:
        store = get_job_store()
        await store.save_job(
            {
                "job_id": job.job_id,
                "session_id": job.session_id,
                "source_url": job.source_url,
                "source_type": job.source_type,
                "state": job.state.value,
                "transcode_mode": job.transcode_mode,
                "segments_count": job.segments_count,
                "s3_prefix": job.s3_prefix,
                "error": job.error,
                "created_at": job.created_at,
                "finished_at": job.finished_at,
            }
        )

    async def get_job(self, job_id: str) -> HlsJob:
        job = self._jobs.get(job_id)
        if job:
            return job
        store = get_job_store()
        row = await store.get_job(job_id)
        if not row:
            raise JobNotFoundError(f"Job {job_id} not found")
        job = HlsJob(
            job_id=row["job_id"],
            source_url=row["source_url"],
            session_id=row.get("session_id"),
            source_type=row.get("source_type", "stream"),
            state=JobState(row["state"]),
            transcode_mode=row.get("transcode_mode"),
            segments_count=row.get("segments_count", 0),
            s3_prefix=row["s3_prefix"],
            error=row.get("error"),
            created_at=row.get("created_at", time.time()),
            finished_at=row.get("finished_at"),
        )
        self._jobs[job_id] = job
        return job

    async def get_status(self, job_id: str) -> dict[str, Any]:
        job = await self.get_job(job_id)
        return {
            "job_id": job.job_id,
            "session_id": job.session_id,
            "state": job.state.value,
            "source_url": job.source_url,
            "transcode_mode": job.transcode_mode,
            "segments_count": job.segments_count,
            "manifest_url": f"/api/v1/manifest/{job.job_id}",
            "error": job.error,
            "created_at": job.created_at,
            "finished_at": job.finished_at,
        }

    async def _run_job(self, job: HlsJob) -> None:
        start = time.monotonic()
        work_dir = os.path.join(settings.hls_work_dir, job.job_id)

        try:
            job.state = JobState.TRANSCODING
            result = await run_ffmpeg(job.source_url, work_dir, job.job_id)

            if not result.success:
                raise TranscodeError(result.stderr_tail or "FFmpeg failed")

            job.transcode_mode = result.mode.value
            job.state = JobState.UPLOADING

            await self._upload_hls_output(job, work_dir)

            job.state = JobState.READY
            job.finished_at = time.time()
            await self._persist(job)
            transcode_duration_seconds.observe(time.monotonic() - start)
            log.info(
                "job_ready",
                job_id=job.job_id,
                segments=job.segments_count,
                mode=job.transcode_mode,
            )
        except asyncio.CancelledError:
            job.state = JobState.FAILED
            job.error = "cancelled"
            raise
        except Exception as exc:
            job.state = JobState.FAILED
            job.error = str(exc)
            job.finished_at = time.time()
            await self._persist(job)
            log.error("job_failed", job_id=job.job_id, error=str(exc))
        finally:
            self._update_active_gauge()
            if os.path.isdir(work_dir):
                try:
                    shutil.rmtree(work_dir)
                except OSError:
                    pass

    async def _upload_hls_output(self, job: HlsJob, work_dir: str) -> None:
        files = sorted(os.listdir(work_dir))
        ts_files = [f for f in files if f.endswith(".ts")]
        m3u8_files = [f for f in files if f.endswith(".m3u8")]

        for name in ts_files:
            local = os.path.join(work_dir, name)
            s3_key = f"{job.s3_prefix}/{name}"
            await asyncio.to_thread(upload_file, local, s3_key)
            job.segments_count += 1
            segments_uploaded_total.inc()

        for name in m3u8_files:
            local = os.path.join(work_dir, name)
            s3_key = f"{job.s3_prefix}/{name}"
            await asyncio.to_thread(upload_file, local, s3_key)

    def _update_active_gauge(self) -> None:
        active = sum(
            1
            for j in self._jobs.values()
            if j.state in (JobState.PENDING, JobState.TRANSCODING, JobState.UPLOADING)
        )
        jobs_active.set(active)

    async def get_manifest_from_s3(self, job_id: str) -> str:
        job = await self.get_job(job_id)
        if job.state != JobState.READY:
            raise JobNotFoundError(f"Job {job_id} not ready (state={job.state.value})")

        raw = download_bytes(f"{job.s3_prefix}/index.m3u8").decode("utf-8")
        return rewrite_manifest(
            raw,
            job_id,
            settings.public_api_base,
            s3_public_base=settings.s3_public_base_url,
            s3_prefix=job.s3_prefix,
        )

    async def get_segment_s3_key(self, job_id: str, filename: str) -> str:
        if not validate_segment_filename(filename):
            raise JobNotFoundError(f"Invalid segment filename: {filename}")
        job = await self.get_job(job_id)
        return f"{job.s3_prefix}/{filename}"


_manager: JobManager | None = None


def get_manager() -> JobManager:
    global _manager
    if _manager is None:
        _manager = JobManager()
    return _manager
