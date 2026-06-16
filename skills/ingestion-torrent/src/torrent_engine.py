"""Motor libtorrent con descarga secuencial y gestión de sesiones."""

from __future__ import annotations

import asyncio
import mimetypes
import os
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

import libtorrent as lt

import sys
from pathlib import Path

_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from episode_utils import matches_episode_filename  # noqa: E402

from config import settings
from errors import (
    InvalidMagnetError,
    MaxSessionsError,
    PeerTimeoutError,
    SessionNotFoundError,
    StorageExhaustedError,
)
from skill_telemetry import (
    bytes_streamed_total,
    ingest_duration_seconds,
    log,
    sessions_active,
)


@dataclass
class TorrentSession:
    """Estado de una sesión de ingesta activa."""

    session_id: str
    magnet_uri: str
    handle: lt.torrent_handle
    save_path: str
    file_index: int = 0
    season_number: int | None = None
    episode_number: int | None = None
    stream_offset: int = 0
    bytes_streamed: int = 0
    created_at: float = field(default_factory=time.time)
    last_touch: float = field(default_factory=time.time)
    metadata_ready: asyncio.Event = field(default_factory=asyncio.Event)
    _lock: Lock = field(default_factory=Lock)

    def touch(self) -> None:
        self.last_touch = time.time()

    def record_bytes_streamed(self, n: int) -> None:
        self.bytes_streamed += n
        bytes_streamed_total.inc(n)

    def set_stream_position(self, file_index: int, offset: int) -> None:
        self.file_index = file_index
        self.stream_offset = offset
        self._prioritize_from_offset(file_index, offset)

    def _prioritize_from_offset(self, file_index: int, offset: int) -> None:
        if not self.handle.is_valid() or not self.handle.has_metadata():
            return

        ti = self.handle.torrent_file()
        if file_index >= ti.num_files():
            return

        piece_size = ti.piece_length()
        file_offset_in_torrent = ti.file_offset(file_index)
        absolute_offset = file_offset_in_torrent + offset
        first_piece = ti.map_file(file_index, offset, 0).piece

        # Priorizar piezas desde la posición de lectura
        for piece in range(first_piece, ti.num_pieces()):
            deadline = (piece - first_piece) * 10  # ms escalonado
            self.handle.set_piece_deadline(piece, deadline)

        self.handle.set_sequential_download(True)

    def get_file_size(self, file_index: int) -> int:
        if not self.handle.has_metadata():
            return 0
        ti = self.handle.torrent_file()
        if file_index >= ti.num_files():
            return 0
        return ti.file_size(file_index)

    def get_file_name(self, file_index: int) -> str:
        if not self.handle.has_metadata():
            return "unknown"
        ti = self.handle.torrent_file()
        return ti.files().file_name(file_index)

    def get_mime_type(self, file_index: int) -> str:
        name = self.get_file_name(file_index)
        mime, _ = mimetypes.guess_type(name)
        return mime or "application/octet-stream"

    def get_status(self) -> dict[str, Any]:
        if not self.handle.is_valid():
            return {"state": "invalid", "progress": 0.0, "download_rate_bps": 0}

        s = self.handle.status()
        state_map = {
            lt.torrent_status.queued_for_checking: "queued",
            lt.torrent_status.checking_files: "checking",
            lt.torrent_status.downloading_metadata: "metadata",
            lt.torrent_status.downloading: "downloading",
            lt.torrent_status.finished: "finished",
            lt.torrent_status.seeding: "seeding",
        }
        return {
            "state": state_map.get(s.state, "unknown"),
            "progress": round(s.progress, 4),
            "download_rate_bps": s.download_rate,
            "upload_rate_bps": s.upload_rate,
            "num_peers": s.num_peers,
            "total_done": s.total_done,
            "total_wanted": s.total_wanted,
        }

    async def wait_for_bytes(
        self,
        file_index: int,
        offset: int,
        length: int,
        timeout: float = 120.0,
    ) -> int:
        """Espera hasta que `length` bytes desde `offset` estén disponibles."""
        if not self.handle.has_metadata():
            try:
                await asyncio.wait_for(
                    self._wait_metadata(), timeout=timeout
                )
            except asyncio.TimeoutError as exc:
                raise PeerTimeoutError("Metadata download timed out") from exc

        ti = self.handle.torrent_file()
        file_size = ti.file_size(file_index)
        if offset >= file_size:
            return 0

        want = min(length, file_size - offset)
        self._prioritize_from_offset(file_index, offset)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            available = self._bytes_available(file_index, offset, want)
            if available > 0:
                return available

            status = self.get_status()
            if status["state"] in ("seeding", "finished"):
                # Todo descargado
                return min(want, file_size - offset)

            await asyncio.sleep(0.05)

        raise PeerTimeoutError(
            f"Timeout waiting for {want} bytes at offset {offset}"
        )

    async def _wait_metadata(self) -> None:
        await self.metadata_ready.wait()

    def _bytes_available(self, file_index: int, offset: int, length: int) -> int:
        if not self.handle.has_metadata():
            return 0

        ti = self.handle.torrent_file()
        file_size = ti.file_size(file_index)
        if offset >= file_size:
            return 0

        want = min(length, file_size - offset)
        file_offset = ti.file_offset(file_index)
        start_piece = ti.map_file(file_index, offset, 1).piece
        end_offset = offset + want - 1
        end_piece = ti.map_file(file_index, end_offset, 1).piece

        piece_size = ti.piece_length()
        available = 0
        checked_offset = offset

        for piece in range(start_piece, end_piece + 1):
            if not self.handle.have_piece(piece):
                break

            # Calcular bytes de esta pieza dentro del rango del archivo
            piece_start = piece * piece_size
            piece_end = piece_start + piece_size

            file_piece_start = max(checked_offset, piece_start - file_offset)
            file_piece_end = min(offset + want, piece_end - file_offset)

            if file_piece_end > file_piece_start:
                available += file_piece_end - file_piece_start
                checked_offset = file_piece_end
            else:
                break

        return min(available, want)

    async def read_file_bytes(
        self, file_index: int, offset: int, length: int
    ) -> bytes:
        """Lee bytes del archivo usando el storage de libtorrent."""
        if not self.handle.has_metadata():
            return b""

        ti = self.handle.torrent_file()
        file_size = ti.file_size(file_index)
        if offset >= file_size:
            return b""

        to_read = min(length, file_size - offset)
        file_offset_in_torrent = ti.file_offset(file_index)
        absolute_offset = file_offset_in_torrent + offset

        # Leer vía archivo en disco (parcialmente descargado)
        storage_path = os.path.join(
            self.save_path,
            self.handle.name(),
            ti.files().file_path(file_index),
        )

        if os.path.isfile(storage_path):
            try:
                with open(storage_path, "rb") as f:
                    f.seek(offset)
                    return f.read(to_read)
            except OSError:
                pass

        # Fallback: leer pieza por pieza con read_piece
        return await self._read_via_pieces(
            ti, file_index, offset, to_read, absolute_offset
        )

    async def _read_via_pieces(
        self,
        ti: lt.torrent_info,
        file_index: int,
        offset: int,
        length: int,
        absolute_offset: int,
    ) -> bytes:
        result = bytearray()
        remaining = length
        pos = offset

        while remaining > 0:
            map_entry = ti.map_file(file_index, pos, 1)
            piece = map_entry.piece
            piece_offset = map_entry.start

            if not self.handle.have_piece(piece):
                break

            piece_size = ti.piece_length()
            to_copy = min(remaining, piece_size - piece_offset)

            # read_piece es async en libtorrent 2.x via alert
            data = self._read_piece_sync(piece)
            if data is None:
                break

            chunk = data[piece_offset : piece_offset + to_copy]
            result.extend(chunk)
            remaining -= len(chunk)
            pos += len(chunk)

        return bytes(result)

    def _read_piece_sync(self, piece: int) -> bytes | None:
        with self._lock:
            try:
                self.handle.read_piece(piece)
            except Exception:
                return None
        # El resultado llega por alert; para MVP usamos archivo en disco
        # como vía principal. Este fallback retorna None si no hay archivo.
        return None


class TorrentEngine:
    """Gestor singleton de sesiones libtorrent."""

    def __init__(self) -> None:
        self._sessions: dict[str, TorrentSession] = {}
        self._lock = asyncio.Lock()
        self._lt_session = lt.session()
        self._lt_session.listen_on(6881, 6891)
        self._configure_session()
        self._alert_task: asyncio.Task[None] | None = None
        self._running = False

        os.makedirs(settings.torrent_cache_dir, exist_ok=True)

    def _configure_session(self) -> None:
        settings_pack = {
            "enable_dht": True,
            "enable_lsd": True,
            "enable_upnp": True,
            "enable_natpmp": True,
            "allow_multiple_connections_per_ip": True,
        }
        if settings.download_rate_limit_kb > 0:
            settings_pack["download_rate_limit"] = (
                settings.download_rate_limit_kb * 1024
            )
        self._lt_session.apply_settings(settings_pack)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._alert_task = asyncio.create_task(self._process_alerts())
        log.info("torrent_engine_started")

    async def stop(self) -> None:
        self._running = False
        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass
        async with self._lock:
            for sid in list(self._sessions.keys()):
                await self._remove_session(sid)
        log.info("torrent_engine_stopped")

    async def _process_alerts(self) -> None:
        while self._running:
            alerts = self._lt_session.pop_alerts()
            for alert in alerts:
                await self._handle_alert(alert)
            await asyncio.sleep(0.1)

    async def _handle_alert(self, alert: lt.alert) -> None:
        if isinstance(alert, lt.metadata_received_alert):
            handle = alert.handle
            for session in self._sessions.values():
                if session.handle == handle:
                    session.metadata_ready.set()
                    session.handle.set_sequential_download(True)
                    session._prioritize_from_offset(0, 0)
                    log.info(
                        "metadata_received",
                        session_id=session.session_id,
                        name=handle.name(),
                    )

        elif isinstance(alert, lt.torrent_error_alert):
            log.error("torrent_error", error=str(alert.error))

    async def create_session(
        self,
        magnet_uri: str,
        *,
        season_number: int | None = None,
        episode_number: int | None = None,
    ) -> TorrentSession:
        if not magnet_uri.startswith("magnet:?"):
            raise InvalidMagnetError("URI must start with magnet:?")

        async with self._lock:
            if len(self._sessions) >= settings.max_concurrent_sessions:
                raise MaxSessionsError(
                    f"Maximum {settings.max_concurrent_sessions} concurrent sessions"
                )

            session_id = str(uuid.uuid4())
            save_path = os.path.join(
                settings.torrent_cache_dir, session_id
            )
            os.makedirs(save_path, exist_ok=True)

            try:
                params = lt.parse_magnet_uri(magnet_uri)
                params.save_path = save_path
                handle = self._lt_session.add_torrent(params)
                handle.set_sequential_download(True)
            except Exception as exc:
                raise InvalidMagnetError(str(exc)) from exc

            torrent_session = TorrentSession(
                session_id=session_id,
                magnet_uri=magnet_uri,
                handle=handle,
                save_path=save_path,
                season_number=season_number,
                episode_number=episode_number,
            )
            self._sessions[session_id] = torrent_session
            sessions_active.set(len(self._sessions))

            log.info(
                "session_created",
                session_id=session_id,
                info_hash=str(handle.info_hash()),
            )
            return torrent_session

    async def get_session(self, session_id: str) -> TorrentSession:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        return session

    async def get_status(self, session_id: str) -> dict[str, Any]:
        session = await self.get_session(session_id)
        status = session.get_status()
        status["session_id"] = session_id
        status["name"] = (
            session.handle.name()
            if session.handle.has_metadata()
            else "pending_metadata"
        )
        status["bytes_streamed"] = session.bytes_streamed
        if session.handle.has_metadata():
            ti = session.handle.torrent_file()
            status["size_bytes"] = sum(
                ti.file_size(i) for i in range(ti.num_files())
            )
            status["files"] = [
                {
                    "index": i,
                    "name": ti.files().file_name(i),
                    "size": ti.file_size(i),
                }
                for i in range(ti.num_files())
            ]
        else:
            status["size_bytes"] = 0
            status["files"] = []
        return status

    async def remove_session(self, session_id: str) -> None:
        async with self._lock:
            await self._remove_session(session_id)

    async def _remove_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if not session:
            return

        if session.handle.is_valid():
            self._lt_session.remove_torrent(session.handle)

        sessions_active.set(len(self._sessions))
        log.info("session_removed", session_id=session_id)

    def pick_largest_video_file(self, session: TorrentSession) -> int:
        """Selecciona el archivo de video más grande del torrent."""
        if not session.handle.has_metadata():
            return 0

        ti = session.handle.torrent_file()
        video_ext = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".m4v"}
        best_index = 0
        best_size = 0

        for i in range(ti.num_files()):
            name = ti.files().file_name(i).lower()
            ext = os.path.splitext(name)[1]
            size = ti.file_size(i)
            if ext in video_ext and size > best_size:
                best_size = size
                best_index = i
            elif best_size == 0 and size > best_size:
                best_size = size
                best_index = i

        return best_index

    def pick_episode_file(
        self, session: TorrentSession, season: int, episode: int
    ) -> int:
        """Selecciona el archivo que coincide con SxxExx en el torrent."""
        if not session.handle.has_metadata():
            return 0

        ti = session.handle.torrent_file()
        video_ext = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".m4v"}
        match_index: int | None = None
        best_size = 0
        fallback = 0

        for i in range(ti.num_files()):
            name = ti.files().file_name(i)
            ext = os.path.splitext(name.lower())[1]
            size = ti.file_size(i)
            if ext not in video_ext:
                continue
            if size > best_size:
                best_size = size
                fallback = i
            if matches_episode_filename(name, season, episode):
                match_index = i
                break

        if match_index is not None:
            return match_index
        return fallback

    def pick_file_for_session(
        self,
        session: TorrentSession,
        *,
        season: int | None = None,
        episode: int | None = None,
    ) -> int:
        s = season if season is not None else session.season_number
        e = episode if episode is not None else session.episode_number
        if s is not None and e is not None:
            return self.pick_episode_file(session, s, e)
        return self.pick_largest_video_file(session)


# Singleton global
_engine: TorrentEngine | None = None


def get_engine() -> TorrentEngine:
    global _engine
    if _engine is None:
        _engine = TorrentEngine()
    return _engine
