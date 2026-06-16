# SKILL #2 — Storage & HLS

Segmenta video en HLS con FFmpeg y almacena segmentos en S3 (MinIO dev / Cloudflare R2 prod).

## Responsabilidades

- Consumir stream HTTP de Skill #1 (`source_url` o `session_id`)
- Segmentar con FFmpeg (`-codec copy` primero, fallback `ultrafast`)
- Subir `.m3u8` y `.ts` a S3
- Servir manifest y segmentos vía API (proxy S3, CORS limpio)

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/transcode` | Iniciar job HLS |
| `GET` | `/api/v1/status/{job_id}` | Estado del job |
| `GET` | `/api/v1/manifest/{job_id}` | Playlist M3U8 reescrita |
| `GET` | `/api/v1/segments/{job_id}/{file}` | Segmento .ts desde S3 |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus |

### POST /api/v1/transcode

```json
{ "session_id": "uuid-from-skill1" }
```

o

```json
{ "source_url": "http://ingestion-torrent:8001/api/v1/stream/uuid" }
```

Respuesta:

```json
{
  "job_id": "uuid",
  "state": "pending",
  "manifest_url": "http://localhost/api/hls/api/v1/manifest/uuid"
}
```

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `S3_ENDPOINT` | `http://minio:9000` | MinIO o R2 endpoint |
| `S3_BUCKET` | `streaming-hls` | Bucket HLS |
| `AWS_ACCESS_KEY_ID` | `minioadmin` | Credencial S3 |
| `AWS_SECRET_ACCESS_KEY` | `minioadmin` | Credencial S3 |
| `INGESTION_BASE_URL` | `http://ingestion-torrent:8001` | Skill #1 interno |
| `PUBLIC_API_BASE` | `http://localhost/api/hls` | Base URL manifest pública |
| `FFMPEG_THREADS` | `2` | Límite CPU FFmpeg |
| `MAX_CONCURRENT_JOBS` | `2` | Jobs paralelos |
| `HLS_SEGMENT_DURATION` | `6` | Segundos por segmento |

## Migración a Cloudflare R2

```bash
S3_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
S3_BUCKET=streaming-hls
AWS_ACCESS_KEY_ID=<r2_access_key>
AWS_SECRET_ACCESS_KEY=<r2_secret_key>
```

## Métricas

- `hls_jobs_active`
- `hls_segments_uploaded_total`
- `hls_transcode_duration_seconds`
- `hls_errors_total{error_type}` (vía MetricsRegistry)

## Límites de recursos

| Recurso | Estimación | Mitigación |
|---------|------------|------------|
| CPU | 30–80% durante transcode | `-codec copy`, `-threads 2` |
| RAM | 512 MB–1 GB/job | `MAX_CONCURRENT_JOBS=2` |
| Disco | Temporal en `/tmp/hls-jobs` | Cleanup post-upload |
| Red | Ingest stream + S3 upload | Segmentos de 6s |
