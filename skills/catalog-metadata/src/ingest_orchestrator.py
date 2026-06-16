"""Orquestador batch: Torznab → qBittorrent/libtorrent → Skill #2."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from config import settings
from db.repository import CatalogRepository
from qbittorrent_client import get_qbittorrent_client
from skill_telemetry import (
    batch_ingest_total,
    log,
    record_error,
    resolve_magnets_total,
)
from media_library import (
    build_media_manifest_url,
    clear_series_index_cache,
    find_subtitle_for_video,
    resolve_episode_media,
    resolve_movie_media,
)
from torrent_acquisition_agent import (
    format_acquire_response,
    get_torrent_agent,
)
from torznab_client import get_torznab_client
from url_utils import build_manifest_url, normalize_manifest_url


class IngestOrchestrator:
    def __init__(self, repo: CatalogRepository) -> None:
        self.repo = repo
        self._http: httpx.AsyncClient | None = None
        self._acquire_in_progress: set[str] = set()
        self._acquire_messages: dict[str, str] = {}

    async def start(self) -> None:
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=3600.0))

    async def stop(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    async def resolve_magnets(
        self,
        *,
        priority_only: bool = True,
        limit: int | None = None,
    ) -> dict[str, int]:
        limit = limit or settings.resolve_limit_default
        torznab = get_torznab_client()
        titles = await self.repo.get_pending_resolve(
            priority_only=priority_only, limit=limit
        )

        resolved = 0
        failed = 0

        for title in titles:
            await self.repo.update_title(
                title["id"],
                pipeline_status="resolving",
                error_message=None,
            )
            magnet, err = await torznab.search_magnet(
                title["title"],
                title["content_type"],
                year=title.get("year"),
            )
            if magnet:
                await self.repo.update_title(
                    title["id"],
                    magnet_uri=magnet,
                    magnet_status="resolved",
                    magnet_source=settings.indexer_provider,
                    pipeline_status="catalog",
                )
                resolved += 1
                resolve_magnets_total.labels(result="resolved").inc()
            else:
                await self.repo.update_title(
                    title["id"],
                    magnet_status="failed",
                    pipeline_status="failed",
                    error_message=err,
                )
                failed += 1
                resolve_magnets_total.labels(result="failed").inc()

        return {"resolved": resolved, "failed": failed, "processed": len(titles)}

    async def batch_ingest(
        self,
        *,
        priority_only: bool = True,
        limit: int | None = None,
        concurrency: int | None = None,
    ) -> dict[str, int]:
        limit = limit or settings.ingest_limit_default
        concurrency = concurrency or settings.batch_concurrency
        titles = await self.repo.get_ready_for_ingest(
            priority_only=priority_only, limit=limit
        )

        if not titles:
            return {"success": 0, "failed": 0, "processed": 0}

        sem = asyncio.Semaphore(concurrency)
        results = await asyncio.gather(
            *[self._ingest_one(t, sem) for t in titles],
            return_exceptions=True,
        )

        success = sum(1 for r in results if r is True)
        failed = len(results) - success
        return {"success": success, "failed": failed, "processed": len(titles)}

    async def _ingest_one(self, title: dict, sem: asyncio.Semaphore) -> bool:
        async with sem:
            tid = title["id"]
            magnet = title.get("magnet_uri")
            if not magnet or not self._http:
                return False

            try:
                await self.repo.update_title(
                    tid, pipeline_status="ingesting", error_message=None
                )

                use_qbit = settings.ingest_mode in ("qbittorrent", "auto")
                job_id = None
                ingest_mode = "libtorrent"

                if use_qbit:
                    job_id, ingest_mode = await self._try_qbittorrent_ingest(
                        tid, magnet
                    )

                if not job_id:
                    job_id, ingest_mode = await self._libtorrent_ingest(tid, magnet)

                manifest_url = build_manifest_url(job_id)
                await self.repo.update_title(tid, transcode_job_id=job_id)

                ready = await self._poll_transcode(job_id)
                if not ready:
                    raise RuntimeError("Transcode timed out or failed")

                await self.repo.update_title(
                    tid,
                    pipeline_status="ready",
                    manifest_url=manifest_url,
                    ingest_mode=ingest_mode,
                )
                batch_ingest_total.labels(result="success").inc()
                log.info("batch_ingest_ok", title_id=tid, job_id=job_id, mode=ingest_mode)
                return True

            except Exception as exc:
                await self.repo.update_title(
                    tid,
                    pipeline_status="failed",
                    error_message=str(exc),
                )
                batch_ingest_total.labels(result="failed").inc()
                record_error("batch_ingest_failed")
                log.error("batch_ingest_failed", title_id=tid, error=str(exc))
                return False

    async def _try_qbittorrent_ingest(
        self, title_id: str, magnet: str
    ) -> tuple[str | None, str]:
        qbit = get_qbittorrent_client()
        try:
            added = await qbit.add_magnet(magnet, title_id=title_id)
            if not added:
                return None, "qbittorrent"

            file_path, infohash = await qbit.wait_for_complete(magnet)
            if not file_path:
                return None, "qbittorrent"

            await self.repo.update_title(
                title_id,
                qbittorrent_hash=infohash,
                ingest_mode="qbittorrent",
            )

            job = await self._http.post(
                f"{settings.storage_hls_base_url.rstrip('/')}/api/v1/transcode",
                json={
                    "source_type": "file",
                    "source_url": file_path,
                },
            )
            job.raise_for_status()
            return job.json()["job_id"], "qbittorrent"
        except Exception as exc:
            log.warning("qbittorrent_fallback", title_id=title_id, error=str(exc))
            return None, "qbittorrent"

    async def _libtorrent_ingest(self, title_id: str, magnet: str) -> tuple[str, str]:
        ing = await self._http.post(
            f"{settings.ingestion_base_url.rstrip('/')}/api/v1/ingest",
            json={"magnet_uri": magnet},
        )
        ing.raise_for_status()
        session_id = ing.json()["session_id"]

        await self.repo.update_title(
            title_id,
            ingest_session_id=session_id,
            pipeline_status="transcoding",
            ingest_mode="libtorrent",
        )

        job = await self._http.post(
            f"{settings.storage_hls_base_url.rstrip('/')}/api/v1/transcode",
            json={"session_id": session_id, "source_type": "stream"},
        )
        job.raise_for_status()
        return job.json()["job_id"], "libtorrent"

    async def _check_transcode_state(self, job_id: str) -> str:
        if not self._http:
            return "failed"
        url = f"{settings.storage_hls_base_url.rstrip('/')}/api/v1/status/{job_id}"
        try:
            resp = await self._http.get(url)
            if resp.status_code == 404:
                return "failed"
            state = resp.json().get("state")
            if state in ("ready", "failed"):
                return state
        except Exception:
            return "pending"
        return "pending"

    async def _poll_transcode(self, job_id: str) -> bool:
        if not self._http:
            return False

        deadline = time.monotonic() + settings.transcode_timeout_seconds
        while time.monotonic() < deadline:
            state = await self._check_transcode_state(job_id)
            if state == "ready":
                return True
            if state == "failed":
                return False
            await asyncio.sleep(settings.transcode_poll_interval)

        return False

    async def _maybe_complete_transcode(
        self, episode_id: str, job_id: str
    ) -> dict[str, Any] | None:
        state = await self._check_transcode_state(job_id)
        if state != "ready":
            return None
        manifest_url = build_manifest_url(job_id)
        await self.repo.update_episode(
            episode_id,
            pipeline_status="ready",
            manifest_url=manifest_url,
            error_message=None,
        )
        return {
            "episode_id": episode_id,
            "pipeline_status": "ready",
            "manifest_url": normalize_manifest_url(manifest_url),
            "transcode_job_id": job_id,
            "message": None,
        }

    async def _maybe_complete_title_transcode(
        self, title_id: str, job_id: str
    ) -> dict[str, Any] | None:
        state = await self._check_transcode_state(job_id)
        if state != "ready":
            return None
        manifest_url = build_manifest_url(job_id)
        await self.repo.update_title(
            title_id,
            pipeline_status="ready",
            manifest_url=manifest_url,
            error_message=None,
        )
        return {
            "title_id": title_id,
            "pipeline_status": "ready",
            "manifest_url": normalize_manifest_url(manifest_url),
            "transcode_job_id": job_id,
            "message": None,
        }

    async def get_title_status(self, title_id: str) -> dict[str, Any]:
        title = await self.repo.get_title(title_id)
        if not title:
            from errors import NotFoundError

            raise NotFoundError(f"Title {title_id} not found")

        if (
            title.get("pipeline_status") == "transcoding"
            and title.get("transcode_job_id")
        ):
            completed = await self._maybe_complete_title_transcode(
                title_id, title["transcode_job_id"]
            )
            if completed:
                title = await self.repo.get_title(title_id)

        return {
            "title_id": title_id,
            "pipeline_status": title.get("pipeline_status"),
            "manifest_url": normalize_manifest_url(title.get("manifest_url")),
            "transcode_job_id": title.get("transcode_job_id"),
            "error_message": title.get("error_message"),
        }

    async def resolve_episode_magnet(self, episode_id: str) -> dict[str, str]:
        ep = await self.repo.get_episode(episode_id)
        if not ep:
            from errors import NotFoundError

            raise NotFoundError(f"Episode {episode_id} not found")

        series = await self.repo.get_title(ep["series_id"])
        if not series:
            from errors import NotFoundError

            raise NotFoundError(f"Series {ep['series_id']} not found")

        await self.repo.update_episode(
            episode_id, pipeline_status="resolving", error_message=None
        )
        torznab = get_torznab_client()
        magnet, err = await torznab.search_episode_magnet(
            series["title"],
            ep["season_number"],
            ep["episode_number"],
            year=series.get("year"),
        )
        if magnet:
            await self.repo.update_episode(
                episode_id,
                magnet_uri=magnet,
                magnet_status="resolved",
                magnet_source=settings.indexer_provider,
                pipeline_status="catalog",
            )
            resolve_magnets_total.labels(result="resolved").inc()
            return {"status": "resolved", "episode_id": episode_id}

        await self.repo.update_episode(
            episode_id,
            magnet_status="failed",
            pipeline_status="failed",
            error_message=err,
        )
        resolve_magnets_total.labels(result="failed").inc()
        return {"status": "failed", "episode_id": episode_id, "error": err or ""}

    async def resolve_episodes_batch(
        self,
        *,
        series_id: str,
        season_number: int | None = None,
        limit: int | None = None,
    ) -> dict[str, int]:
        limit = limit or settings.episode_resolve_limit
        episodes = await self.repo.get_episodes_pending_resolve(
            series_id=series_id,
            season_number=season_number,
            limit=limit,
        )
        resolved = 0
        failed = 0
        for ep in episodes:
            result = await self.resolve_episode_magnet(ep["id"])
            if result.get("status") == "resolved":
                resolved += 1
            else:
                failed += 1
        return {"resolved": resolved, "failed": failed, "processed": len(episodes)}

    async def get_episode_status(self, episode_id: str) -> dict[str, Any]:
        ep = await self.repo.get_episode(episode_id)
        if not ep:
            from errors import NotFoundError

            raise NotFoundError(f"Episode {episode_id} not found")

        if (
            ep.get("pipeline_status") == "transcoding"
            and ep.get("transcode_job_id")
        ):
            completed = await self._maybe_complete_transcode(
                episode_id, ep["transcode_job_id"]
            )
            if completed:
                ep = await self.repo.get_episode(episode_id)

        stage = self._episode_stage(ep)
        download_progress = None
        download_speed_mbps = None
        if stage == "downloading" and ep.get("qbittorrent_hash"):
            qbit = get_qbittorrent_client()
            prog = await qbit.get_torrent_progress(ep.get("qbittorrent_hash"))
            download_progress = prog.get("progress")
            download_speed_mbps = prog.get("dlspeed")
            if download_progress is not None and download_progress > 0:
                msg = self._acquire_messages.get(episode_id) or "Descargando"
                self._acquire_messages[episode_id] = (
                    f"{msg.split(' - ')[0]} - {download_progress:.0f}%"
                )

        return {
            "episode_id": episode_id,
            "pipeline_status": ep.get("pipeline_status"),
            "magnet_status": ep.get("magnet_status"),
            "manifest_url": normalize_manifest_url(ep.get("manifest_url")),
            "transcode_job_id": ep.get("transcode_job_id"),
            "error_message": ep.get("error_message"),
            "stage": stage,
            "message": self._acquire_messages.get(episode_id),
            "download_progress": download_progress,
            "download_speed_mbps": download_speed_mbps,
        }

    def _episode_stage(self, ep: dict[str, Any]) -> str:
        status = ep.get("pipeline_status", "catalog")
        if status == "resolving":
            return "searching"
        if status == "ingesting":
            if ep.get("magnet_status") == "resolved" and ep.get("magnet_uri"):
                return "downloading"
            return "ingesting"
        if status == "transcoding":
            return "transcoding"
        if status == "ready":
            return "ready"
        if status == "failed":
            return "failed"
        return "catalog"

    async def play_episode(self, episode_id: str) -> dict[str, Any]:
        ep = await self.repo.get_episode(episode_id)
        if not ep:
            from errors import NotFoundError

            raise NotFoundError(f"Episode {episode_id} not found")

        if ep.get("pipeline_status") == "ready" and ep.get("manifest_url"):
            return {
                "episode_id": episode_id,
                "pipeline_status": "ready",
                "manifest_url": normalize_manifest_url(ep["manifest_url"]),
                "transcode_job_id": ep.get("transcode_job_id"),
                "message": "Already ready",
            }

        if settings.media_source_mode in ("library", "hybrid"):
            result = await self._play_episode_library(episode_id, ep)
            if settings.media_source_mode == "library":
                return result
            if result.get("pipeline_status") in ("ready", "transcoding"):
                return result
            msg = result.get("message") or ""
            if "No local media file" in msg and settings.auto_acquire_on_play:
                return await self.acquire_episode(episode_id)
            return result

        if ep.get("magnet_status") != "resolved" or not ep.get("magnet_uri"):
            await self.resolve_episode_magnet(episode_id)
            ep = await self.repo.get_episode(episode_id)
            if not ep or ep.get("magnet_status") != "resolved":
                return {
                    "episode_id": episode_id,
                    "pipeline_status": ep.get("pipeline_status", "failed") if ep else "failed",
                    "manifest_url": None,
                    "message": ep.get("error_message") if ep else "Magnet resolve failed",
                }

        ok = await self._ingest_episode_one(ep)
        ep = await self.repo.get_episode(episode_id)
        return {
            "episode_id": episode_id,
            "pipeline_status": ep.get("pipeline_status") if ep else "failed",
            "manifest_url": normalize_manifest_url(ep.get("manifest_url")) if ep else None,
            "transcode_job_id": ep.get("transcode_job_id") if ep else None,
            "message": None if ok else (ep.get("error_message") if ep else "Ingest failed"),
        }

    async def acquire_episode(self, episode_id: str) -> dict[str, Any]:
        ep = await self.repo.get_episode(episode_id)
        if not ep:
            from errors import NotFoundError

            raise NotFoundError(f"Episode {episode_id} not found")

        if ep.get("pipeline_status") == "ready" and ep.get("manifest_url"):
            return {
                "episode_id": episode_id,
                "pipeline_status": "ready",
                "manifest_url": normalize_manifest_url(ep["manifest_url"]),
                "transcode_job_id": ep.get("transcode_job_id"),
                "stage": "ready",
                "message": "Already ready",
            }

        if (
            ep.get("pipeline_status") == "transcoding"
            and ep.get("transcode_job_id")
        ):
            completed = await self._maybe_complete_transcode(
                episode_id, ep["transcode_job_id"]
            )
            if completed:
                completed["stage"] = "ready"
                return completed
            return {
                "episode_id": episode_id,
                "pipeline_status": "transcoding",
                "manifest_url": None,
                "transcode_job_id": ep.get("transcode_job_id"),
                "stage": "transcoding",
                "message": "Transcode en progreso",
            }

        if episode_id in self._acquire_in_progress:
            ep = await self.repo.get_episode(episode_id)
            return self._build_acquire_status_response(episode_id, ep)

        series = await self.repo.get_title(ep["series_id"])
        if not series:
            from errors import NotFoundError

            raise NotFoundError(f"Series {ep['series_id']} not found")

        await self.scan_series_library(ep["series_id"])
        ep = await self.repo.get_episode(episode_id)
        lib = await self._play_episode_library(episode_id, ep)
        if lib.get("pipeline_status") in ("ready", "transcoding"):
            refreshed = await self.repo.get_episode(episode_id)
            lib["stage"] = self._episode_stage(refreshed or ep)
            return lib

        await self.repo.update_episode(
            episode_id, pipeline_status="resolving", error_message=None
        )
        agent = get_torrent_agent()
        candidate, err = await agent.search_and_select(
            series["title"],
            ep["season_number"],
            ep["episode_number"],
            year=series.get("year"),
        )
        if not candidate:
            await self.repo.update_episode(
                episode_id,
                pipeline_status="failed",
                magnet_status="failed",
                error_message=err,
            )
            return {
                "episode_id": episode_id,
                "pipeline_status": "failed",
                "manifest_url": None,
                "stage": "failed",
                "message": err,
            }

        extra = format_acquire_response(candidate)
        self._acquire_messages[episode_id] = extra["message"]

        await self.repo.update_episode(
            episode_id,
            magnet_uri=candidate.magnet,
            magnet_status="resolved",
            magnet_source=settings.indexer_provider,
            pipeline_status="ingesting",
            error_message=None,
        )

        qbit = get_qbittorrent_client()
        try:
            added = await qbit.add_magnet(candidate.magnet, title_id=episode_id)
            if not added:
                raise RuntimeError("qBittorrent rejected magnet")
            infohash = qbit._extract_hash(candidate.magnet)
            if infohash:
                await self.repo.update_episode(
                    episode_id, qbittorrent_hash=infohash
                )
        except Exception as exc:
            await self.repo.update_episode(
                episode_id,
                pipeline_status="failed",
                error_message=str(exc),
            )
            self._acquire_messages.pop(episode_id, None)
            return {
                "episode_id": episode_id,
                "pipeline_status": "failed",
                "manifest_url": None,
                "stage": "failed",
                "message": str(exc),
            }

        self._acquire_in_progress.add(episode_id)
        asyncio.create_task(
            self._complete_acquire_background(
                episode_id,
                candidate.magnet,
                ep["season_number"],
                ep["episode_number"],
                ep["series_id"],
            )
        )

        return {
            "episode_id": episode_id,
            "pipeline_status": "ingesting",
            "manifest_url": None,
            "transcode_job_id": None,
            "stage": "downloading",
            **extra,
        }

    def _build_acquire_status_response(
        self, episode_id: str, ep: dict[str, Any] | None
    ) -> dict[str, Any]:
        if not ep:
            return {
                "episode_id": episode_id,
                "pipeline_status": "failed",
                "manifest_url": None,
                "stage": "failed",
                "message": "Episode not found",
            }
        return {
            "episode_id": episode_id,
            "pipeline_status": ep.get("pipeline_status", "catalog"),
            "manifest_url": normalize_manifest_url(ep.get("manifest_url")),
            "transcode_job_id": ep.get("transcode_job_id"),
            "stage": self._episode_stage(ep),
            "message": self._acquire_messages.get(episode_id),
        }

    async def _complete_acquire_background(
        self,
        episode_id: str,
        magnet: str,
        season: int,
        ep_num: int,
        series_id: str,
    ) -> None:
        try:
            qbit = get_qbittorrent_client()
            file_path, infohash = await qbit.wait_for_episode_complete(
                magnet, season, ep_num
            )
            if not file_path:
                err = infohash or "Download failed or timed out"
                await self.repo.update_episode(
                    episode_id,
                    pipeline_status="failed",
                    error_message=err,
                )
                return

            await self.repo.update_episode(
                episode_id,
                qbittorrent_hash=infohash,
                ingest_mode="qbittorrent",
            )

            await self.scan_series_library(series_id)
            ep = await self.repo.get_episode(episode_id)
            series = await self.repo.get_title(series_id)
            if not ep or not series:
                return

            source, media_type = resolve_episode_media(
                series_id=series_id,
                series_title=series["title"],
                season=season,
                episode=ep_num,
                stored_path=ep.get("source_path"),
            )
            if not source:
                source = file_path
                media_type = "file"

            await self.repo.update_episode(
                episode_id,
                source_path=source,
                pipeline_status="ingesting",
            )
            self._acquire_messages[episode_id] = "Transcodificando…"

            await self._ingest_from_file(
                episode_id, source, media_type, wait=False
            )
        except Exception as exc:
            log.error(
                "acquire_background_failed",
                episode_id=episode_id,
                error=str(exc),
            )
            await self.repo.update_episode(
                episode_id,
                pipeline_status="failed",
                error_message=str(exc),
            )
        finally:
            self._acquire_in_progress.discard(episode_id)

    async def _play_episode_library(
        self, episode_id: str, ep: dict[str, Any]
    ) -> dict[str, Any]:
        series = await self.repo.get_title(ep["series_id"])
        if not series:
            return {
                "episode_id": episode_id,
                "pipeline_status": "failed",
                "manifest_url": None,
                "message": f"Series {ep['series_id']} not found",
            }

        if (
            ep.get("pipeline_status") == "transcoding"
            and ep.get("transcode_job_id")
        ):
            completed = await self._maybe_complete_transcode(
                episode_id, ep["transcode_job_id"]
            )
            if completed:
                return completed
            return {
                "episode_id": episode_id,
                "pipeline_status": "transcoding",
                "manifest_url": None,
                "transcode_job_id": ep.get("transcode_job_id"),
                "message": "Transcode en progreso",
            }

        source, media_type = resolve_episode_media(
            series_id=ep["series_id"],
            series_title=series["title"],
            season=ep["season_number"],
            episode=ep["episode_number"],
            stored_path=ep.get("source_path"),
        )
        if not source:
            return {
                "episode_id": episode_id,
                "pipeline_status": ep.get("pipeline_status", "catalog"),
                "manifest_url": None,
                "message": media_type,
                "stage": "catalog",
            }

        await self.repo.update_episode(
            episode_id,
            source_path=source,
            magnet_status="skipped",
            magnet_source="library",
            pipeline_status="ingesting",
            error_message=None,
        )

        if media_type in ("hls", "url_hls"):
            if media_type == "hls":
                manifest_url = build_media_manifest_url(source)
            else:
                manifest_url = source
            await self.repo.update_episode(
                episode_id,
                pipeline_status="ready",
                manifest_url=manifest_url,
                ingest_mode="library",
            )
            return {
                "episode_id": episode_id,
                "pipeline_status": "ready",
                "manifest_url": normalize_manifest_url(manifest_url),
                "message": None,
            }

        ok = await self._ingest_from_file(
            episode_id, source, media_type, wait=False
        )
        ep = await self.repo.get_episode(episode_id)
        if ok and ep and ep.get("pipeline_status") == "transcoding":
            return {
                "episode_id": episode_id,
                "pipeline_status": "transcoding",
                "manifest_url": None,
                "transcode_job_id": ep.get("transcode_job_id"),
                "message": "Transcode iniciado",
            }
        return {
            "episode_id": episode_id,
            "pipeline_status": ep.get("pipeline_status") if ep else "failed",
            "manifest_url": normalize_manifest_url(ep.get("manifest_url")) if ep else None,
            "transcode_job_id": ep.get("transcode_job_id") if ep else None,
            "message": None if ok else (ep.get("error_message") if ep else "Ingest failed"),
        }

    async def play_movie(self, title_id: str) -> dict[str, Any]:
        title = await self.repo.get_title(title_id)
        if not title:
            from errors import NotFoundError

            raise NotFoundError(f"Title {title_id} not found")
        if title.get("content_type") != "movie":
            from errors import InvalidInputError

            raise InvalidInputError(f"{title_id} is not a movie")

        if title.get("pipeline_status") == "ready" and title.get("manifest_url"):
            return {
                "title_id": title_id,
                "pipeline_status": "ready",
                "manifest_url": normalize_manifest_url(title["manifest_url"]),
                "message": "Already ready",
            }

        if settings.media_source_mode not in ("library", "hybrid"):
            return {
                "title_id": title_id,
                "pipeline_status": title.get("pipeline_status", "catalog"),
                "manifest_url": None,
                "message": "Movie play requires library/hybrid mode or pre-ingested manifest",
            }

        if (
            title.get("pipeline_status") == "transcoding"
            and title.get("transcode_job_id")
        ):
            completed = await self._maybe_complete_title_transcode(
                title_id, title["transcode_job_id"]
            )
            if completed:
                return completed
            return {
                "title_id": title_id,
                "pipeline_status": "transcoding",
                "manifest_url": None,
                "transcode_job_id": title.get("transcode_job_id"),
                "message": "Transcode en progreso",
            }

        source, media_type = resolve_movie_media(
            title_id=title_id,
            title=title["title"],
            stored_path=title.get("source_path"),
        )
        if not source:
            await self.repo.update_title(
                title_id,
                pipeline_status="failed",
                error_message=media_type,
            )
            return {
                "title_id": title_id,
                "pipeline_status": "failed",
                "manifest_url": None,
                "message": media_type,
            }

        await self.repo.update_title(
            title_id,
            source_path=source,
            magnet_status="skipped",
            magnet_source="library",
            pipeline_status="ingesting",
            error_message=None,
        )

        if media_type in ("hls", "url_hls"):
            manifest_url = (
                build_media_manifest_url(source)
                if media_type == "hls"
                else source
            )
            await self.repo.update_title(
                title_id,
                pipeline_status="ready",
                manifest_url=manifest_url,
                ingest_mode="library",
            )
            return {
                "title_id": title_id,
                "pipeline_status": "ready",
                "manifest_url": normalize_manifest_url(manifest_url),
                "message": None,
            }

        ok = await self._ingest_title_from_file(
            title_id, source, media_type, wait=False
        )
        title = await self.repo.get_title(title_id)
        return {
            "title_id": title_id,
            "pipeline_status": title.get("pipeline_status") if title else "failed",
            "manifest_url": normalize_manifest_url(title.get("manifest_url")) if title else None,
            "transcode_job_id": title.get("transcode_job_id") if title else None,
            "message": None if ok else (title.get("error_message") if title else "Ingest failed"),
        }

    async def _ingest_from_file(
        self,
        episode_id: str,
        source: str,
        media_type: str,
        *,
        wait: bool = True,
    ) -> bool:
        if not self._http:
            return False
        try:
            await self.repo.update_episode(
                episode_id, pipeline_status="transcoding", ingest_mode="library"
            )
            payload: dict[str, Any] = {"source_type": "file"}
            if media_type == "url":
                payload = {"source_type": "stream", "source_url": source}
            else:
                payload["source_url"] = source

            job = await self._http.post(
                f"{settings.storage_hls_base_url.rstrip('/')}/api/v1/transcode",
                json=payload,
            )
            job.raise_for_status()
            job_id = job.json()["job_id"]
            manifest_url = build_manifest_url(job_id)
            await self.repo.update_episode(episode_id, transcode_job_id=job_id)

            if not wait:
                batch_ingest_total.labels(result="success").inc()
                return True

            ready = await self._poll_transcode(job_id)
            if not ready:
                raise RuntimeError("Transcode timed out or failed")

            await self.repo.update_episode(
                episode_id,
                pipeline_status="ready",
                manifest_url=manifest_url,
            )
            batch_ingest_total.labels(result="success").inc()
            return True
        except Exception as exc:
            await self.repo.update_episode(
                episode_id,
                pipeline_status="failed",
                error_message=str(exc),
            )
            batch_ingest_total.labels(result="failed").inc()
            record_error("episode_ingest_failed")
            log.error("episode_library_ingest_failed", episode_id=episode_id, error=str(exc))
            return False

    async def _pretranscode_batch(
        self, items: list[tuple[str, str, str]]
    ) -> None:
        sem = asyncio.Semaphore(max(1, settings.episode_play_concurrency))

        async def _one(episode_id: str, source: str, media_type: str) -> None:
            async with sem:
                ep = await self.repo.get_episode(episode_id)
                if not ep or ep.get("pipeline_status") == "ready":
                    return
                if ep.get("pipeline_status") == "transcoding" and ep.get(
                    "transcode_job_id"
                ):
                    return
                await self._ingest_from_file(
                    episode_id, source, media_type, wait=True
                )

        await asyncio.gather(*(_one(*item) for item in items))

    async def scan_series_library(self, series_id: str) -> dict[str, int]:
        series = await self.repo.get_title(series_id)
        if not series:
            from errors import NotFoundError

            raise NotFoundError(f"Series {series_id} not found")

        clear_series_index_cache(series_id)
        episodes = await self.repo.list_episodes(series_id)
        linked = 0
        ready = 0
        pending_transcode: list[tuple[str, str, str]] = []

        for ep in episodes:
            source, media_type = resolve_episode_media(
                series_id=series_id,
                series_title=series["title"],
                season=ep["season_number"],
                episode=ep["episode_number"],
                stored_path=ep.get("source_path"),
            )
            if not source:
                continue

            linked += 1
            subtitle_path = None
            if media_type == "file":
                from pathlib import Path

                subtitle_path = find_subtitle_for_video(Path(source))

            if media_type in ("hls", "url_hls"):
                manifest_url = (
                    build_media_manifest_url(source)
                    if media_type == "hls"
                    else source
                )
                await self.repo.update_episode(
                    ep["id"],
                    source_path=source,
                    subtitle_path=subtitle_path,
                    magnet_status="skipped",
                    magnet_source="library",
                    pipeline_status="ready",
                    manifest_url=manifest_url,
                    ingest_mode="library",
                    error_message=None,
                )
                ready += 1
            else:
                await self.repo.update_episode(
                    ep["id"],
                    source_path=source,
                    subtitle_path=subtitle_path,
                    magnet_status="skipped",
                    magnet_source="library",
                    error_message=None,
                )
                if ep.get("pipeline_status") != "ready":
                    pending_transcode.append((ep["id"], source, media_type))

        if pending_transcode and settings.media_source_mode == "library":
            asyncio.create_task(self._pretranscode_batch(pending_transcode))

        return {"resolved": ready, "failed": 0, "processed": linked}

    async def scan_movie_library(self, title_id: str) -> dict[str, int]:
        title = await self.repo.get_title(title_id)
        if not title:
            from errors import NotFoundError

            raise NotFoundError(f"Title {title_id} not found")
        if title.get("content_type") != "movie":
            from errors import InvalidInputError

            raise InvalidInputError(f"{title_id} is not a movie")

        source, media_type = resolve_movie_media(
            title_id=title_id,
            title=title["title"],
            stored_path=title.get("source_path"),
        )
        if not source:
            return {"resolved": 0, "failed": 1, "processed": 0}

        if media_type in ("hls", "url_hls"):
            manifest_url = (
                build_media_manifest_url(source)
                if media_type == "hls"
                else source
            )
            await self.repo.update_title(
                title_id,
                source_path=source,
                magnet_status="skipped",
                magnet_source="library",
                pipeline_status="ready",
                manifest_url=manifest_url,
                ingest_mode="library",
                error_message=None,
            )
            return {"resolved": 1, "failed": 0, "processed": 1}

        await self.repo.update_title(
            title_id,
            source_path=source,
            magnet_status="skipped",
            magnet_source="library",
            pipeline_status="ingesting",
            error_message=None,
        )
        ok = await self._ingest_title_from_file(
            title_id, source, media_type, wait=False
        )
        if ok:
            refreshed = await self.repo.get_title(title_id)
            if refreshed and refreshed.get("pipeline_status") == "ready":
                return {"resolved": 1, "failed": 0, "processed": 1}
        return {"resolved": 0, "failed": 0, "processed": 1}

    async def scan_all_library(self) -> dict[str, int]:
        series_ids = await self.repo.list_series_ids(content_type="series")
        movie_ids = await self.repo.list_series_ids(content_type="movie")
        linked = 0
        ready = 0
        for series_id in series_ids:
            try:
                result = await self.scan_series_library(series_id)
                linked += result.get("processed", 0)
                ready += result.get("resolved", 0)
            except Exception as exc:
                log.warning("scan_all_library_failed", series_id=series_id, error=str(exc))
        for movie_id in movie_ids:
            try:
                result = await self.scan_movie_library(movie_id)
                linked += result.get("processed", 0)
                ready += result.get("resolved", 0)
            except Exception as exc:
                log.warning("scan_all_library_failed", movie_id=movie_id, error=str(exc))
        return {"resolved": ready, "failed": 0, "processed": linked}

    async def _ingest_title_from_file(
        self,
        title_id: str,
        source: str,
        media_type: str,
        *,
        wait: bool = True,
    ) -> bool:
        if not self._http:
            return False
        try:
            await self.repo.update_title(
                title_id, pipeline_status="transcoding", ingest_mode="library"
            )
            payload: dict[str, Any] = {"source_type": "file"}
            if media_type == "url":
                payload = {"source_type": "stream", "source_url": source}
            else:
                payload["source_url"] = source

            job = await self._http.post(
                f"{settings.storage_hls_base_url.rstrip('/')}/api/v1/transcode",
                json=payload,
            )
            job.raise_for_status()
            job_id = job.json()["job_id"]
            manifest_url = build_manifest_url(job_id)
            await self.repo.update_title(title_id, transcode_job_id=job_id)

            if not wait:
                batch_ingest_total.labels(result="success").inc()
                return True

            ready = await self._poll_transcode(job_id)
            if not ready:
                raise RuntimeError("Transcode timed out or failed")

            await self.repo.update_title(
                title_id,
                pipeline_status="ready",
                manifest_url=manifest_url,
            )
            batch_ingest_total.labels(result="success").inc()
            return True
        except Exception as exc:
            await self.repo.update_title(
                title_id,
                pipeline_status="failed",
                error_message=str(exc),
            )
            batch_ingest_total.labels(result="failed").inc()
            record_error("batch_ingest_failed")
            log.error("movie_library_ingest_failed", title_id=title_id, error=str(exc))
            return False

    async def _ingest_episode_one(self, episode: dict) -> bool:
        eid = episode["id"]
        magnet = episode.get("magnet_uri")
        if not magnet or not self._http:
            return False

        season = episode["season_number"]
        ep_num = episode["episode_number"]
        series_id = episode["series_id"]

        try:
            await self.repo.update_episode(
                eid, pipeline_status="ingesting", error_message=None
            )

            use_qbit = settings.ingest_mode in ("qbittorrent", "auto")
            job_id = None
            ingest_mode = "libtorrent"

            if use_qbit:
                job_id, ingest_mode = await self._try_qbittorrent_episode_ingest(
                    eid, magnet, season, ep_num, series_id=series_id
                )

            if not job_id:
                job_id, ingest_mode = await self._libtorrent_episode_ingest(
                    eid, magnet, season, ep_num
                )

            manifest_url = build_manifest_url(job_id)
            await self.repo.update_episode(eid, transcode_job_id=job_id)

            ready = await self._poll_transcode(job_id)
            if not ready:
                raise RuntimeError("Transcode timed out or failed")

            await self.repo.update_episode(
                eid,
                pipeline_status="ready",
                manifest_url=manifest_url,
                ingest_mode=ingest_mode,
            )
            batch_ingest_total.labels(result="success").inc()
            log.info("episode_ingest_ok", episode_id=eid, job_id=job_id)
            return True

        except Exception as exc:
            await self.repo.update_episode(
                eid,
                pipeline_status="failed",
                error_message=str(exc),
            )
            batch_ingest_total.labels(result="failed").inc()
            record_error("episode_ingest_failed")
            log.error("episode_ingest_failed", episode_id=eid, error=str(exc))
            return False

    async def _libtorrent_episode_ingest(
        self, episode_id: str, magnet: str, season: int, episode: int
    ) -> tuple[str, str]:
        ing = await self._http.post(
            f"{settings.ingestion_base_url.rstrip('/')}/api/v1/ingest",
            json={
                "magnet_uri": magnet,
                "season_number": season,
                "episode_number": episode,
            },
        )
        ing.raise_for_status()
        session_id = ing.json()["session_id"]

        await self.repo.update_episode(
            episode_id,
            ingest_session_id=session_id,
            pipeline_status="transcoding",
            ingest_mode="libtorrent",
        )

        job = await self._http.post(
            f"{settings.storage_hls_base_url.rstrip('/')}/api/v1/transcode",
            json={
                "session_id": session_id,
                "source_type": "stream",
                "season_number": season,
                "episode_number": episode,
            },
        )
        job.raise_for_status()
        return job.json()["job_id"], "libtorrent"

    async def _try_qbittorrent_episode_ingest(
        self,
        episode_id: str,
        magnet: str,
        season: int,
        episode: int,
        *,
        series_id: str,
    ) -> tuple[str | None, str]:
        qbit = get_qbittorrent_client()
        try:
            added = await qbit.add_magnet(magnet, title_id=episode_id)
            if not added:
                return None, "qbittorrent"

            file_path, infohash = await qbit.wait_for_episode_complete(
                magnet, season, episode
            )
            if not file_path:
                return None, "qbittorrent"

            await self.repo.update_episode(
                episode_id,
                qbittorrent_hash=infohash,
                ingest_mode="qbittorrent",
            )

            job = await self._http.post(
                f"{settings.storage_hls_base_url.rstrip('/')}/api/v1/transcode",
                json={
                    "source_type": "file",
                    "source_url": file_path,
                },
            )
            job.raise_for_status()
            return job.json()["job_id"], "qbittorrent"
        except Exception as exc:
            log.warning("qbittorrent_episode_fallback", episode_id=episode_id, error=str(exc))
            return None, "qbittorrent"


_orch: IngestOrchestrator | None = None


def get_orchestrator(repo: CatalogRepository) -> IngestOrchestrator:
    global _orch
    if _orch is None:
        _orch = IngestOrchestrator(repo)
    return _orch
