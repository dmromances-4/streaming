# SKILL #1 — Ingestión Torrent

Servicio de ingesta que recibe un magnet link, descarga piezas en orden secuencial y expone un stream HTTP en tiempo real.

## Responsabilidades

- Aceptar magnet URIs y crear sesiones de descarga
- Descarga secuencial (`set_sequential_download`, `set_piece_deadline`)
- Exponer `GET /stream/{id}` como Readable Stream chunked
- Telemetría Prometheus y logs JSON estructurados
- Limpieza de sesiones al desconectar o `DELETE`

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/ingest` | Crear sesión desde magnet |
| `GET` | `/api/v1/stream/{session_id}` | Stream de video (soporta `Range`) |
| `GET` | `/api/v1/status/{session_id}` | Progreso y metadatos |
| `DELETE` | `/api/v1/sessions/{session_id}` | Liberar sesión |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Métricas Prometheus |

### POST /api/v1/ingest

```json
{ "magnet_uri": "magnet:?xt=urn:btih:..." }
```

Respuesta:

```json
{
  "session_id": "uuid",
  "name": "video.mp4",
  "size_bytes": 123456789,
  "info_hash": "abc..."
}
```

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `TORRENT_CACHE_DIR` | `/tmp/torrent-cache` | Directorio de cache |
| `MAX_CONCURRENT_SESSIONS` | `3` | Límite de sesiones paralelas |
| `MAX_BUFFER_MB` | `64` | Buffer máximo en RAM |
| `PEER_TIMEOUT_SECONDS` | `120` | Timeout sin datos de peers |
| `DOWNLOAD_RATE_LIMIT_KB` | `0` | Límite descarga (0 = ilimitado) |
| `LOG_LEVEL` | `INFO` | Nivel de logging |

## Errores

| error_type | HTTP | Causa |
|------------|------|-------|
| `invalid_magnet` | 400 | URI magnet inválida |
| `session_not_found` | 404 | session_id inexistente |
| `peer_timeout` | 504 | Sin peers/datos en timeout |
| `max_sessions` | 429 | Límite de sesiones alcanzado |
| `storage_exhausted` | 507 | Disco lleno |

## Métricas

- `torrent_sessions_active` — sesiones activas
- `torrent_bytes_streamed_total` — bytes enviados a clientes
- `torrent_ingest_duration_seconds` — latencia hasta primer byte
- `torrent_ingest_errors_total{error_type}` — errores por tipo

## Límites de recursos

| Recurso | Estimación | Mitigación |
|---------|------------|------------|
| CPU | 5–15% | Sin transcode |
| RAM | 64–256 MB/sesión | `MAX_CONCURRENT_SESSIONS` |
| Disco | Tamaño del torrent | Volumen Docker + cleanup |
| Red | Throughput P2P | `DOWNLOAD_RATE_LIMIT_KB` |

## Ejecución local

```bash
cd skills/ingestion-torrent
pip install -e ".[dev]"
PYTHONPATH=src:../../shared/python uvicorn main:app --host 0.0.0.0 --port 8001
```

## Docker

```bash
cd deploy
docker compose up --build
```

Nginx expone: `http://localhost/api/ingest/api/v1/...`
