#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE_URL:-http://127.0.0.1}"
API="${BASE}/api/live/api/v1"
HOST_PREFIX="${BASE}"

echo "== verify-spanish-autonomic =="

ES_TOTAL=$(curl -sf "${API}/channels?country=ES" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('channels',[])))")
AUTO_TOTAL=$(curl -sf "${API}/channels?country=ES&tag=autonomic" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('channels',[])))")

echo "Canales ES: ${ES_TOTAL} (autonómicos: ${AUTO_TOTAL})"

if [[ "${ES_TOTAL}" -lt 30 ]]; then
  echo "FAIL: se esperaban al menos 30 canales españoles"
  exit 1
fi

if [[ "${AUTO_TOTAL}" -lt 25 ]]; then
  echo "FAIL: se esperaban al menos 25 canales autonómicos"
  exit 1
fi

check_stream() {
  local id="$1"
  local label="$2"
  local strict="${3:-0}"
  STREAM=$(curl -sf "${API}/channels/${id}/stream" || true)
  if [[ -z "$STREAM" ]]; then
    if [[ "$strict" == "1" ]]; then
      echo "FAIL: [${label}] no stream JSON for ${id}"
      return 1
    fi
    echo "WARN: [${label}] no stream JSON for ${id}"
    return 1
  fi
  ERR=$(echo "$STREAM" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error',''))" 2>/dev/null || true)
  if [[ -n "$ERR" ]]; then
    if [[ "$strict" == "1" ]]; then
      echo "FAIL: [${label}] ${id}: ${ERR}"
      return 1
    fi
    echo "WARN: [${label}] ${id}: ${ERR}"
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
  if [[ "$strict" == "1" ]]; then
    echo "FAIL: [${label}] ${id} proxy sin M3U8"
    return 1
  fi
  echo "WARN: [${label}] ${id} proxy sin M3U8 (geo-block?)"
  return 1
}

OK=0
FAIL=0

for id in es-ccma-tv3 es-etb1 es-telemadrid es-csur-andalucia; do
  if check_stream "$id" "tier-es-core" 1; then OK=$((OK + 1)); else FAIL=$((FAIL + 1)); fi
done

for id in es-aragon-tv es-tvg2 es-apunt es-telemadrid-laotra; do
  if check_stream "$id" "tier-es-static"; then OK=$((OK + 1)); else FAIL=$((FAIL + 1)); fi
done

for id in es-tvg es-cyl-la7; do
  if check_stream "$id" "tier-es-dynamic"; then OK=$((OK + 1)); else FAIL=$((FAIL + 1)); fi
done

SAMPLE_TOTAL=10
echo "Muestra autonómicas: ${OK} OK, ${FAIL} fallos/warnings (objetivo ${SAMPLE_TOTAL}/${SAMPLE_TOTAL})"
if [[ "$OK" -lt "${SAMPLE_TOTAL}" ]]; then
  echo "FAIL: se esperaban ${SAMPLE_TOTAL}/${SAMPLE_TOTAL} muestras OK (obtenidas: ${OK})"
  exit 1
fi
echo "verify-spanish-autonomic: OK"
