#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
LIVE_URL="${BASE_URL}/api/live"

echo "==> Skill #3 health"
curl -sf "${LIVE_URL}/health" | python3 -m json.tool

echo "==> Invalid URL (expect 400)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${LIVE_URL}/api/v1/proxy?url=not-a-url")
if [ "$STATUS" != "400" ]; then
  echo "Expected 400, got $STATUS"
  exit 1
fi
echo "OK: 400 for invalid proxy URL"

echo "==> Blocked localhost (expect 400)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "${LIVE_URL}/api/v1/proxy?url=http%3A%2F%2Flocalhost%2Ftest.m3u8")
if [ "$STATUS" != "400" ]; then
  echo "Expected 400, got $STATUS"
  exit 1
fi
echo "OK: SSRF block for localhost"

echo "==> All live checks passed"
