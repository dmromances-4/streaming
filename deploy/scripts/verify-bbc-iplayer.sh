#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE_URL:-http://127.0.0.1}"
API="${BASE}/api/live/api/v1"
HOST_PREFIX="${BASE}"

echo "== verify-bbc-iplayer =="

AUTH=$(curl -sf "${API}/auth/status" || echo "{}")
BBC_OK=$(echo "$AUTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('bbc_configured',False))")
VPN_UP=$(echo "$AUTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('vpn_up',True))")

echo "bbc_configured: ${BBC_OK}"
echo "vpn_up: ${VPN_UP}"

if [[ "$BBC_OK" != "True" ]]; then
  echo "SKIP: BBC_IPLAYER_COOKIES no configuradas"
  exit 0
fi

CHANNEL="uk-bbcone"
STREAM=$(curl -sf "${API}/channels/${CHANNEL}/stream" || true)
if [[ -z "$STREAM" ]]; then
  echo "FAIL: no stream JSON for ${CHANNEL}"
  exit 1
fi

echo "$STREAM" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('drm'), 'sin drm'; print('drm:', d['drm'])"

PROXIED=$(echo "$STREAM" | python3 -c "import sys,json; print(json.load(sys.stdin).get('proxied_url',''))")
if [[ "$PROXIED" != http* ]]; then
  PROXIED="${HOST_PREFIX}${PROXIED}"
fi

BODY=$(curl -sf "$PROXIED" | head -c 500 || true)
if echo "$BODY" | grep -qE 'EXTM3U|EXT-X-'; then
  echo "OK: ${CHANNEL} manifest HLS"
else
  echo "WARN: manifest sin EXT-M3U (puede requerir VPN UK)"
  exit 1
fi

echo "verify-bbc-iplayer: OK"
