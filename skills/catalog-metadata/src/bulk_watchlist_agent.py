"""Agente bulk: descarga masiva de películas (Fase 1) y series (futuro)."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from config import settings
from db.repository import CatalogRepository
from ingest_orchestrator import IngestOrchestrator
from metadata_enricher import get_enricher
from skill_telemetry import log


class BulkWatchlistAgent:
    def __init__(self, repo: CatalogRepository, orchestrator: IngestOrchestrator) -> None:
        self.repo = repo
        self.orch = orchestrator
        self._run_id: int | None = None
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def _media_free_gb(self) -> float:
        candidates: list[Path] = []
        host_path = settings.bulk_acquire_host_media_path.strip()
        if host_path and not (len(host_path) >= 2 and host_path[1] == ":"):
            candidates.append(Path(host_path))
        for path in (
            Path(settings.media_root or "/downloads"),
            Path("/downloads"),
        ):
            if path not in candidates:
                candidates.append(path)
        for path in candidates:
            try:
                if not path.exists():
                    continue
                usage = shutil.disk_usage(path)
                return usage.free / (1024**3)
            except OSError:
                continue
        return float("inf")

    async def enrich_all_movies(self, *, limit: int = 100) -> dict[str, int]:
        if not settings.tmdb_enabled:
            log.info("bulk_enrich_skipped_no_tmdb_key")
            return {
                "resolved": 0,
                "failed": 0,
                "processed": 0,
                "skipped": True,
                "reason": "TMDB desactivado (sin API key)",
            }

        enricher = get_enricher(self.repo)
        total_resolved = 0
        total_failed = 0
        total_processed = 0
        rounds = 0
        max_rounds = 500

        while rounds < max_rounds:
            rounds += 1
            pending = await self.repo.get_pending_tmdb(limit=limit)
            movies = [t for t in pending if t.get("content_type") == "movie"]
            if not movies:
                break
            result = await enricher.enrich_by_ids(
                [m["id"] for m in movies],
                force_reenrich=False,
            )
            resolved = int(result.get("resolved", 0))
            failed = int(result.get("failed", 0))
            processed = int(result.get("processed", 0))
            total_resolved += resolved
            total_failed += failed
            total_processed += processed
            if processed == 0:
                break
            await asyncio.sleep(0.5)

        return {
            "resolved": total_resolved,
            "failed": total_failed,
            "processed": total_processed,
        }

    async def acquire_movies(
        self,
        *,
        origin: str | None = None,
        limit: int | None = None,
        concurrency: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        concurrency = concurrency or settings.bulk_acquire_concurrency
        movies = await self.repo.list_movies_for_bulk_acquire(
            origin=origin,
            limit=limit,
            skip_ready=True,
        )

        if dry_run:
            return {
                "dry_run": True,
                "total": len(movies),
                "free_gb": round(self._media_free_gb(), 2),
                "movies": [m["id"] for m in movies[:20]],
            }

        run_id = await self.repo.create_bulk_acquire_run(
            content_type="movie",
            total=len(movies),
        )
        self._run_id = run_id
        completed = 0
        failed = 0
        skipped = 0
        sem = asyncio.Semaphore(concurrency)
        results: list[dict[str, Any]] = []

        async def process_one(movie: dict[str, Any]) -> None:
            nonlocal completed, failed, skipped
            if self._stop_requested:
                return
            free_gb = self._media_free_gb()
            if free_gb < settings.bulk_acquire_min_free_gb:
                self._stop_requested = True
                log.warning(
                    "bulk_acquire_paused_low_disk",
                    free_gb=round(free_gb, 2),
                    min_gb=settings.bulk_acquire_min_free_gb,
                )
                return

            title_id = movie["id"]
            async with sem:
                if self._stop_requested:
                    return
                try:
                    await self.orch.scan_movie_library(title_id)
                    refreshed = await self.repo.get_title(title_id)
                    if (
                        refreshed
                        and refreshed.get("pipeline_status") == "ready"
                        and refreshed.get("source_path")
                    ):
                        skipped += 1
                        results.append(
                            {"title_id": title_id, "status": "skipped", "reason": "already_local"}
                        )
                        return

                    result = await self.orch.acquire_movie(title_id)
                    status = result.get("pipeline_status", "failed")
                    stage = result.get("stage", status)
                    if status in ("ready", "ingesting", "transcoding", "resolving") or stage in (
                        "downloading",
                        "searching",
                        "transcoding",
                    ):
                        completed += 1
                        results.append({"title_id": title_id, "status": "started", "stage": stage})
                    else:
                        failed += 1
                        results.append(
                            {
                                "title_id": title_id,
                                "status": "failed",
                                "message": result.get("message"),
                            }
                        )
                except Exception as exc:
                    failed += 1
                    results.append(
                        {"title_id": title_id, "status": "failed", "message": str(exc)}
                    )
                finally:
                    await self.repo.update_bulk_acquire_run(
                        run_id,
                        completed=completed,
                        failed=failed,
                        skipped=skipped,
                    )

        await asyncio.gather(*[process_one(m) for m in movies])

        final_status = "paused" if self._stop_requested else "completed"
        await self.repo.update_bulk_acquire_run(
            run_id,
            status=final_status,
            completed=completed,
            failed=failed,
            skipped=skipped,
        )

        log.info(
            "bulk_acquire_movies_done",
            run_id=run_id,
            total=len(movies),
            completed=completed,
            failed=failed,
            skipped=skipped,
            free_gb=round(self._media_free_gb(), 2),
        )

        return {
            "run_id": run_id,
            "total": len(movies),
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "status": final_status,
            "free_gb": round(self._media_free_gb(), 2),
            "results": results[:50],
        }

    async def get_status(self, run_id: int | None = None) -> dict[str, Any]:
        if run_id:
            run = await self.repo.get_bulk_acquire_run(run_id)
        else:
            run = await self.repo.get_latest_bulk_acquire_run(content_type="movie")
        if not run:
            return {
                "status": "idle",
                "free_gb": round(self._media_free_gb(), 2),
            }
        return {
            "run_id": run["id"],
            "content_type": run["content_type"],
            "total": run["total"],
            "completed": run["completed"],
            "failed": run["failed"],
            "skipped": run["skipped"],
            "status": run["status"],
            "error_message": run.get("error_message"),
            "free_gb": round(self._media_free_gb(), 2),
        }


_agent: BulkWatchlistAgent | None = None


def get_bulk_agent(
    repo: CatalogRepository, orchestrator: IngestOrchestrator
) -> BulkWatchlistAgent:
    global _agent
    if _agent is None:
        _agent = BulkWatchlistAgent(repo, orchestrator)
    return _agent
