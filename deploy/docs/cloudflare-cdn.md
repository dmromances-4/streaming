# Cloudflare CDN para HLS

## Objetivo

Servir segmentos `.ts` desde la red de Cloudflare para reducir egress del servidor de origen.

## Paso 1 — Proxy cache (sin cambiar URLs)

1. Apunta tu dominio a Cloudflare (proxy naranja activo).
2. En **Cache Rules**, crea:

| Campo | Valor |
|-------|-------|
| URI Path | `/api/hls/api/v1/segments/*` |
| Cache eligibility | Eligible |
| Edge TTL | 1 day (o respect origin) |

3. Bypass cache para manifests:

| URI Path | `/api/hls/api/v1/manifest/*` |
| Cache | Bypass |

4. Variables de producción en `.env`:

```bash
PUBLIC_API_BASE=https://stream.tudominio.com/api/hls
PUBLIC_HLS_BASE=https://stream.tudominio.com/api/hls
S3_PUBLIC_BASE_URL=https://cdn.tudominio.com
```

## Paso 2 — R2 directo (opcional)

Con `S3_PUBLIC_BASE_URL` configurado, los manifests reescriben segmentos a URLs CDN directas (`jobs/{job_id}/segment_XXX.ts`).

Configura dominio custom en R2 + Cloudflare.

## Headers de origen

Skill #2 ya emite:

- Manifest: `Cache-Control: no-cache`
- Segmentos: `Cache-Control: public, max-age=86400, immutable`

## Persistencia de jobs

Los jobs HLS se guardan en SQLite (`/data/hls-jobs.db`) para sobrevivir reinicios del contenedor `storage-hls`.
