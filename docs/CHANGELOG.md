# Changelog — Streaming Platform MVP

Registro histórico append-only de modificaciones por sesión.

---

## 2026-06-08 — Fase 2 TVs autonómicas: proxy headers, Brightcove, cierre catálogo

### Reporte Técnico — Skill #3 autonómicas ES

**[FASE]:** Cierre fase 2 — proxy por canal, resolvers Brightcove/IB3/Navarra, verify autonómicas

**[MOTIVACIÓN]:** Reproducir TVs autonómicas españolas con headers CDN correctos y resolvers dinámicos; retirar emisoras sin HLS upstream fiable.

**[REGISTRO DE CAMBIOS]:**
- `channel_id` + `proxy_headers` en `/proxy`, `/fetch` y `m3u8_rewriter`
- `brightcove_resolver` (Telemadrid, La Otra, À Punt) con `policy_key` en `video_cloud`
- Resolvers `ib3`, `navarra` y scrape endurecido (`probe_manifest`, JSON)
- `verify-spanish-autonomic.sh`: muestra 10/10, mínimo 25 autonómicas activas
- Catálogo: 150 canales; ES 30 (25 autonómicas)

**[CANALES RETIRADOS]** (`enabled: false` en sync script):
- `es-rioja-tv` — streamlock 404
- `es-ib3`, `es-ib3-2` — API oficial solo YouTube
- `es-navarra-tv` — NATV Play / nice264 sin HLS scrapeable

---

## 2026-06-07 — Extensiones Hacker: TMDB, Prowlarr, Modo Cóctel, CDN, VPN

### Reporte Técnico — Platform Hacker Extensions

**[FASE]:** TMDB enrichment, Torznab/Prowlarr, ingesta híbrida qBittorrent, Modo Cóctel UX, CDN Cloudflare, WireGuard VPN, WebTorrent preview

**[MOTIVACIÓN]:** Automatizar metadatos y descargas sin intervención manual; gamificar Coctelería; reducir egress con CDN; aislar egress IPTV vía VPN.

**[REGISTRO DE CAMBIOS]:**
- `tmdb_client.py`, `metadata_enricher.py`, `POST /enrich-metadata`
- `torznab_client.py` con `INDEXER_PROVIDER` (prowlarr/jackett)
- `qbittorrent_client.py`, ingesta híbrida en orchestrator
- `catalog/data/cocktails/*.yaml`, API cócteles, `cocktail-mode.js`
- `job_store.py` persistencia HLS, segmentos `max-age=86400`
- `deploy/docker-compose.vpn.yml`, gluetun, SSRF redirect fix
- Tab Preview P2P con WebTorrent.js

---

## 2026-06-07 — SKILL #6: Catálogo de Metadatos + Jackett + Ingesta Automatizada

### Reporte Técnico — SKILL #6 Catalog Metadata

**[FASE / PASO ACTUAL]:** SKILL #6 — Catalog Metadata (`skills/catalog-metadata/`), seed YAML, Jackett, orquestación batch

**[MOTIVACIÓN]:** El MVP solo aceptaba magnets manuales. Se necesita catálogo persistente (SQLite), resolución automática vía Jackett Torznab y orquestación batch hacia Skills #1/#2 sin modificar su código.

**[IMPACTO EN EL SISTEMA]:** SQLite ~5–20 MB en volumen Docker. Jackett ~256 MB RAM. Batch ingest suma carga CPU/R2 según límites existentes (~280 GB estimados para 45 títulos Coctelería). Nginx nueva ruta `/api/catalog/`.

**[REGISTRO DE CAMBIOS]:**
- `skills/catalog-metadata/` — SQLite schema, repository, Jackett client, ingest orchestrator, REST API (puerto 8004)
- `catalog/data/seed/*.yaml` — 785 títulos deduplicados (45 Coctelería priority=1)
- `scripts/build_seed_from_catalog.py`, `scripts/catalog_data.py` — generación y dedup de seeds
- `deploy/docker-compose.yml` — servicios `jackett` + `catalog-metadata`
- `deploy/nginx/default.conf` — proxy `/api/catalog/`
- `deploy/scripts/seed-catalog.sh`, `ingest-cocteleria.sh`, `verify-catalog.sh`
- Frontend tab **Catálogo** — filtros, resolve/batch-ingest, reproducción HLS
- Tests unitarios `skills/catalog-metadata/tests/test_shared.py`

---

## 2026-06-07 — Fases 3–5: Live Sports + Frontend + DevOps

### Reporte Técnico — SKILL #3, #4, #5

**[FASE / PASO ACTUAL]:** Skills #3 (Live Sports), #4 (Frontend SPA), #5 (Orquestación Nginx/Compose)

**[MOTIVACIÓN]:** Skill #3 resuelve CORS en IPTV/M3U8 reescribiendo playlists. Skill #4 unifica UX en SPA Vanilla sin framework. Skill #5 centraliza routing en Nginx para aislamiento de microservicios.

**[IMPACTO EN EL SISTEMA]:** Skill #3: CPU/RAM bajos (proxy relay). Skill #4: estático, impacto mínimo. Nginx: ~64 MB RAM, terminación y proxy de 4 backends.

**[REGISTRO DE CAMBIOS]:**
- `skills/live-sports/` — proxy M3U8, SSRF guard, CORS
- `skills/frontend-view/` — HTML/CSS/JS + Hls.js
- `deploy/docker-compose.yml` — 6 servicios + nginx edge
- `deploy/nginx/default.conf` — rutas completas MVP
- Scripts verify-live.sh, verify-frontend.sh

---

## 2026-06-07 — Fase 2: SKILL #2 Storage & HLS

### Reporte Técnico — SKILL #2 Storage & HLS

**[FASE / PASO ACTUAL]:** SKILL #2 — Storage & HLS (`skills/storage-hls`)

**[MOTIVACIÓN]:** FFmpeg segmenta el stream de Skill #1 en HLS (.m3u8 + .ts) con `-codec copy` cuando es posible para minimizar CPU. boto3 sube segmentos a MinIO/R2 (API S3 idéntica, egress $0 en R2). Jobs asíncronos desacoplan transcode de la petición HTTP.

**[IMPACTO EN EL SISTEMA]:** CPU moderada-alta durante transcode (mitigado con copy + `-threads 2`). RAM ~512 MB/job. Disco temporal en `/tmp/hls-jobs`. Ancho de banda: lectura desde Skill #1 + upload S3. MinIO añade ~128 MB RAM en dev.

**[REGISTRO DE CAMBIOS]:**
- Nuevo `skills/storage-hls/` con FFmpeg runner, S3 uploader, job manager
- MinIO en docker-compose como stub S3
- Nginx route `/api/hls/`
- Errores Skill #2 en `shared/python/errors.py`

---

## 2026-06-07 — Fase 1: Arquitectura Global + SKILL #1

### Reporte Técnico — Inicialización

**[FASE / PASO ACTUAL]:** Documentación arquitectónica global (`docs/ARCHITECTURE.md`) y estructura base del repositorio.

**[MOTIVACIÓN]:** Establecer contratos API inter-Skills, protocolo de trazabilidad y layout modular antes de escribir código. Evita acoplamiento monolítico y facilita despliegue independiente por Skill.

**[IMPACTO EN EL SISTEMA]:** Sin impacto en runtime (solo documentación). Define límites de recursos por Skill para planificación de VPS.

**[REGISTRO DE CAMBIOS]:**
- Creado `docs/ARCHITECTURE.md` con diagramas y contratos API
- Creado `docs/CHANGELOG.md` (este archivo)
- Definida estructura `skills/`, `shared/`, `deploy/`

---

### Reporte Técnico — SKILL #1 Ingestión Torrent

**[FASE / PASO ACTUAL]:** SKILL #1 — Servicio de Ingestión Torrent (`skills/ingestion-torrent`)

**[MOTIVACIÓN]:** Python + libtorrent ofrece `sequential_download` nativo y alertas de piezas para exponer un Readable Stream HTTP sin esperar descarga completa. FastAPI permite `StreamingResponse` con backpressure.

**[IMPACTO EN EL SISTEMA]:** CPU baja (solo I/O P2P + hash). RAM acotada por buffer y límite de sesiones. Ancho de banda = throughput P2P entrante + reenvío al cliente/SKILL #2. Disco temporal proporcional al contenido activo.

**[REGISTRO DE CAMBIOS]:**
- Inicialización repo, docs arquitectura, implementación Skill #1
- `shared/python/` — telemetría y errores compartidos
- `deploy/docker-compose.yml` + nginx route `/api/ingest/`
- `deploy/scripts/verify.sh` — script de verificación post-deploy
- Tests unitarios `test_shared.py` (sin libtorrent)
- Tests integración `test_health.py` (requieren Docker/Python 3.12 + libtorrent)

### Verificación — Fase 1

- `test_shared.py`: 4 tests passed
- Docker no disponible en entorno dev local — verificación E2E vía `docker compose up`
