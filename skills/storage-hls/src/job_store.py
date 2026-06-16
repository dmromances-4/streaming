"""Persistencia SQLite de jobs HLS."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import aiosqlite

from config import settings


class JobStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.jobs_db_path

    async def init(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS hls_jobs (
                    job_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    source_url TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'stream',
                    state TEXT NOT NULL,
                    transcode_mode TEXT,
                    segments_count INTEGER DEFAULT 0,
                    s3_prefix TEXT NOT NULL,
                    error TEXT,
                    created_at REAL NOT NULL,
                    finished_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_hls_jobs_state ON hls_jobs (state);
                """
            )
            await db.commit()

    async def save_job(self, job: dict[str, Any]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO hls_jobs
                (job_id, session_id, source_url, source_type, state, transcode_mode,
                 segments_count, s3_prefix, error, created_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["job_id"],
                    job.get("session_id"),
                    job["source_url"],
                    job.get("source_type", "stream"),
                    job["state"],
                    job.get("transcode_mode"),
                    job.get("segments_count", 0),
                    job["s3_prefix"],
                    job.get("error"),
                    job.get("created_at", time.time()),
                    job.get("finished_at"),
                ),
            )
            await db.commit()

    async def update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [job_id]
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE hls_jobs SET {cols} WHERE job_id = ?", vals)
            await db.commit()

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM hls_jobs WHERE job_id = ?", (job_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def load_all(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM hls_jobs")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


_store: JobStore | None = None


def get_job_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store
