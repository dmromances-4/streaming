#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
CATALOG_URL="${BASE_URL}/api/catalog"
SERIES_IDS="${SERIES_IDS:-series-american-californication,series-american-boardwalk-empire}"

IFS=',' read -ra IDS <<< "$SERIES_IDS"

for series_id in "${IDS[@]}"; do
  series_id=$(echo "$series_id" | xargs)
  [ -z "$series_id" ] && continue

  echo "==> Bootstrap ${series_id}"

  echo "  -> ensure-episodes"
  curl -sf -X POST "${CATALOG_URL}/api/v1/catalog/${series_id}/ensure-episodes" \
    -H "Content-Type: application/json" \
    -d '{}' | python3 -m json.tool

  echo "  -> scan-library"
  curl -sf -X POST "${CATALOG_URL}/api/v1/catalog/${series_id}/scan-library" \
    -H "Content-Type: application/json" \
    -d '{}' | python3 -m json.tool

  echo "  -> verify S01E01 has_local_media"
  EPISODES=$(curl -sf "${CATALOG_URL}/api/v1/catalog/${series_id}/episodes?season=1")
  has_local=$(echo "$EPISODES" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for ep in d.get('items', []):
    if ep.get('season_number') == 1 and ep.get('episode_number') == 1:
        print('yes' if ep.get('has_local_media') else 'no')
        break
else:
    print('missing')
")
  if [ "$has_local" != "yes" ]; then
    echo "ERROR: ${series_id} S01E01 has_local_media=${has_local}"
    exit 1
  fi
  echo "  OK: S01E01 linked to local media"
done

echo "==> Test library bootstrap OK"
