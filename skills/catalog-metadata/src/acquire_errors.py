"""Mensajes de error accionables para adquisición torrent."""

from __future__ import annotations


def map_acquire_error(raw: str | None) -> str:
    if not raw:
        return "No se pudo preparar el episodio."

    lower = raw.lower()
    if "indexer" in lower or "no indexer" in lower or "prowlarr" in lower:
        return (
            "No hay indexers configurados. Ve a Ajustes → configura Prowlarr "
            "(http://localhost:9696) y añade INDEXER_API_KEY al .env."
        )
    if "no matching episode torrent" in lower or "no se encontró torrent" in lower:
        return (
            "No se encontró un torrent adecuado para este episodio. "
            "Prueba más tarde o baja TORRENT_MIN_SEEDERS en .env."
        )
    if "qbittorrent" in lower or "rejected magnet" in lower:
        return (
            "qBittorrent no aceptó el magnet. Revisa http://localhost:8080 "
            "y las credenciales QBITTORRENT_PASS."
        )
    if "timeout" in lower or "timed out" in lower:
        return (
            "La descarga tardó demasiado. Comprueba qBittorrent o inténtalo de nuevo."
        )
    if "no local media" in lower:
        return raw
    return raw
