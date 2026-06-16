#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE_URL:-http://127.0.0.1}"
API="${BASE}/api/live/api/v1"
HOST_PREFIX="${BASE}"

echo "== verify-european-channels =="

TOTAL=$(curl -sf "${API}/channels" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))")
echo "Total canales: ${TOTAL}"

if [[ "${TOTAL}" -lt 50 ]]; then
  echo "FAIL: se esperaban al menos 50 canales"
  exit 1
fi

COUNTRIES=$(curl -sf "${API}/channels" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('countries',[])))")
echo "Países: ${COUNTRIES}"

check_stream() {
  local id="$1"
  local label="$2"
  STREAM=$(curl -sf "${API}/channels/${id}/stream" || true)
  if [[ -z "$STREAM" ]]; then
    echo "WARN: [${label}] no stream JSON for ${id}"
    return 1
  fi
  PROXIED=$(echo "$STREAM" | python3 -c "import sys,json; print(json.load(sys.stdin).get('proxied_url',''))")
  if [[ -z "$PROXIED" ]]; then
    echo "WARN: [${label}] sin proxied_url ${id}"
    return 1
  fi
  if [[ "$PROXIED" != http* ]]; then
    PROXIED="${HOST_PREFIX}${PROXIED}"
  fi
  BODY=$(curl -sf "$PROXIED" | head -c 80 || true)
  if echo "$BODY" | grep -q EXT; then
    echo "OK: [${label}] ${id}"
    return 0
  fi
  echo "WARN: [${label}] ${id} proxy sin M3U8"
  return 1
}

OK=0
FAIL=0

# Tier 1: static / rtve
for id in de-daserste rtve-la1; do
  if check_stream "$id" "tier1"; then OK=$((OK + 1)); else FAIL=$((FAIL + 1)); fi
done

# Tier ES autonómicas (muestra)
for id in es-ccma-tv3 es-etb1 es-telemadrid; do
  if check_stream "$id" "tier-es-autonomic"; then OK=$((OK + 1)); else FAIL=$((FAIL + 1)); fi
done

# Tier 2: dynamic clear HLS
for id in fr-france2 it-rai1 pt-rtp1; do
  if check_stream "$id" "tier2"; then OK=$((OK + 1)); else FAIL=$((FAIL + 1)); fi
done

# Tier 3: BBC iPlayer (solo si cookies configuradas)
BBC_OK=$(curl -sf "${API}/auth/status" | python3 -c "import sys,json; print(json.load(sys.stdin).get('bbc_configured',False))" 2>/dev/null || echo "False")
if [[ "$BBC_OK" == "True" ]]; then
  if check_stream "uk-bbcone" "tier3-bbc"; then OK=$((OK + 1)); else FAIL=$((FAIL + 1)); fi
else
  echo "SKIP: tier3 BBC (BBC_IPLAYER_COOKIES no configuradas)"
fi

echo "Muestra: ${OK} OK, ${FAIL} fallos"
if [[ "$OK" -lt 2 ]]; then
  exit 1
fi
echo "verify-european-channels: OK"
