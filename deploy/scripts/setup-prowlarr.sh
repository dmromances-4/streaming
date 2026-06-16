#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"

echo "== setup-prowlarr =="

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# Desde el host Docker usa localhost; dentro del compose usa prowlarr:9696.
INDEXER_URL="${INDEXER_URL:-http://127.0.0.1:9696}"
if [[ "$INDEXER_URL" == *"prowlarr"* ]]; then
  INDEXER_URL="http://127.0.0.1:9696"
fi
API_KEY="${INDEXER_API_KEY:-}"

echo ""
echo "1. Abre Prowlarr: http://localhost:9696 (API: ${INDEXER_URL})"
echo "   → Settings → General → copia API Key"
echo "   → Indexers → añade al menos un indexer (torrent) y actívalo"
echo ""

if [[ -z "$API_KEY" ]]; then
  echo "WARN: INDEXER_API_KEY vacío en ${ENV_FILE}"
  echo "Añade: INDEXER_API_KEY=tu_clave"
  exit 1
fi

echo "2. Comprobando API key..."
HTTP_CODE=$(curl -s -o /tmp/prowlarr-indexers.json -w "%{http_code}" \
  -H "X-Api-Key: ${API_KEY}" \
  "${INDEXER_URL}/api/v1/indexer" || echo "000")

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "FAIL: Prowlarr respondió HTTP ${HTTP_CODE}"
  exit 1
fi

ENABLED=$(python3 -c "
import json
data = json.load(open('/tmp/prowlarr-indexers.json'))
print(sum(1 for i in data if i.get('enable')))
")

echo "   Indexers activos: ${ENABLED}"
if [[ "$ENABLED" -lt 1 ]]; then
  echo "WARN: No hay indexers activos. Añade uno en la UI de Prowlarr."
  exit 1
fi

echo ""
echo "3. Búsqueda de prueba..."
SEARCH=$(curl -s -H "X-Api-Key: ${API_KEY}" \
  "${INDEXER_URL}/api/v1/search?query=Boardwalk%20Empire%20S01E01&type=search" | head -c 200)
if [[ -z "$SEARCH" || "$SEARCH" == "[]" ]]; then
  echo "WARN: Búsqueda sin resultados (puede ser normal si el indexer no tiene ese título)"
else
  echo "OK: Prowlarr devolvió resultados"
fi

echo ""
echo "4. Siguiente paso:"
echo "   cd deploy && docker compose --env-file ../.env up -d --build catalog-metadata"
echo "   curl http://localhost/api/catalog/api/v1/system/status"
