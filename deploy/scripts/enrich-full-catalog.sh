#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
CATALOG_URL="${BASE_URL}/api/catalog"
BATCH_LIMIT="${BATCH_LIMIT:-50}"
SLEEP_SECS="${SLEEP_SECS:-1.5}"
MAX_ROUNDS="${MAX_ROUNDS:-200}"

echo "==> TMDB enrich — full catalog (batch=${BATCH_LIMIT})"

total_resolved=0
total_failed=0
round=0

while [ "$round" -lt "$MAX_ROUNDS" ]; do
  round=$((round + 1))
  RESULT=$(curl -sf -X POST "${CATALOG_URL}/api/v1/enrich-metadata" \
    -H "Content-Type: application/json" \
    -d "{\"limit\": ${BATCH_LIMIT}}")

  resolved=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('resolved', 0))")
  failed=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('failed', 0))")
  processed=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('processed', 0))")

  total_resolved=$((total_resolved + resolved))
  total_failed=$((total_failed + failed))

  echo "Round ${round}: processed=${processed} resolved=${resolved} failed=${failed} (cumulative resolved=${total_resolved})"

  if [ "$processed" -eq 0 ] || [ "$resolved" -eq 0 ] && [ "$failed" -eq 0 ]; then
    echo "==> No more pending titles"
    break
  fi

  sleep "$SLEEP_SECS"
done

echo "==> Enrich complete: resolved=${total_resolved} failed=${total_failed}"
