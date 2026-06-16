# SKILL #6 — Catalog Metadata

Catálogo SQLite, TMDB, Torznab (Prowlarr/Jackett), qBittorrent híbrido, biblioteca local y Modo Cóctel.

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/import` | Carga YAML semilla + cócteles |
| `POST` | `/api/v1/enrich-metadata` | Enriquece con TMDB (batch o `title_ids`) |
| `GET` | `/api/v1/catalog` | Lista con filtros (incl. `ingredient`) |
| `GET` | `/api/v1/catalog/local-library` | Series con episodios listos en biblioteca |
| `GET` | `/api/v1/catalog/{id}/cocktails` | Recetas del título |
| `GET` | `/api/v1/cocktails/ingredients` | Ingredientes para filtros |
| `POST` | `/api/v1/resolve-magnets` | Torznab batch |
| `POST` | `/api/v1/batch-ingest` | qBittorrent → libtorrent fallback |
| `POST` | `/api/v1/catalog/{id}/ensure-episodes` | TMDB enrich + sync episodios |
| `POST` | `/api/v1/catalog/{id}/scan-library` | Enlaza archivos locales (`source_path`) |
| `POST` | `/api/v1/catalog/scan-all-library` | Scan de todas las series |
| `GET` | `/api/v1/catalog/{id}/episodes/{s}/{e}/probe` | Debug de resolución de archivo |
| `GET` | `/api/v1/catalog/{id}/seasons` | Resumen por temporada |
| `GET` | `/api/v1/catalog/{id}/episodes?season=N` | Lista episodios (`has_local_media`, `still_url`) |
| `POST` | `/api/v1/catalog/{id}/resolve-episodes` | Torznab SxxExx batch |
| `POST` | `/api/v1/episodes/{id}/play` | Play: biblioteca primero; en `hybrid` auto-acquire si falta archivo |
| `POST` | `/api/v1/episodes/{id}/acquire` | Busca torrent (Prowlarr) → qBittorrent → scan → transcode |
| `GET` | `/api/v1/episodes/{id}/status` | Estado del pipeline (`stage`, `message`; completa transcode si listo) |
| `POST` | `/api/v1/catalog/{id}/play` | Play película en modo biblioteca |

## Modo híbrido (`MEDIA_SOURCE_MODE=hybrid`, default)

1. Intenta biblioteca local (`~/Downloads` montado en `/downloads`)
2. Si no hay archivo → agente torrent on-demand ([`agents/torrent-acquisition.md`](agents/torrent-acquisition.md))
3. qBittorrent descarga en la misma carpeta que escanea la biblioteca
4. Tras descarga: `scan-library` + transcode async → HLS

```env
MEDIA_SOURCE_MODE=hybrid
MEDIA_HOST_PATH=/Users/you/Downloads
QBITTORRENT_DOWNLOAD_PATH=/downloads
TORRENT_MIN_SEEDERS=10
TORRENT_PREFER_HEVC=false
AUTO_ACQUIRE_ON_PLAY=true
```

Frontend: episodios sin `has_local_media` muestran **Buscar y descargar** → poll con etapas `searching` / `downloading` / `transcoding`.

```bash
bash scripts/verify-acquire.sh
```

## Modo biblioteca (`MEDIA_SOURCE_MODE=library`)

1. Montar descargas en Docker: `MEDIA_HOST_PATH` → `/downloads`
2. Aliases en [`catalog/data/media-aliases.yaml`](../../catalog/data/media-aliases.yaml) para carpetas torrent con nombres largos
3. `ensure-episodes` → metadatos TMDB + episodios en BD
4. `scan-library` → enlaza `.mkv`/HLS y pre-transcodifica en background
5. Play devuelve `transcoding` de inmediato; el frontend hace poll en `/status`

Variables clave en `.env`:

```env
MEDIA_SOURCE_MODE=library
MEDIA_HOST_PATH=/Users/you/Downloads
MEDIA_ROOT=/downloads
MEDIA_ALIASES_PATH=/app/catalog/data/media-aliases.yaml
LIBRARY_BOOTSTRAP_SERIES_IDS=series-american-californication,series-american-boardwalk-empire
```

HLS/archivos locales se sirven en nginx bajo `/api/media/`.

## Series VOD (torrent / híbrido)

1. `enrich-metadata` para obtener `tmdb_id`
2. `ensure-episodes` para poblar temporadas/episodios
3. En el frontend: `has_local_media` → **Transcodificar y ver**; sin archivo → **Buscar y descargar**

## Scripts de deploy

```bash
bash scripts/seed-catalog.sh
bash scripts/enrich-full-catalog.sh
bash scripts/sync-all-series-episodes.sh
bash scripts/bootstrap-test-library.sh
bash scripts/verify-catalog.sh
bash scripts/verify-acquire.sh
```

## Setup

1. **Prowlarr** `http://localhost:9696` → indexers → `INDEXER_API_KEY`
2. **TMDB** → `https://www.themoviedb.org/settings/api` → `TMDB_API_KEY`
3. **qBittorrent** `http://localhost:8080` → cambiar password → `QBITTORRENT_PASS`
4. Jackett alternativo: `docker compose --profile jackett up` + `INDEXER_PROVIDER=jackett`

## VPN (live-sports)

```bash
docker compose -f docker-compose.yml -f docker-compose.vpn.yml up
```

Configura `WIREGUARD_*` en `.env`.
