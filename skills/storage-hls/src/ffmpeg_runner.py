"""Ejecutor FFmpeg para segmentación HLS con bajo uso de CPU."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from enum import Enum

from config import settings
from errors import TranscodeError
from skill_telemetry import log


class TranscodeMode(str, Enum):
    COPY = "copy"
    TRANSCODE = "transcode"


@dataclass
class FfmpegResult:
    success: bool
    mode: TranscodeMode
    exit_code: int
    stderr_tail: str


def _build_ffmpeg_args(
    source_url: str,
    output_dir: str,
    job_id: str,
    mode: TranscodeMode,
) -> list[str]:
    manifest = os.path.join(output_dir, "index.m3u8")
    segment_pattern = os.path.join(output_dir, "segment_%03d.ts")

    base = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-threads",
        str(settings.ffmpeg_threads),
        "-i",
        source_url,
    ]

    if mode == TranscodeMode.COPY:
        base.extend([
            "-c",
            "copy",
            "-bsf:v",
            "h264_mp4toannexb",
        ])
    else:
        base.extend([
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
        ])

    base.extend([
        "-f",
        "hls",
        "-hls_time",
        str(settings.hls_segment_duration),
        "-hls_list_size",
        "0",
        "-hls_segment_filename",
        segment_pattern,
        "-start_number",
        "0",
        manifest,
    ])
    return base


async def run_ffmpeg(
    source_url: str,
    output_dir: str,
    job_id: str,
) -> FfmpegResult:
    """Ejecuta FFmpeg; intenta copy primero, fallback a transcode."""
    os.makedirs(output_dir, exist_ok=True)

    for mode in (TranscodeMode.COPY, TranscodeMode.TRANSCODE):
        args = _build_ffmpeg_args(source_url, output_dir, job_id, mode)
        log.info("ffmpeg_start", job_id=job_id, mode=mode.value, source=source_url[:80])

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            _, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=settings.job_timeout_seconds,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise TranscodeError(f"FFmpeg timed out after {settings.job_timeout_seconds}s")

        stderr_text = stderr.decode(errors="replace")[-2000:]
        manifest_path = os.path.join(output_dir, "index.m3u8")

        if proc.returncode == 0 and os.path.isfile(manifest_path):
            log.info("ffmpeg_success", job_id=job_id, mode=mode.value)
            return FfmpegResult(
                success=True,
                mode=mode,
                exit_code=0,
                stderr_tail=stderr_text,
            )

        log.warning(
            "ffmpeg_failed",
            job_id=job_id,
            mode=mode.value,
            exit_code=proc.returncode,
            stderr=stderr_text[-500:],
        )

        if mode == TranscodeMode.COPY:
            # Limpiar artefactos parciales antes del fallback
            for f in os.listdir(output_dir):
                try:
                    os.remove(os.path.join(output_dir, f))
                except OSError:
                    pass
            continue

        return FfmpegResult(
            success=False,
            mode=mode,
            exit_code=proc.returncode or 1,
            stderr_tail=stderr_text,
        )

    raise TranscodeError("FFmpeg failed in both copy and transcode modes")
