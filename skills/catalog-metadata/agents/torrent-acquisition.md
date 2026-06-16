# Agente de adquisición torrent on-demand

Contrato determinista (sin LLM) para buscar y descargar episodios que no están en la biblioteca local.

## Entrada

- `series_title` — título de la serie (se normaliza: NFKD, sin acentos)
- `season` / `episode` — números SxxExx
- `year` — opcional, mejora queries Torznab

## Paso 1 — Búsqueda

Variantes de query vía `build_episode_query_variants()` en Prowlarr/Jackett.

## Paso 2 — Filtros estrictos (`is_safe_torrent_title`)

**Excluir:**

- Extensiones: `.exe`, `.scr`, `.bat`, `.zip`, `.rar`, `.lnk`
- Calidades: CAM, CAMRip, TS, TELESYNC, HDCAM, WORKPRINT
- `seeders < TORRENT_MIN_SEEDERS` (default 10)

**Aceptar:** contenedor video o tags de calidad (1080p, WEB-DL, etc.) o patrón SxxExx.

## Paso 3 — Scoring (`_score_episode_item`)

| Criterio | Peso |
|----------|------|
| Match SxxExx + título serie | +200 (+80 si título en nombre) |
| Seeders ≥ mínimo | requisito; bonus `seeders × 10` |
| 1080p / BluRay / WEB-DL | +50 |
| x265/HEVC (si `TORRENT_PREFER_HEVC=true`) o x264 | +20 |
| Tamaño episodio 300MB–1.5GB | +30 |
| CAM/TS | descarte total |

## Paso 4 — Ejecución

1. `qBittorrent.add_magnet()` con tags `catalog,{episode_id}`
2. Mensaje UI: `Descargando [Nombre] - Tamaño: X GB - Seeders: Y`
3. Background: `wait_for_episode_complete` → `scan_series_library` → transcode async

## API

```
POST /api/v1/episodes/{id}/acquire
GET  /api/v1/episodes/{id}/status   # stage: searching | downloading | transcoding | ready
```

## Configuración

```env
MEDIA_SOURCE_MODE=hybrid
QBITTORRENT_DOWNLOAD_PATH=/downloads
MEDIA_HOST_PATH=/Users/you/Downloads
TORRENT_MIN_SEEDERS=10
TORRENT_PREFER_HEVC=false
AUTO_ACQUIRE_ON_PLAY=true
```

Implementación: [`src/torrent_acquisition_agent.py`](../src/torrent_acquisition_agent.py)
