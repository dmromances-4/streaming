#!/usr/bin/env bash
# Fase 1: importar watchlist y lanzar descarga masiva de películas (sin cuentas externas).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/deploy/.env}"

echo "==> Forzar ruta D: (sin fallback a C:/E:)"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/resolve-media-path.ps1" -ForceDrive D -UpdateEnv

echo "==> Verificar montaje Docker en D:"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/verify-d-mount.ps1" || {
  echo "AVISO: montaje Docker incorrecto. Corrige File sharing en Docker Desktop antes de descargar."
  exit 1
}

echo "==> API key local de Prowlarr (opcional)"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/setup-keyless.ps1" -UpdateEnv 2>/dev/null || true

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

BASE="${CATALOG_URL:-http://127.0.0.1/api/catalog/api/v1}"
CURL_OPTS=(-4 -sf)

echo "==> Regenerar YAML de la watchlist"
python3 "$ROOT/deploy/scripts/build-watchlist-json.py" 2>/dev/null || true
python3 "$ROOT/deploy/scripts/generate-watchlist-seed.py"

echo "==> Salud del catálogo"
curl "${CURL_OPTS[@]}" "$BASE/health" | python3 -m json.tool

echo "==> Importar semilla"
curl "${CURL_OPTS[@]}" -X POST "$BASE/import" \
  -H "Content-Type: application/json" \
  -d '{"source":"seed"}' | python3 -m json.tool

echo "==> Descarga masiva de películas (TMDB opcional, YTS como respaldo)"
curl "${CURL_OPTS[@]}" --max-time 3600 -X POST "$BASE/bulk-acquire" \
  -H "Content-Type: application/json" \
  -d '{"content_type":"movie","enrich_first":false,"dry_run":false}' \
  | python3 -m json.tool

echo "==> Estado"
curl "${CURL_OPTS[@]}" "$BASE/bulk-acquire/status" | python3 -m json.tool

echo "==> Listo. Revisa qBittorrent: http://localhost:8080"
