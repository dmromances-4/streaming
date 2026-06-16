"""Tests unitarios Skill #2 (sin FFmpeg/S3)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_src = Path(__file__).resolve().parents[1] / "src"
_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
for p in (str(_src), str(_shared)):
    if p not in sys.path:
        sys.path.insert(0, p)


def test_job_not_found_error():
    from errors import JobNotFoundError

    exc = JobNotFoundError("missing job")
    assert exc.http_status == 404
    assert exc.error_type == "job_not_found"


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="Pydantic schemas use Python 3.10+ union syntax; run in Docker",
)
def test_transcode_request_requires_source():
    from pydantic import ValidationError

    from api.schemas import TranscodeRequest

    with pytest.raises(ValidationError):
        TranscodeRequest()


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="Pydantic schemas use Python 3.10+ union syntax; run in Docker",
)
def test_transcode_request_session_id():
    from api.schemas import TranscodeRequest

    req = TranscodeRequest(session_id="abc-123")
    assert req.session_id == "abc-123"
    assert req.source_url is None


def test_manifest_rewrite():
    from manifest_utils import rewrite_manifest

    raw = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXTINF:6.0,
segment_000.ts
#EXTINF:6.0,
segment_001.ts
#EXT-X-ENDLIST
"""
    result = rewrite_manifest(raw, "job-123", "/api/hls")
    assert "/api/hls/api/v1/segments/job-123/segment_000.ts" in result
    assert "/api/hls/api/v1/segments/job-123/segment_001.ts" in result
    assert "#EXTM3U" in result


def test_ffmpeg_args_copy_mode():
    from ffmpeg_runner import TranscodeMode, _build_ffmpeg_args

    args = _build_ffmpeg_args(
        "http://example.com/stream",
        "/tmp/out",
        "job-1",
        TranscodeMode.COPY,
    )
    assert "ffmpeg" in args
    assert "-c" in args
    assert "copy" in args
    assert "-f" in args
    assert "hls" in args


def test_segment_filename_validation():
    from manifest_utils import validate_segment_filename

    assert validate_segment_filename("segment_000.ts")
    assert validate_segment_filename("segment_123.ts")
    assert not validate_segment_filename("../etc/passwd")
    assert not validate_segment_filename("index.m3u8")
