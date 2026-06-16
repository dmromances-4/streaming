"""Tests de health/metrics — requieren libtorrent (Docker / Python 3.12)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_src = Path(__file__).resolve().parents[1] / "src"
_shared = Path(__file__).resolve().parents[3] / "shared" / "python"
for p in (str(_src), str(_shared)):
    if p not in sys.path:
        sys.path.insert(0, p)

libtorrent = pytest.importorskip("libtorrent", reason="libtorrent required — use Docker")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from main import app
    from torrent_engine import get_engine

    engine = get_engine()
    await engine.start()
    transport = ASGITransport(app=app, lifespan="on")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await engine.stop()


@pytest.mark.anyio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["skill"] == "ingestion-torrent"


@pytest.mark.anyio
async def test_metrics(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "torrent_sessions_active" in response.text


@pytest.mark.anyio
async def test_ingest_invalid_magnet(client):
    response = await client.post(
        "/api/v1/ingest",
        json={"magnet_uri": "not-a-magnet"},
    )
    assert response.status_code == 400
    assert response.json()["error_type"] == "invalid_magnet"
