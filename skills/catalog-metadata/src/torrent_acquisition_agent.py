"""Agente de adquisición torrent on-demand (Prowlarr → qBittorrent)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import settings
from skill_telemetry import log
from torznab_client import get_torznab_client, normalize_search_title


@dataclass
class TorrentCandidate:
    title: str
    magnet: str
    size_bytes: int
    seeders: int

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024**3) if self.size_bytes else 0.0

    def user_message(self) -> str:
        return (
            f"Descargando {self.title} - "
            f"Tamaño: {self.size_gb:.2f} GB - Seeders: {self.seeders}"
        )


class TorrentAcquisitionAgent:
    async def search_and_select(
        self,
        series_title: str,
        season: int,
        episode: int,
        year: int | None = None,
    ) -> tuple[TorrentCandidate | None, str | None]:
        torznab = get_torznab_client()
        clean = normalize_search_title(series_title) or series_title
        best, err = await torznab.search_episode_best(
            clean, season, episode, year=year
        )
        if not best:
            return None, err or "No se encontró torrent adecuado"

        candidate = TorrentCandidate(
            title=best["title"],
            magnet=best["magnet"],
            size_bytes=int(best.get("size") or 0),
            seeders=int(best.get("seeders") or 0),
        )
        log.info(
            "torrent_agent_selected",
            series=clean[:40],
            season=season,
            episode=episode,
            torrent=candidate.title[:80],
            seeders=candidate.seeders,
        )
        return candidate, None

    async def search_movie(
        self,
        movie_title: str,
        year: int | None = None,
        *,
        extra_queries: list[str] | None = None,
    ) -> tuple[TorrentCandidate | None, str | None]:
        torznab = get_torznab_client()
        clean = normalize_search_title(movie_title) or movie_title
        best, err = await torznab.search_movie_best(
            clean, year=year, extra_queries=extra_queries
        )
        if not best:
            from yts_client import get_yts_client

            yts = get_yts_client()
            best, yts_err = await yts.search_movie_best(
                clean, year=year, extra_queries=extra_queries
            )
            if not best:
                return None, err or yts_err or "No se encontró torrent adecuado"
            log.info("torrent_agent_movie_yts_fallback", movie=clean[:40])

        candidate = TorrentCandidate(
            title=best["title"],
            magnet=best["magnet"],
            size_bytes=int(best.get("size") or 0),
            seeders=int(best.get("seeders") or 0),
        )
        log.info(
            "torrent_agent_movie_selected",
            movie=clean[:40],
            torrent=candidate.title[:80],
            seeders=candidate.seeders,
        )
        return candidate, None


_agent: TorrentAcquisitionAgent | None = None


def get_torrent_agent() -> TorrentAcquisitionAgent:
    global _agent
    if _agent is None:
        _agent = TorrentAcquisitionAgent()
    return _agent


def format_acquire_response(candidate: TorrentCandidate) -> dict[str, Any]:
    return {
        "torrent_title": candidate.title,
        "torrent_size_gb": round(candidate.size_gb, 2),
        "seeders": candidate.seeders,
        "message": candidate.user_message(),
    }
