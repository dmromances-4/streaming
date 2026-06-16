#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
CATALOG_URL="${BASE_URL}/api/catalog"

echo "==> Scan all library"
curl -sf -X POST "${CATALOG_URL}/api/v1/catalog/scan-all-library" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool

echo "==> Scan all library OK"
