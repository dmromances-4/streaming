#!/usr/bin/env bash
# Verificación Fase 2 — Skill #2 Storage & HLS
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
HLS_URL="${BASE_URL}/api/hls"

echo "==> Skill #2 health"
curl -sf "${HLS_URL}/health" | python3 -m json.tool

echo "==> Skill #2 metrics"
curl -sf "${HLS_URL}/metrics" | head -15

echo "==> Transcode validation (expect 422 without source)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${HLS_URL}/api/v1/transcode" \
  -H "Content-Type: application/json" \
  -d '{}')
if [ "$STATUS" != "422" ]; then
  echo "Expected 422, got $STATUS"
  exit 1
fi
echo "OK: 422 for empty transcode request"

echo "==> Job not found (expect 404)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${HLS_URL}/api/v1/status/00000000-0000-0000-0000-000000000000")
if [ "$STATUS" != "404" ]; then
  echo "Expected 404, got $STATUS"
  exit 1
fi
echo "OK: 404 for unknown job"

echo "==> All HLS checks passed"
