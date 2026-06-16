#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
CATALOG_URL="${BASE_URL}/api/catalog"
PAGE_SIZE="${PAGE_SIZE:-50}"
SLEEP_SECS="${SLEEP_SECS:-0.5}"
PRIORITY_IDS="${PRIORITY_IDS:-series-american-californication,series-american-boardwalk-empire}"

sync_series() {
  local series_id="$1"
  echo "  -> ensure-episodes ${series_id}"
  curl -sf -X POST "${CATALOG_URL}/api/v1/catalog/${series_id}/ensure-episodes" \
    -H "Content-Type: application/json" \
    -d '{}' > /dev/null
}

echo "==> Sync episodes — priority series first"
IFS=',' read -ra PRIORITY <<< "$PRIORITY_IDS"
for series_id in "${PRIORITY[@]}"; do
  series_id=$(echo "$series_id" | xargs)
  [ -z "$series_id" ] && continue
  sync_series "$series_id"
  sleep "$SLEEP_SECS"
done

echo "==> Sync episodes — all series with TMDB id"
offset=0
total_synced=0

while true; do
  RESPONSE=$(curl -sf "${CATALOG_URL}/api/v1/catalog?type=series&limit=${PAGE_SIZE}&offset=${offset}")
  ids=$(echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for item in d.get('items', []):
    if item.get('tmdb_id'):
        print(item['id'])
")

  if [ -z "$ids" ]; then
    count=$(echo "$RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('items', [])))")
    if [ "$count" -eq 0 ]; then
      break
    fi
    offset=$((offset + PAGE_SIZE))
    continue
  fi

  while IFS= read -r series_id; do
    [ -z "$series_id" ] && continue
    skip=0
    for p in "${PRIORITY[@]}"; do
      p=$(echo "$p" | xargs)
      if [ "$series_id" = "$p" ]; then
        skip=1
        break
      fi
    done
    [ "$skip" -eq 1 ] && continue
    sync_series "$series_id"
    total_synced=$((total_synced + 1))
    sleep "$SLEEP_SECS"
  done <<< "$ids"

  count=$(echo "$RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('items', [])))")
  if [ "$count" -lt "$PAGE_SIZE" ]; then
    break
  fi
  offset=$((offset + PAGE_SIZE))
done

echo "==> Episode sync complete (additional series synced: ${total_synced})"
