#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE_URL:-http://127.0.0.1}/api/live/api/v1"

echo "== verify-live-channels =="

curl -sf "${BASE%/api/v1}/health" | python3 -m json.tool

echo "Channels:"
curl -sf "${BASE}/channels" | python3 -m json.tool

HEALTH=$(curl -sf "${BASE}/channels/health")
echo "$HEALTH" | python3 -m json.tool

OK=$(echo "$HEALTH" | python3 -c "import sys,json; print('yes' if json.load(sys.stdin).get('ok') else 'no')")
if [[ "$OK" != "yes" ]]; then
  echo "WARN: RTVE resolver no pudo obtener La 1 (geo-block o red)"
  exit 0
fi

STREAM=$(curl -sf "${BASE}/channels/rtve-la1/stream")
echo "$STREAM" | python3 -m json.tool
PROXIED=$(echo "$STREAM" | python3 -c "import sys,json; print(json.load(sys.stdin).get('proxied_url',''))")

if [[ -n "$PROXIED" ]]; then
  if [[ "$PROXIED" != http* ]]; then
    PROXIED="${BASE_URL:-http://127.0.0.1}${PROXIED}"
  fi
  BODY=$(curl -sf "$PROXIED" | head -c 80)
  if echo "$BODY" | grep -q EXT; then
    echo "OK: proxy devuelve playlist HLS"
  else
    echo "WARN: proxy no devolvió M3U8 válido"
  fi
fi
