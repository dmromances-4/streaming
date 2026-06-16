"""Estado del sistema para onboarding de descargas torrent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from config import settings
from qbittorrent_client import get_qbittorrent_client


async def get_system_status() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    messages: list[str] = []

    indexer_configured = bool(settings.effective_indexer_api_key.strip())
    checks["indexer_configured"] = indexer_configured
    if not indexer_configured:
        messages.append(
            "Falta INDEXER_API_KEY en .env. Abre Prowlarr (http://localhost:9696) "
            "→ Settings → General → copia la API key."
        )

    indexer_reachable = False
    if indexer_configured:
        indexer_reachable = await _check_indexer()
    checks["indexer_reachable"] = indexer_reachable
    if indexer_configured and not indexer_reachable:
        messages.append(
            f"No se puede contactar con el indexador en {settings.effective_indexer_url}. "
            "Comprueba que el contenedor prowlarr esté en marcha."
        )

    qbittorrent_ok = await _check_qbittorrent()
    checks["qbittorrent_ok"] = qbittorrent_ok
    if not qbittorrent_ok:
        messages.append(
            "qBittorrent no responde o las credenciales fallan. "
            "Revisa http://localhost:8080 y QBITTORRENT_PASS en .env."
        )

    media_root = Path(settings.media_root)
    media_path_ok = media_root.is_dir()
    checks["media_path_ok"] = media_path_ok
    if not media_path_ok:
        messages.append(
            f"La carpeta de biblioteca {settings.media_root} no existe en el contenedor. "
            "Revisa MEDIA_HOST_PATH en .env."
        )

    acquire_ready = (
        indexer_configured
        and indexer_reachable
        and qbittorrent_ok
        and media_path_ok
    )

    return {
        "acquire_ready": acquire_ready,
        "media_source_mode": settings.media_source_mode,
        "checks": checks,
        "messages": messages,
        "hints": {
            "prowlarr_url": "http://localhost:9696",
            "qbittorrent_url": "http://localhost:8080",
        },
    }


async def _check_indexer() -> bool:
    base = settings.effective_indexer_url.rstrip("/")
    headers = {"X-Api-Key": settings.effective_indexer_api_key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if settings.indexer_provider == "prowlarr" or settings.indexer_api_key:
                resp = await client.get(
                    f"{base}/api/v1/indexer",
                    headers=headers,
                )
                if resp.status_code == 200:
                    indexers = resp.json()
                    enabled = [i for i in indexers if i.get("enable")]
                    return len(enabled) > 0
            resp = await client.get(f"{base}/api/v2.0/indexers", headers=headers)
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


async def _check_qbittorrent() -> bool:
    qbit = get_qbittorrent_client()
    if not qbit._client:
        return False
    try:
        resp = await qbit._request("GET", "/api/v2/app/version")
        return resp.status_code == 200
    except Exception:
        return False
