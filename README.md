# Streaming Platform MVP

Plataforma de streaming modular: películas, series y deportes en vivo.

## Skills implementados

| # | Skill | Puerto | Ruta |
|---|-------|--------|------|
| 1 | Ingestión Torrent | 8001 | `/api/ingest/` |
| 2 | Storage & HLS | 8002 | `/api/hls/` |
| 3 | Live Sports Proxy | 8003 | `/api/live/` |
| 4 | Frontend SPA | 80 (interno) | `/` |
| 5 | Nginx + Compose | 80 | edge |
| 6 | Catalog Metadata | 8004 | `/api/catalog/` |

## Inicio rápido

```bash
cd deploy
docker compose up --build
```

Abre **http://localhost** — interfaz con reproductor Hls.js.

## Verificación completa

```bash
./deploy/scripts/verify.sh
```

## Flujos

### Torrent → HLS (UI)
1. Pestaña **Torrent / VOD** → pegar magnet → Ingestar y transcodificar
2. El frontend orquesta Skill #1 + #2 automáticamente

### Catálogo + Coctelería (UI)
1. Configura **Prowlarr** (`http://localhost:9696`) y **TMDB** (`TMDB_API_KEY` en `.env`)
2. Pestaña **Catálogo** → Importar → Enriquecer TMDB → Resolver magnets → Ingestar
3. Filtra por ingrediente (gin, whisky, vermut…) y reproduce con **Modo Cóctel**
4. **Preview P2P** para magnets locales vía WebTorrent (sin pipeline HLS)

```bash
./deploy/scripts/seed-catalog.sh
./deploy/scripts/ingest-cocteleria.sh
```

### TV en directo europea (UI)
1. Pestaña **Deportes en vivo** → catálogo de ~150 canales o URL M3U8 manual
2. Skill #3 resuelve manifest (RTVE, Brightcove, CCMA, static…) y proxifica con CORS limpio
3. 25 autonómicas españolas activas; algunas emisoras retiradas por falta de HLS upstream (Rioja, IB3, Navarra)

```bash
bash deploy/scripts/verify-spanish-autonomic.sh
bash deploy/scripts/verify-european-channels.sh
```

### VPN para deportes en vivo

```bash
cd deploy
docker compose -f docker-compose.yml -f docker-compose.vpn.yml up
```

Configura `WIREGUARD_*` en `.env`. Ver [deploy/docs/cloudflare-cdn.md](deploy/docs/cloudflare-cdn.md) para CDN.

### API manual

```bash
# Ingest
curl -X POST http://localhost/api/ingest/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"magnet_uri":"magnet:?xt=urn:btih:..."}'

# Transcode
curl -X POST http://localhost/api/hls/api/v1/transcode \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<id>"}'

# Live proxy
curl "http://localhost/api/live/api/v1/proxy?url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('https://example.com/live.m3u8'))")"
```

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [SKILL #1](skills/ingestion-torrent/SKILL.md)
- [SKILL #2](skills/storage-hls/SKILL.md)
- [SKILL #3](skills/live-sports/SKILL.md)
- [SKILL #4](skills/frontend-view/SKILL.md)
- [SKILL #6](skills/catalog-metadata/SKILL.md)
