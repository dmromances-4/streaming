# Modo sin cuentas externas — descargas solo en D:\Media

No necesitas TMDB, ni registrarse en indexers, ni copiar API keys a mano.

## Arranque (solo disco D:)

```powershell
cd C:\Users\Administrator\OneDrive\Documents\streaming\deploy
New-Item -ItemType Directory -Force -Path D:\Media\movies, D:\Media\series
powershell -File scripts\resolve-media-path.ps1 -ForceDrive D -UpdateEnv
docker compose --env-file .env up -d --force-recreate qbittorrent catalog-metadata storage-hls
powershell -File scripts\verify-d-mount.ps1
```

Si `verify-d-mount.ps1` falla, Docker no ve el disco completo. Haz esto **una vez**:

1. **Docker Desktop** → **Settings** → **Resources** → **File sharing**
2. Marca la unidad **D:**
3. **Apply & Restart**
4. Repite los comandos de arriba

**Criterio de éxito:** `docker exec skill-qbittorrent df -h /downloads` debe mostrar **cientos de GB** libres, no ~137 MB.

## Descargar películas de tu lista

```powershell
# Opción A: script completo (verifica D: antes de descargar)
& "C:\Program Files\Git\bin\bash.exe" deploy/scripts/bulk-download-movies.sh

# Opción B: manual
docker exec skill-catalog-metadata python -c "import urllib.request,json; req=urllib.request.Request('http://localhost:8004/api/v1/import', data=json.dumps({'source':'seed'}).encode(), headers={'Content-Type':'application/json'}, method='POST'); print(urllib.request.urlopen(req).read().decode())"

docker exec skill-catalog-metadata python -c "import urllib.request,json; body={'content_type':'movie','enrich_first':False,'dry_run':False}; req=urllib.request.Request('http://localhost:8004/api/v1/bulk-acquire', data=json.dumps(body).encode(), headers={'Content-Type':'application/json'}, method='POST'); print(urllib.request.urlopen(req, timeout=3600).read().decode())"
```

## Variables en `.env`

```env
MEDIA_HOST_PATH=D:/Media
BULK_ACQUIRE_HOST_MEDIA_PATH=D:/Media
```

**No uses** `setup-keyless.ps1` sin `-ForceDrive D` ni cambies manualmente a C: o E:.

## Si bulk-acquire queda en `paused`

Casi siempre significa que Docker ve poco espacio en `/downloads` (montaje USB roto). Ejecuta `verify-d-mount.ps1` y corrige File sharing.

## Qué funciona sin claves

| Componente | Comportamiento |
|------------|----------------|
| Watchlist | ~786 títulos importados desde YAML |
| TMDB | Omitido si `TMDB_API_KEY` vacío |
| Prowlarr | API key leída del `config.xml` local |
| YTS | Respaldo público si Prowlarr no encuentra nada |
| qBittorrent | http://localhost:8080 (admin / adminadmin) |

## Limitaciones

- **YTS** cubre sobre todo películas internacionales en inglés; el cine español/catalán depende de los alias en `search_queries`.
- **Sin indexers en Prowlarr** la cobertura es menor.
- **Series** quedan para la fase 2.
- El catálogo API funciona vía `docker exec skill-catalog-metadata` si nginx no arranca.
