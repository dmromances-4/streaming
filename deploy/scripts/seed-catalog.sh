#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
CATALOG_URL="${BASE_URL}/api/catalog"

echo "==> Catalog health"
curl -sf "${CATALOG_URL}/health" | python3 -m json.tool

echo "==> Import seed YAML"
curl -sf -X POST "${CATALOG_URL}/api/v1/import" \
  -H "Content-Type: application/json" \
  -d '{"source":"seed"}' | python3 -m json.tool

echo "==> Stats"
curl -sf "${CATALOG_URL}/api/v1/stats" | python3 -m json.tool

echo "==> Seed catalog OK"
