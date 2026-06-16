#!/usr/bin/env bash
# Resuelve magnets Coctelería vía Jackett e inicia batch ingest
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
CATALOG_URL="${BASE_URL}/api/catalog"

if [ -z "${JACKETT_API_KEY:-}" ]; then
  echo "WARN: JACKETT_API_KEY no definida — resolve-magnets fallará"
  echo "Configura Jackett en http://localhost:9117 y añade la key al .env"
fi

echo "==> Resolve magnets (cocteleria, limit 42)"
curl -sf -X POST "${CATALOG_URL}/api/v1/resolve-magnets" \
  -H "Content-Type: application/json" \
  -d '{"priority_only":true,"limit":42}' | python3 -m json.tool

echo "==> Batch ingest (cocteleria, limit 5)"
curl -sf -X POST "${CATALOG_URL}/api/v1/batch-ingest" \
  -H "Content-Type: application/json" \
  -d '{"priority_only":true,"limit":5,"concurrency":2}' | python3 -m json.tool

echo "==> Final stats"
curl -sf "${CATALOG_URL}/api/v1/stats" | python3 -m json.tool

echo "==> Coctelería ingest pipeline triggered"
