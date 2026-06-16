CREATE TABLE IF NOT EXISTS titles (
    id TEXT PRIMARY KEY,
    content_type TEXT NOT NULL CHECK (content_type IN ('series', 'movie')),
    origin TEXT NOT NULL CHECK (origin IN ('american', 'european', 'spanish', 'catalan')),
    title TEXT NOT NULL,
    title_normalized TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    priority INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    tmdb_id INTEGER,
    year INTEGER,
    overview TEXT,
    poster_url TEXT,
    backdrop_url TEXT,
    genres TEXT DEFAULT '[]',
    cast TEXT DEFAULT '[]',
    runtime_minutes INTEGER,
    tmdb_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (tmdb_status IN ('pending', 'resolved', 'failed')),
    magnet_uri TEXT,
    source_path TEXT,
    magnet_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (magnet_status IN ('pending', 'resolved', 'failed', 'skipped')),
    magnet_source TEXT,
    ingest_mode TEXT,
    qbittorrent_hash TEXT,
    ingest_session_id TEXT,
    transcode_job_id TEXT,
    manifest_url TEXT,
    pipeline_status TEXT NOT NULL DEFAULT 'catalog'
        CHECK (pipeline_status IN ('catalog', 'resolving', 'ingesting', 'transcoding', 'ready', 'failed')),
    error_message TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE (content_type, origin, title_normalized)
);

CREATE INDEX IF NOT EXISTS idx_titles_type_origin ON titles (content_type, origin);
CREATE INDEX IF NOT EXISTS idx_titles_priority ON titles (priority);
CREATE INDEX IF NOT EXISTS idx_titles_pipeline ON titles (pipeline_status);
CREATE INDEX IF NOT EXISTS idx_titles_magnet ON titles (magnet_status);
CREATE INDEX IF NOT EXISTS idx_titles_tmdb ON titles (tmdb_status);

CREATE TABLE IF NOT EXISTS import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    inserted INTEGER NOT NULL DEFAULT 0,
    skipped_duplicates INTEGER NOT NULL DEFAULT 0,
    skipped_invalid INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

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

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    series_id TEXT NOT NULL,
    season_number INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    title TEXT,
    overview TEXT,
    runtime_minutes INTEGER,
    tmdb_episode_id INTEGER,
    still_url TEXT,
    subtitle_path TEXT,
    magnet_uri TEXT,
    magnet_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (magnet_status IN ('pending', 'resolved', 'failed', 'skipped')),
    magnet_source TEXT,
    ingest_mode TEXT,
    qbittorrent_hash TEXT,
    ingest_session_id TEXT,
    transcode_job_id TEXT,
    manifest_url TEXT,
    pipeline_status TEXT NOT NULL DEFAULT 'catalog'
        CHECK (pipeline_status IN ('catalog', 'resolving', 'ingesting', 'transcoding', 'ready', 'failed')),
    error_message TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (series_id) REFERENCES titles(id),
    UNIQUE (series_id, season_number, episode_number)
);

CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes (series_id);
CREATE INDEX IF NOT EXISTS idx_episodes_pipeline ON episodes (pipeline_status);
CREATE INDEX IF NOT EXISTS idx_episodes_magnet ON episodes (magnet_status);
