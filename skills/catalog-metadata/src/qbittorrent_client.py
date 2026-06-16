"""Cliente qBittorrent Web API v2."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

import httpx

_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from episode_utils import matches_episode_filename  # noqa: E402

from config import settings
from errors import UpstreamError
from skill_telemetry import log, record_error


class QBittorrentClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._sid: str | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.qbittorrent_url.rstrip("/"),
            timeout=httpx.Timeout(30.0, read=120.0),
        )
        await self._login()

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._sid = None

    async def _login(self) -> None:
        if not self._client:
            return
        try:
            resp = await self._client.post(
                "/api/v2/auth/login",
                data={
                    "username": settings.qbittorrent_user,
                    "password": settings.qbittorrent_pass,
                },
            )
            if resp.text != "Ok.":
                log.warning("qbittorrent_login_failed", response=resp.text[:80])
        except httpx.HTTPError as exc:
            record_error("qbittorrent_error")
            log.warning("qbittorrent_unreachable", error=str(exc))

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self._client:
            raise UpstreamError("qBittorrent client not initialized")
        resp = await self._client.request(method, path, **kwargs)
        if resp.status_code == 403:
            await self._login()
            resp = await self._client.request(method, path, **kwargs)
        return resp

    async def add_magnet(
        self, magnet: str, *, title_id: str, category: str = "streaming"
    ) -> bool:
        if not self._client:
            raise UpstreamError("qBittorrent client not initialized")

        try:
            resp = await self._request(
                "POST",
                "/api/v2/torrents/add",
                data={
                    "urls": magnet,
                    "category": category,
                    "tags": f"catalog,{title_id}",
                    "paused": "false",
                },
            )
            return resp.text == "Ok."
        except httpx.HTTPError as exc:
            record_error("qbittorrent_error")
            raise UpstreamError(f"qBittorrent add failed: {exc}") from exc

    async def wait_for_complete(
        self, magnet: str, timeout: int | None = None
    ) -> tuple[str | None, str | None]:
        """Retorna (file_path, infohash) o (None, error)."""
        timeout = timeout or settings.qbittorrent_timeout_seconds
        if not self._client:
            return None, "qBittorrent not initialized"

        infohash = self._extract_hash(magnet)
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            try:
                resp = await self._request(
                    "GET",
                    "/api/v2/torrents/info",
                    params={"hashes": infohash} if infohash else {},
                )
                torrents = resp.json()
            except httpx.HTTPError as exc:
                return None, str(exc)

            for t in torrents:
                if infohash and t.get("hash", "").lower() != infohash.lower():
                    continue
                progress = t.get("progress", 0)
                if progress >= 1.0:
                    path = self._resolve_file_path(t)
                    if path:
                        return path, t.get("hash")
                    return None, "Download complete but no media file found"
            await asyncio.sleep(5)

        return None, "qBittorrent download timeout"

    async def get_torrent_progress(
        self, infohash: str | None
    ) -> dict[str, float | None]:
        if not self._client or not infohash:
            return {"progress": None, "dlspeed": None, "eta": None}
        try:
            resp = await self._request(
                "GET",
                "/api/v2/torrents/info",
                params={"hashes": infohash},
            )
            torrents = resp.json()
            for t in torrents:
                if t.get("hash", "").lower() == infohash.lower():
                    progress = float(t.get("progress", 0)) * 100.0
                    dlspeed = float(t.get("dlspeed", 0)) / (1024 * 1024)
                    eta = float(t.get("eta", 0)) if t.get("eta", -1) >= 0 else None
                    return {"progress": progress, "dlspeed": dlspeed, "eta": eta}
        except httpx.HTTPError:
            pass
        return {"progress": None, "dlspeed": None, "eta": None}

    async def wait_for_episode_complete(
        self,
        magnet: str,
        season: int,
        episode: int,
        timeout: int | None = None,
    ) -> tuple[str | None, str | None]:
        timeout = timeout or settings.qbittorrent_timeout_seconds
        if not self._client:
            return None, "qBittorrent not initialized"

        infohash = self._extract_hash(magnet)
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            try:
                resp = await self._request(
                    "GET",
                    "/api/v2/torrents/info",
                    params={"hashes": infohash} if infohash else {},
                )
                torrents = resp.json()
            except httpx.HTTPError as exc:
                return None, str(exc)

            for t in torrents:
                if infohash and t.get("hash", "").lower() != infohash.lower():
                    continue
                progress = t.get("progress", 0)
                if progress >= 1.0:
                    path = self._resolve_episode_file_path(t, season, episode)
                    if path:
                        return path, t.get("hash")
                    return None, "Download complete but episode file not found"
            await asyncio.sleep(5)

        return None, "qBittorrent download timeout"

    def _extract_hash(self, magnet: str) -> str | None:
        for part in magnet.split("&"):
            if part.lower().startswith("xt=urn:btih:"):
                return part.split(":")[-1]
        return None

    def _resolve_file_path(self, torrent: dict) -> str | None:
        save_path = torrent.get("save_path", settings.qbittorrent_download_path)
        name = torrent.get("name", "")
        content_path = torrent.get("content_path") or ""

        candidates = []
        if content_path:
            candidates.append(content_path)
        if name:
            candidates.append(str(Path(save_path) / name))

        media_ext = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".ts", ".wmv"}
        for c in candidates:
            p = Path(c)
            if p.is_file() and p.suffix.lower() in media_ext:
                return str(p)
            if p.is_dir():
                for f in sorted(p.rglob("*")):
                    if f.is_file() and f.suffix.lower() in media_ext:
                        return str(f)
        return None

    def _resolve_episode_file_path(
        self, torrent: dict, season: int, episode: int
    ) -> str | None:
        save_path = torrent.get("save_path", settings.qbittorrent_download_path)
        name = torrent.get("name", "")
        content_path = torrent.get("content_path") or ""

        roots: list[Path] = []
        if content_path:
            roots.append(Path(content_path))
        if name:
            roots.append(Path(save_path) / name)

        media_ext = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".ts", ".wmv"}
        matches: list[Path] = []
        for root in roots:
            if root.is_file() and root.suffix.lower() in media_ext:
                if matches_episode_filename(root.name, season, episode):
                    return str(root)
                matches.append(root)
            elif root.is_dir():
                for f in sorted(root.rglob("*")):
                    if f.is_file() and f.suffix.lower() in media_ext:
                        if matches_episode_filename(f.name, season, episode):
                            return str(f)
                        matches.append(f)

        return str(matches[0]) if matches else self._resolve_file_path(torrent)


_client: QBittorrentClient | None = None


def get_qbittorrent_client() -> QBittorrentClient:
    global _client
    if _client is None:
        _client = QBittorrentClient()
    return _client
