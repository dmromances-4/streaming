"""Migraciones incrementales para bases SQLite existentes."""

from __future__ import annotations

import aiosqlite

_TITLE_COLUMNS = [
    ("tmdb_id", "INTEGER"),
    ("year", "INTEGER"),
    ("overview", "TEXT"),
    ("poster_url", "TEXT"),
    ("backdrop_url", "TEXT"),
    ("genres", "TEXT DEFAULT '[]'"),
    ("cast", "TEXT DEFAULT '[]'"),
    ("runtime_minutes", "INTEGER"),
    ("tmdb_status", "TEXT NOT NULL DEFAULT 'pending'"),
    ("ingest_mode", "TEXT"),
    ("qbittorrent_hash", "TEXT"),
]


async def apply_migrations(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("PRAGMA table_info(titles)")
    existing = {row[1] for row in await cursor.fetchall()}

    for col, typedef in _TITLE_COLUMNS:
        if col not in existing:
            await db.execute(f"ALTER TABLE titles ADD COLUMN {col} {typedef}")

    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS tmdb_sync_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resolved INTEGER NOT NULL DEFAULT 0,
            failed INTEGER NOT NULL DEFAULT 0,
            processed INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cocktails (
            id TEXT PRIMARY KEY,
            title_id TEXT NOT NULL,
            name TEXT NOT NULL,
            ingredients TEXT NOT NULL DEFAULT '[]',
            recipe TEXT NOT NULL DEFAULT '[]',
            timestamp_seconds REAL,
            scene TEXT,
            FOREIGN KEY (title_id) REFERENCES titles(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cocktails_title ON cocktails (title_id);
        CREATE INDEX IF NOT EXISTS idx_titles_tmdb ON titles (tmdb_status);
        CREATE TABLE IF NOT EXISTS episodes (
            id TEXT PRIMARY KEY,
            series_id TEXT NOT NULL,
            season_number INTEGER NOT NULL,
            episode_number INTEGER NOT NULL,
            title TEXT,
            overview TEXT,
            runtime_minutes INTEGER,
            tmdb_episode_id INTEGER,
            magnet_uri TEXT,
            magnet_status TEXT NOT NULL DEFAULT 'pending',
            magnet_source TEXT,
            ingest_mode TEXT,
            qbittorrent_hash TEXT,
            ingest_session_id TEXT,
            transcode_job_id TEXT,
            manifest_url TEXT,
            pipeline_status TEXT NOT NULL DEFAULT 'catalog',
            error_message TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            FOREIGN KEY (series_id) REFERENCES titles(id),
            UNIQUE (series_id, season_number, episode_number)
        );
        CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes (series_id);
        CREATE INDEX IF NOT EXISTS idx_episodes_pipeline ON episodes (pipeline_status);
        CREATE INDEX IF NOT EXISTS idx_episodes_magnet ON episodes (magnet_status);
        """
    )

    for table in ("titles", "episodes"):
        cursor = await db.execute(f"PRAGMA table_info({table})")
        cols = {row[1] for row in await cursor.fetchall()}
        if "source_path" not in cols:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN source_path TEXT")

    cursor = await db.execute("PRAGMA table_info(episodes)")
    episode_cols = {row[1] for row in await cursor.fetchall()}
    for col, typedef in (
        ("still_url", "TEXT"),
        ("subtitle_path", "TEXT"),
    ):
        if col not in episode_cols:
            await db.execute(f"ALTER TABLE episodes ADD COLUMN {col} {typedef}")
