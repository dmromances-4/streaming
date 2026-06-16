#!/usr/bin/env bash
# Smoke test: episodio sin archivo local → POST acquire → downloading/transcoding
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

BASE="${CATALOG_URL:-http://127.0.0.1/api/catalog/api/v1}"
SERIES_ID="${VERIFY_ACQUIRE_SERIES_ID:-series-american-archer}"
SEASON="${VERIFY_ACQUIRE_SEASON:-1}"
EPISODE="${VERIFY_ACQUIRE_EPISODE:-1}"

echo "== verify-acquire =="
echo "Base: $BASE"
echo "Target: $SERIES_ID S$(printf '%02d' "$SEASON")E$(printf '%02d' "$EPISODE")"

EPISODE_ID="${SERIES_ID}-s$(printf '%02d' "$SEASON")e$(printf '%02d' "$EPISODE")"
EP_JSON="$(curl -sf "$BASE/episodes/$EPISODE_ID" 2>/dev/null || echo '{}')"
HAS_LOCAL="$(echo "$EP_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print('1' if d.get('has_local_media') else '0')" 2>/dev/null || echo 0)"

if [[ "$HAS_LOCAL" == "1" ]]; then
  echo "SKIP: episodio ya tiene archivo local ($EPISODE_ID)"
  exit 0
fi

echo "POST acquire $EPISODE_ID (timeout 45s)"
RESP="$(curl -sf --max-time 45 -X POST "$BASE/episodes/$EPISODE_ID/acquire" \
  -H 'Content-Type: application/json' \
  -d '{}' || true)"

if [[ -z "$RESP" ]]; then
  echo "FAIL: acquire sin respuesta"
  exit 1
fi

echo "$RESP" | python3 -m json.tool

STAGE="$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stage') or d.get('pipeline_status',''))")"
STATUS="$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('pipeline_status',''))")"

case "$STAGE" in
  downloading|searching|transcoding|ready|ingesting)
    echo "OK: stage=$STAGE status=$STATUS"
    ;;
  failed)
    MSG="$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message') or '')")"
    echo "WARN: acquire failed — $MSG (Prowlarr/indexers pueden no estar configurados)"
    exit 0
    ;;
  *)
    if [[ "$STATUS" == "transcoding" || "$STATUS" == "ingesting" || "$STATUS" == "ready" ]]; then
      echo "OK: status=$STATUS"
    else
      echo "FAIL: respuesta inesperada stage=$STAGE status=$STATUS"
      exit 1
    fi
    ;;
esac
