#!/usr/bin/env bash
# Verificación Fase 1 — requiere docker compose en ejecución
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
INGEST_URL="${BASE_URL}/api/ingest"

echo "==> Health check"
curl -sf "${BASE_URL}/health" | python3 -m json.tool

echo "==> Skill health via nginx"
curl -sf "${INGEST_URL}/health" | python3 -m json.tool

echo "==> Metrics"
curl -sf "${INGEST_URL}/metrics" | head -20

echo "==> Invalid magnet (expect 400)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${INGEST_URL}/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{"magnet_uri": "not-a-magnet"}')
if [ "$STATUS" != "400" ]; then
  echo "Expected 400, got $STATUS"
  exit 1
fi
echo "OK: 400 for invalid magnet"

# Big Buck Bunny — contenido libre Blender Foundation (opcional, requiere red P2P)
if [ "${RUN_LIVE_TORRENT_TEST:-0}" = "1" ]; then
  MAGNET='magnet:?xt=urn:btih:dd8255fecf9ae244b1d14e716841219eb3779a7&dn=Big+Buck+Bunny'
  echo "==> Live ingest test"
  RESP=$(curl -sf -X POST "${INGEST_URL}/api/v1/ingest" \
    -H "Content-Type: application/json" \
    -d "{\"magnet_uri\": \"${MAGNET}\"}")
  echo "$RESP" | python3 -m json.tool
  SESSION_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
  echo "==> Stream first 1MB (session: $SESSION_ID)"
  curl -sf -r 0-1048575 "${INGEST_URL}/api/v1/stream/${SESSION_ID}" -o /tmp/stream-test.bin
  BYTES=$(wc -c < /tmp/stream-test.bin | tr -d ' ')
  echo "Downloaded $BYTES bytes"
  if [ "$BYTES" -lt 1000 ]; then
    echo "WARN: fewer than 1KB received (peers may be unavailable)"
  else
    echo "OK: stream working"
  fi
fi

echo "==> Skill #2 HLS checks"
bash "$(dirname "$0")/verify-hls.sh"

echo "==> Skill #3 Live checks"
bash "$(dirname "$0")/verify-live.sh"

echo "==> Skill #4 Frontend checks"
bash "$(dirname "$0")/verify-frontend.sh"

echo "==> Skill #6 Catalog checks"
bash "$(dirname "$0")/verify-catalog.sh"

echo "==> All MVP checks passed"
