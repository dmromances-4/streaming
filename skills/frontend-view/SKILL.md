# SKILL #4 — Frontend View

SPA ligera en Vanilla JS con tema oscuro y reproductor Hls.js.

## Funcionalidades

- **Torrent / VOD:** magnet → ingest (Skill #1) → transcode (Skill #2) → play
- **Deportes en vivo:** URL M3U8 → proxy (Skill #3) → play
- **HLS directo:** reproducir por `job_id`

## Archivos

- `public/index.html` — layout y tabs
- `public/css/style.css` — tema oscuro
- `public/js/app.js` — lógica API + Hls.js

## Despliegue

Servido por Nginx interno (puerto 80). El Nginx edge (`deploy/nginx`) enruta `/` al frontend.
