# SKILL #3 — Live Sports Proxy

Proxy HTTP para flujos IPTV/M3U8 externos con CORS limpio, catálogo europeo y resolvers dinámicos.

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/proxy?url=` | Proxy playlist M3U8 (reescribe URIs) |
| `GET` | `/api/v1/fetch?url=` | Proxy segmentos .ts y sub-playlists |
| `GET` | `/api/v1/channels` | Lista canales (`country`, `tag`, `group`) |
| `GET` | `/api/v1/channels/{id}/stream` | Resuelve manifest + `proxied_url` |
| `GET` | `/api/v1/channels/health` | Estado de resolución por canal |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus |

### Parámetros proxy

| Parámetro | Uso |
|-----------|-----|
| `url` | URL upstream codificada (obligatorio) |
| `channel_id` | ID de canal del catálogo; aplica `proxy_headers` del YAML |

## Catálogo

- Fuente: `catalog/data/live-channels/*.yaml` (generado por `deploy/scripts/sync-european-channels.py`)
- ~150 canales europeos; España: 30 activos (25 autonómicas)
- Campos relevantes: `resolver`, `stream_url`, `proxy_headers`, `geo_country`, `tags`

Regenerar tras editar el script:

```bash
python3 deploy/scripts/sync-european-channels.py --write
```

Canales sin HLS upstream verificado se marcan `enabled: false` en el script (no se escriben al YAML).

### Canales autonómicos retirados (fase 2)

| ID | Motivo |
|----|--------|
| `es-rioja-tv` | URL streamlock caducada (404) |
| `es-ib3`, `es-ib3-2` | API oficial solo YouTube embed |
| `es-navarra-tv` | NATV Play (Clappr/JS); CDN nice264 inaccesible |

## Resolvers

| Resolver | Uso |
|----------|-----|
| `static` | `stream_url` fija en catálogo |
| `rtve` | RTVE dinámico por `slug` |
| `brightcove` | Playback API (`brightcove_account`, `brightcove_ref`, `brightcove_player`) |
| `ccma` | TV3 / 3Cat por `ccma_id` |
| `tvg`, `cyltv`, `murcia`, `tpa`, `trc`, `clm` | Scrape/API emisora |
| `ib3`, `navarra` | Código presente; canales deshabilitados en catálogo |

## Variables

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PUBLIC_API_BASE` | `http://localhost/api/live` | Base para URIs reescritas |
| `PROXY_TIMEOUT_SECONDS` | `30` | Timeout upstream |
| `BLOCK_PRIVATE_IPS` | `true` | Protección SSRF básica |

## Verificación

```bash
bash deploy/scripts/verify-spanish-autonomic.sh   # 10/10 autonómicas muestra
bash deploy/scripts/verify-european-channels.sh   # catálogo completo
```

## Uso con Hls.js

```javascript
const src = '/api/live/api/v1/proxy?url=' + encodeURIComponent('https://example.com/live.m3u8');
hls.loadSource(src);
```

Con catálogo:

```javascript
const r = await fetch('/api/live/api/v1/channels/es-telemadrid/stream');
const { proxied_url } = await r.json();
hls.loadSource(proxied_url.startsWith('http') ? proxied_url : proxied_url);
```
