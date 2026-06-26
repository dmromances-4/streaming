"""Repositorio SQLite para el catálogo."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import aiosqlite

from config import settings
from db.migrations import apply_migrations


class CatalogRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.database_path

    async def init(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        schema_path = Path(__file__).parent / "schema.sql"
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(schema_path.read_text())
            await apply_migrations(db)
            await db.commit()

    async def insert_title(self, row: dict[str, Any]) -> bool:
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO titles (
                        id, content_type, origin, title, title_normalized,
                        tags, priority, notes, search_queries,
                        magnet_status, pipeline_status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'catalog', ?, ?)
                    """,
                    (
                        row["id"],
                        row["content_type"],
                        row["origin"],
                        row["title"],
                        row["title_normalized"],
                        json.dumps(row.get("tags", [])),
                        row.get("priority", 0),
                        row.get("notes"),
                        json.dumps(row.get("search_queries", [])),
                        now,
                        now,
                    ),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def record_import_run(
        self,
        source: str,
        inserted: int,
        skipped_duplicates: int,
        skipped_invalid: int,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO import_runs (source, inserted, skipped_duplicates, skipped_invalid, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source, inserted, skipped_duplicates, skipped_invalid, time.time()),
            )
            await db.commit()

    def _title_filter_clauses(
        self,
        *,
        content_type: str | None = None,
        origin: str | None = None,
        cocteleria: bool | None = None,
        pipeline_status: str | None = None,
        magnet_status: str | None = None,
        query: str | None = None,
        genre: str | None = None,
        without_local: bool | None = None,
    ) -> tuple[list[str], list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        if content_type:
            clauses.append("content_type = ?")
            params.append(content_type)
        if origin:
            clauses.append("origin = ?")
            params.append(origin)
        if cocteleria:
            clauses.append("priority = 1")
        if pipeline_status:
            clauses.append("pipeline_status = ?")
            params.append(pipeline_status)
        if magnet_status:
            clauses.append("magnet_status = ?")
            params.append(magnet_status)
        if query:
            q = query.lower()
            clauses.append(
                "(LOWER(title) LIKE ? OR LOWER(COALESCE(overview,'')) LIKE ? "
                "OR LOWER(COALESCE(genres,'')) LIKE ? OR LOWER(COALESCE(cast,'')) LIKE ?)"
            )
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        if genre:
            clauses.append("LOWER(COALESCE(genres,'')) LIKE ?")
            params.append(f"%{genre.lower()}%")
        if without_local:
            clauses.append("content_type = 'series'")
            clauses.append(
                """NOT EXISTS (
                    SELECT 1 FROM episodes e
                    WHERE e.series_id = titles.id
                      AND e.source_path IS NOT NULL
                      AND TRIM(e.source_path) != ''
                )"""
            )

        return clauses, params

    async def list_titles(
        self,
        *,
        content_type: str | None = None,
        origin: str | None = None,
        cocteleria: bool | None = None,
        pipeline_status: str | None = None,
        magnet_status: str | None = None,
        query: str | None = None,
        genre: str | None = None,
        without_local: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses, params = self._title_filter_clauses(
            content_type=content_type,
            origin=origin,
            cocteleria=cocteleria,
            pipeline_status=pipeline_status,
            magnet_status=magnet_status,
            query=query,
            genre=genre,
            without_local=without_local,
        )

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"SELECT * FROM titles {where} ORDER BY priority DESC, title ASC LIMIT ? OFFSET ?",
                params,
            )
            rows = await cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def count_titles(
        self,
        *,
        content_type: str | None = None,
        origin: str | None = None,
        cocteleria: bool | None = None,
        pipeline_status: str | None = None,
        magnet_status: str | None = None,
        query: str | None = None,
        genre: str | None = None,
        without_local: bool | None = None,
    ) -> int:
        clauses, params = self._title_filter_clauses(
            content_type=content_type,
            origin=origin,
            cocteleria=cocteleria,
            pipeline_status=pipeline_status,
            magnet_status=magnet_status,
            query=query,
            genre=genre,
            without_local=without_local,
        )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"SELECT COUNT(*) FROM titles {where}",
                params,
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_title(self, title_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM titles WHERE id = ?", (title_id,))
            row = await cursor.fetchone()
            return self._row_to_dict(row) if row else None

    async def get_title_by_tmdb_id(
        self, tmdb_id: int, content_type: str
    ) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM titles WHERE tmdb_id = ? AND content_type = ? LIMIT 1",
                (tmdb_id, content_type),
            )
            row = await cursor.fetchone()
            return self._row_to_dict(row) if row else None

    async def update_title(self, title_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = time.time()
        for json_field in ("tags", "genres", "cast", "search_queries"):
            if json_field in fields and isinstance(fields[json_field], list):
                fields[json_field] = json.dumps(fields[json_field])

        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [title_id]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE titles SET {cols} WHERE id = ?", vals)
            await db.commit()

    async def get_pending_resolve(
        self, *, priority_only: bool = False, limit: int = 42
    ) -> list[dict[str, Any]]:
        clauses = ["magnet_status = 'pending'"]
        if priority_only:
            clauses.append("priority = 1")
        where = " AND ".join(clauses)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"SELECT * FROM titles WHERE {where} ORDER BY priority DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def get_ready_for_ingest(
        self, *, priority_only: bool = False, limit: int = 5
    ) -> list[dict[str, Any]]:
        clauses = [
            "magnet_status = 'resolved'",
            "magnet_uri IS NOT NULL",
            "pipeline_status IN ('catalog', 'failed')",
        ]
        if priority_only:
            clauses.append("priority = 1")
        where = " AND ".join(clauses)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"SELECT * FROM titles WHERE {where} ORDER BY priority DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def get_pending_tmdb(
        self, *, priority_only: bool = False, limit: int = 100
    ) -> list[dict[str, Any]]:
        clauses = ["tmdb_status = 'pending'"]
        if priority_only:
            clauses.append("priority = 1")
        where = " AND ".join(clauses)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"SELECT * FROM titles WHERE {where} ORDER BY priority DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def record_tmdb_sync_run(
        self, resolved: int, failed: int, processed: int
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO tmdb_sync_runs (resolved, failed, processed, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (resolved, failed, processed, time.time()),
            )
            await db.commit()

    async def list_titles_by_ingredient(
        self, ingredient: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        pattern = f'%"{ingredient.lower()}"%'
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT DISTINCT t.* FROM titles t
                JOIN cocktails c ON c.title_id = t.id
                WHERE c.ingredients LIKE ?
                ORDER BY t.priority DESC, t.title ASC
                LIMIT ?
                """,
                (pattern, limit),
            )
            rows = await cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def upsert_cocktail(self, row: dict[str, Any]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO cocktails
                (id, title_id, name, ingredients, recipe, timestamp_seconds, scene)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["title_id"],
                    row["name"],
                    json.dumps(row.get("ingredients", [])),
                    json.dumps(row.get("recipe", [])),
                    row.get("timestamp_seconds"),
                    row.get("scene"),
                ),
            )
            await db.commit()

    async def get_cocktails_for_title(self, title_id: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM cocktails WHERE title_id = ? ORDER BY timestamp_seconds",
                (title_id,),
            )
            rows = await cursor.fetchall()
            return [self._cocktail_row(r) for r in rows]

    async def list_cocktails_by_ingredient(
        self, ingredient: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if ingredient:
                pattern = f'%"{ingredient.lower()}"%'
                cursor = await db.execute(
                    "SELECT * FROM cocktails WHERE ingredients LIKE ? LIMIT ?",
                    (pattern, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM cocktails LIMIT ?", (limit,)
                )
            rows = await cursor.fetchall()
            return [self._cocktail_row(r) for r in rows]

    async def list_cocktail_ingredients(self) -> list[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT ingredients FROM cocktails")
            rows = await cursor.fetchall()
        seen: set[str] = set()
        for (raw,) in rows:
            try:
                items = json.loads(raw) if raw else []
            except json.JSONDecodeError:
                continue
            for item in items:
                seen.add(str(item).lower())
        return sorted(seen)

    async def list_series_with_local_media(self, limit: int = 20) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """
                SELECT DISTINCT t.*,
                    (
                        SELECT COUNT(*)
                        FROM episodes er
                        WHERE er.series_id = t.id
                          AND er.pipeline_status = 'ready'
                    ) AS library_ready_count
                FROM titles t
                INNER JOIN episodes e ON e.series_id = t.id
                WHERE e.source_path IS NOT NULL
                  AND TRIM(e.source_path) != ''
                  AND t.content_type = 'series'
                  AND EXISTS (
                    SELECT 1 FROM episodes er2
                    WHERE er2.series_id = t.id
                      AND er2.pipeline_status = 'ready'
                  )
                ORDER BY library_ready_count DESC, t.priority DESC, t.title
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cur.fetchall()
            return [self._row_to_dict(row) for row in rows]

    async def list_titles_with_local_media(self, limit: int = 20) -> list[dict[str, Any]]:
        series = await self.list_series_with_local_media(limit=limit * 2)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """
                SELECT * FROM titles
                WHERE content_type = 'movie'
                  AND source_path IS NOT NULL
                  AND TRIM(source_path) != ''
                  AND pipeline_status = 'ready'
                ORDER BY priority DESC, title
                LIMIT ?
                """,
                (limit,),
            )
            movies = [self._row_to_dict(r) for r in await cur.fetchall()]
        combined = series + movies
        combined.sort(
            key=lambda t: (
                -(t.get("library_ready_count") or (1 if t.get("pipeline_status") == "ready" else 0)),
                -(t.get("priority") or 0),
                t.get("title") or "",
            )
        )
        return combined[:limit]

    async def list_top_genres(self, *, limit: int = 6) -> list[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT genres FROM titles WHERE genres IS NOT NULL AND TRIM(genres) != ''"
            )
            rows = await cur.fetchall()
        counts: dict[str, int] = {}
        for (raw,) in rows:
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                continue
            if not isinstance(parsed, list):
                continue
            for g in parsed:
                name = str(g).strip()
                if name:
                    counts[name] = counts.get(name, 0) + 1
        ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        return [name for name, _ in ranked[:limit]]

    async def find_similar_titles(
        self, title_id: str, *, limit: int = 12
    ) -> list[dict[str, Any]]:
        source = await self.get_title(title_id)
        if not source:
            return []
        genres = source.get("genres") or []
        if isinstance(genres, str):
            try:
                genres = json.loads(genres)
            except json.JSONDecodeError:
                genres = []
        origin = source.get("origin")
        clauses = ["id != ?", "content_type = ?"]
        params: list[Any] = [title_id, source.get("content_type", "series")]
        if origin:
            clauses.append("origin = ?")
            params.append(origin)
        genre_clauses = []
        for g in genres[:5]:
            genre_clauses.append("LOWER(COALESCE(genres,'')) LIKE ?")
            params.append(f"%{str(g).lower()}%")
        if genre_clauses:
            clauses.append(f"({' OR '.join(genre_clauses)})")
        where = " AND ".join(clauses)
        params.append(limit)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                f"SELECT * FROM titles WHERE {where} ORDER BY priority DESC, title LIMIT ?",
                params,
            )
            rows = await cur.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def list_active_downloads(self, limit: int = 20) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """
                SELECT id, series_id, season_number, episode_number, title,
                       pipeline_status, magnet_status, error_message, qbittorrent_hash
                FROM episodes
                WHERE pipeline_status IN ('resolving', 'ingesting', 'downloading', 'transcoding')
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_series_ids(self, *, content_type: str = "series") -> list[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT id FROM titles WHERE content_type = ? ORDER BY priority DESC, title",
                (content_type,),
            )
            rows = await cur.fetchall()
            return [row[0] for row in rows]

    async def get_stats(self) -> dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async def _count(sql: str, params: tuple = ()) -> int:
                cur = await db.execute(sql, params)
                row = await cur.fetchone()
                return row[0] if row else 0

            by_category = []
            for ct in ("series", "movie"):
                for origin in ("american", "european", "spanish", "catalan"):
                    n = await _count(
                        "SELECT COUNT(*) FROM titles WHERE content_type=? AND origin=?",
                        (ct, origin),
                    )
                    by_category.append({"content_type": ct, "origin": origin, "count": n})

            return {
                "total": await _count("SELECT COUNT(*) FROM titles"),
                "by_category": by_category,
                "cocteleria": await _count("SELECT COUNT(*) FROM titles WHERE priority=1"),
                "ready": await _count(
                    "SELECT COUNT(*) FROM titles WHERE pipeline_status='ready'"
                ),
                "magnets_resolved": await _count(
                    "SELECT COUNT(*) FROM titles WHERE magnet_status='resolved'"
                ),
                "failed": await _count(
                    "SELECT COUNT(*) FROM titles WHERE pipeline_status='failed'"
                ),
            }

    def _row_to_dict(self, row: aiosqlite.Row) -> dict[str, Any]:
        d = dict(row)
        for field in ("tags", "genres", "cast", "search_queries"):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except json.JSONDecodeError:
                    d[field] = []
        return d

    def _cocktail_row(self, row: aiosqlite.Row) -> dict[str, Any]:
        d = dict(row)
        for field in ("ingredients", "recipe"):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except json.JSONDecodeError:
                    d[field] = []
        return d

    async def upsert_episode(self, row: dict[str, Any]) -> bool:
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO episodes (
                        id, series_id, season_number, episode_number,
                        title, overview, runtime_minutes, tmdb_episode_id,
                        still_url, subtitle_path,
                        magnet_status, pipeline_status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'catalog', ?, ?)
                    """,
                    (
                        row["id"],
                        row["series_id"],
                        row["season_number"],
                        row["episode_number"],
                        row.get("title"),
                        row.get("overview"),
                        row.get("runtime_minutes"),
                        row.get("tmdb_episode_id"),
                        row.get("still_url"),
                        row.get("subtitle_path"),
                        now,
                        now,
                    ),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                await db.execute(
                    """
                    UPDATE episodes SET
                        title = COALESCE(?, title),
                        overview = COALESCE(?, overview),
                        runtime_minutes = COALESCE(?, runtime_minutes),
                        tmdb_episode_id = COALESCE(?, tmdb_episode_id),
                        still_url = COALESCE(?, still_url),
                        subtitle_path = COALESCE(?, subtitle_path),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        row.get("title"),
                        row.get("overview"),
                        row.get("runtime_minutes"),
                        row.get("tmdb_episode_id"),
                        row.get("still_url"),
                        row.get("subtitle_path"),
                        now,
                        row["id"],
                    ),
                )
                await db.commit()
                return False

    async def list_episodes(
        self, series_id: str, *, season_number: int | None = None
    ) -> list[dict[str, Any]]:
        clauses = ["series_id = ?"]
        params: list[Any] = [series_id]
        if season_number is not None:
            clauses.append("season_number = ?")
            params.append(season_number)
        where = " AND ".join(clauses)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT * FROM episodes
                WHERE {where}
                ORDER BY season_number ASC, episode_number ASC
                """,
                params,
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM episodes WHERE id = ?", (episode_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_episode(self, episode_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [episode_id]
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE episodes SET {cols} WHERE id = ?", vals)
            await db.commit()

    async def count_episodes(
        self, series_id: str, *, season_number: int | None = None
    ) -> int:
        clauses = ["series_id = ?"]
        params: list[Any] = [series_id]
        if season_number is not None:
            clauses.append("season_number = ?")
            params.append(season_number)
        where = " AND ".join(clauses)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"SELECT COUNT(*) FROM episodes WHERE {where}",
                params,
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def list_season_summaries(self, series_id: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT
                    season_number,
                    COUNT(*) AS episode_count,
                    SUM(CASE WHEN pipeline_status = 'ready' THEN 1 ELSE 0 END) AS ready_count,
                    SUM(CASE WHEN magnet_status = 'resolved' THEN 1 ELSE 0 END) AS magnets_resolved
                FROM episodes
                WHERE series_id = ?
                GROUP BY season_number
                ORDER BY season_number ASC
                """,
                (series_id,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_episodes_pending_resolve(
        self,
        *,
        series_id: str | None = None,
        season_number: int | None = None,
        limit: int = 42,
    ) -> list[dict[str, Any]]:
        clauses = ["magnet_status = 'pending'"]
        params: list[Any] = []
        if series_id:
            clauses.append("series_id = ?")
            params.append(series_id)
        if season_number is not None:
            clauses.append("season_number = ?")
            params.append(season_number)
        where = " AND ".join(clauses)
        params.append(limit)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT * FROM episodes
                WHERE {where}
                ORDER BY season_number ASC, episode_number ASC
                LIMIT ?
                """,
                params,
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_episodes_ready_for_ingest(
        self,
        *,
        series_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        clauses = [
            "magnet_status = 'resolved'",
            "magnet_uri IS NOT NULL",
            "pipeline_status IN ('catalog', 'failed')",
        ]
        params: list[Any] = []
        if series_id:
            clauses.append("series_id = ?")
            params.append(series_id)
        where = " AND ".join(clauses)
        params.append(limit)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT * FROM episodes
                WHERE {where}
                ORDER BY season_number ASC, episode_number ASC
                LIMIT ?
                """,
                params,
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def list_movies_for_bulk_acquire(
        self,
        *,
        origin: str | None = None,
        limit: int | None = None,
        skip_ready: bool = True,
    ) -> list[dict[str, Any]]:
        clauses = ["content_type = 'movie'"]
        params: list[Any] = []
        if origin:
            clauses.append("origin = ?")
            params.append(origin)
        if skip_ready:
            clauses.append(
                "(source_path IS NULL OR TRIM(source_path) = '') "
                "AND pipeline_status NOT IN ('ready', 'ingesting', 'transcoding', 'resolving')"
            )
        where = " AND ".join(clauses)
        sql = f"SELECT * FROM titles WHERE {where} ORDER BY priority DESC, title"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def create_bulk_acquire_run(
        self, *, content_type: str, total: int
    ) -> int:
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO bulk_acquire_runs
                (content_type, total, completed, failed, skipped, status, created_at, updated_at)
                VALUES (?, ?, 0, 0, 0, 'running', ?, ?)
                """,
                (content_type, total, now, now),
            )
            await db.commit()
            return cursor.lastrowid or 0

    async def update_bulk_acquire_run(
        self,
        run_id: int,
        *,
        completed: int | None = None,
        failed: int | None = None,
        skipped: int | None = None,
        status: str | None = None,
        error_message: str | None = None,
    ) -> None:
        fields: dict[str, Any] = {"updated_at": time.time()}
        if completed is not None:
            fields["completed"] = completed
        if failed is not None:
            fields["failed"] = failed
        if skipped is not None:
            fields["skipped"] = skipped
        if status is not None:
            fields["status"] = status
        if error_message is not None:
            fields["error_message"] = error_message
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [run_id]
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE bulk_acquire_runs SET {cols} WHERE id = ?", vals
            )
            await db.commit()

    async def get_bulk_acquire_run(self, run_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM bulk_acquire_runs WHERE id = ?", (run_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_latest_bulk_acquire_run(
        self, *, content_type: str = "movie"
    ) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM bulk_acquire_runs
                WHERE content_type = ?
                ORDER BY id DESC LIMIT 1
                """,
                (content_type,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None


_repo: CatalogRepository | None = None


def get_repository() -> CatalogRepository:
    global _repo
    if _repo is None:
        _repo = CatalogRepository()
    return _repo
