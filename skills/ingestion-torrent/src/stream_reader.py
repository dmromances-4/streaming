"""Readable stream secuencial sobre un archivo de torrent en descarga."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.torrent_engine import TorrentSession


class SequentialStreamReader:
    """
    Lee bytes de un archivo dentro de un torrent en orden secuencial,
    esperando a que libtorrent complete las piezas necesarias.
    """

    def __init__(
        self,
        session: TorrentSession,
        file_index: int = 0,
        *,
        chunk_size: int = 256 * 1024,
        peer_timeout_seconds: int = 120,
    ) -> None:
        self._session = session
        self._file_index = file_index
        self._chunk_size = chunk_size
        self._peer_timeout = peer_timeout_seconds
        self._offset = 0
        self._closed = False

    @property
    def file_size(self) -> int:
        return self._session.get_file_size(self._file_index)

    @property
    def mime_type(self) -> str:
        return self._session.get_mime_type(self._file_index)

    @property
    def file_name(self) -> str:
        return self._session.get_file_name(self._file_index)

    def seek(self, offset: int) -> None:
        if offset < 0 or offset > self.file_size:
            raise ValueError(f"Offset {offset} out of range [0, {self.file_size}]")
        self._offset = offset
        self._session.set_stream_position(self._file_index, offset)

    async def read_chunks(
        self,
        start: int | None = None,
        end: int | None = None,
    ) -> AsyncIterator[bytes]:
        """Genera chunks de bytes desde start hasta end (inclusive end-1)."""
        if self._closed:
            return

        file_size = self.file_size
        if file_size == 0:
            return

        pos = self._offset if start is None else start
        if pos < 0:
            pos = 0
        stop = file_size if end is None else min(end + 1, file_size)

        last_progress_time = time.monotonic()

        while pos < stop and not self._closed:
            # Esperar hasta que los bytes en [pos, pos+chunk) estén disponibles
            available = await self._session.wait_for_bytes(
                self._file_index,
                pos,
                min(self._chunk_size, stop - pos),
                timeout=self._peer_timeout,
            )

            if available == 0:
                status = self._session.get_status()
                if status.get("state") in ("seeding", "finished"):
                    break
                if time.monotonic() - last_progress_time > self._peer_timeout:
                    from errors import PeerTimeoutError

                    raise PeerTimeoutError(
                        f"No data received for {self._peer_timeout}s at offset {pos}"
                    )
                await asyncio.sleep(0.25)
                continue

            last_progress_time = time.monotonic()
            data = await self._session.read_file_bytes(
                self._file_index, pos, available
            )
            if not data:
                await asyncio.sleep(0.1)
                continue

            yield data
            pos += len(data)
            self._offset = pos
            self._session.record_bytes_streamed(len(data))

        self._session.touch()

    async def read_range(self, start: int, end: int) -> bytes:
        """Lee un rango completo en memoria (para rangos pequeños)."""
        parts: list[bytes] = []
        self.seek(start)
        async for chunk in self.read_chunks(start=start, end=end):
            parts.append(chunk)
        return b"".join(parts)

    def close(self) -> None:
        self._closed = True

    async def __aenter__(self) -> SequentialStreamReader:
        return self

    async def __aexit__(self, *args: object) -> None:
        self.close()


def parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int] | None:
    """Parsea 'bytes=start-end' y devuelve (start, end) inclusive."""
    if not range_header or not range_header.startswith("bytes="):
        return None

    spec = range_header[6:].strip()
    if "," in spec:
        # Múltiples rangos no soportados; tomar el primero
        spec = spec.split(",", 1)[0].strip()

    if spec.startswith("-"):
        # Suffix range: últimos N bytes
        try:
            suffix = int(spec[1:])
        except ValueError:
            return None
        start = max(0, file_size - suffix)
        return start, file_size - 1

    if "-" not in spec:
        return None

    start_s, end_s = spec.split("-", 1)
    try:
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
    except ValueError:
        return None

    start = max(0, min(start, file_size - 1))
    end = max(start, min(end, file_size - 1))
    return start, end


def safe_file_path(base_dir: str, relative_path: str) -> str:
    """Resuelve ruta de archivo evitando path traversal."""
    base = os.path.realpath(base_dir)
    full = os.path.realpath(os.path.join(base, relative_path))
    if not full.startswith(base + os.sep) and full != base:
        raise ValueError("Invalid file path")
    return full
