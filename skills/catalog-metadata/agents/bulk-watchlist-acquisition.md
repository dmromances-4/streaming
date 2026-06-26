# Agente bulk de adquisición de watchlist (modo sin cuentas)

Orquesta la descarga masiva de películas usando solo recursos locales y APIs públicas.

## Sin registrarse en nada

- **TMDB**: opcional. Si `TMDB_API_KEY` está vacío, se omite el enriquecimiento y se busca por título + `search_queries`.
- **Prowlarr**: la API key se lee del `config.xml` local del contenedor (volumen Docker). No hace falta copiarla a mano.
- **Indexers en Prowlarr**: opcionales. Si no hay ninguno, el sistema usa **YTS** (API pública, sin clave) como respaldo para películas.

## Entrada

- Watchlist en [`catalog/data/seed/`](../../catalog/data/seed/)
- Alias en [`catalog/data/torrent-search-aliases.yaml`](../../catalog/data/torrent-search-aliases.yaml)

## Fase 1 — Películas

1. `POST /api/v1/import`
2. Enriquecimiento TMDB solo si hay clave (si no, se salta)
3. Por cada película sin archivo local: `acquire_movie()`
   - Prowlarr/Torznab (si hay indexers)
   - Si falla → **YTS** (público)
4. qBittorrent descarga en `MEDIA_HOST_PATH` (E: → D: → C:)

## Ruta de descargas

```powershell
powershell -File deploy/scripts/resolve-media-path.ps1 -UpdateEnv
```

Prioridad: `E:\Media` → `D:\Media` → carpeta `media` del proyecto.

## Arranque rápido

```powershell
cd deploy
powershell -File scripts/setup-keyless.ps1 -UpdateEnv
docker compose --env-file .env up --build -d
bash scripts/bulk-download-movies.sh
```

## Limitaciones sin claves

| Qué | Cobertura |
|-----|-----------|
| Películas USA/Europa populares | Buena (YTS + alias) |
| Cine español/catalán | Parcial (alias `search_queries`) |
| Series | Fase 2; episodios necesitan más fuentes |
| Metadatos (pósters, año TMDB) | Solo con clave TMDB |

## API

```
POST /api/v1/bulk-acquire
GET  /api/v1/bulk-acquire/status
```

Implementación: [`src/bulk_watchlist_agent.py`](../src/bulk_watchlist_agent.py), [`src/yts_client.py`](../src/yts_client.py)
