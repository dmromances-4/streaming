#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
CATALOG_URL="${BASE_URL}/api/catalog"

echo "==> Skill #6 health"
curl -sf "${CATALOG_URL}/health" | python3 -m json.tool

echo "==> Stats"
STATS=$(curl -sf "${CATALOG_URL}/api/v1/stats")
echo "$STATS" | python3 -m json.tool

TOTAL=$(echo "$STATS" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])")
if [ "$TOTAL" -lt 700 ]; then
  echo "WARN: expected ~785 titles, got $TOTAL (run seed-catalog.sh first)"
fi

echo "==> Catalog search"
curl -sf "${CATALOG_URL}/api/v1/catalog?q=breaking&type=series&limit=3" | python3 -m json.tool

echo "==> Catalog list sample"
curl -sf "${CATALOG_URL}/api/v1/catalog?cocteleria=1&limit=5" | python3 -m json.tool

echo "==> Series episode API"
SERIES_ID=$(curl -sf "${CATALOG_URL}/api/v1/catalog?q=Breaking%20Bad&type=series&limit=1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['items'][0]['id'] if d['items'] else '')")
if [ -z "$SERIES_ID" ]; then
  SERIES_ID=$(curl -sf "${CATALOG_URL}/api/v1/catalog?type=series&limit=1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['items'][0]['id'] if d['items'] else '')")
fi

if [ -n "$SERIES_ID" ]; then
  echo "Using series: ${SERIES_ID}"
  curl -sf -X POST "${CATALOG_URL}/api/v1/catalog/${SERIES_ID}/ensure-episodes" | python3 -m json.tool
  curl -sf "${CATALOG_URL}/api/v1/catalog/${SERIES_ID}/seasons" | python3 -m json.tool
  EPISODES=$(curl -sf "${CATALOG_URL}/api/v1/catalog/${SERIES_ID}/episodes?season=1")
  echo "$EPISODES" | python3 -m json.tool
  EP1=$(echo "$EPISODES" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['items'][0]['id'] if d.get('items') else '')")
  if [ -n "$EP1" ]; then
    curl -sf "${CATALOG_URL}/api/v1/episodes/${EP1}" | python3 -m json.tool
    curl -sf "${CATALOG_URL}/api/v1/episodes/${EP1}/status" | python3 -m json.tool
    MANIFEST=$(echo "$EPISODES" | python3 -c "import sys,json; d=json.load(sys.stdin); m=d['items'][0].get('manifest_url') if d.get('items') else None; print(m or '')")
    if [ -n "$MANIFEST" ]; then
      if [[ "$MANIFEST" == /api/hls/* ]]; then
        echo "OK: manifest_url is relative ($MANIFEST)"
      else
        echo "WARN: manifest_url not relative: $MANIFEST"
      fi
    fi
  fi
  echo "Series endpoints OK for ${SERIES_ID}"
else
  echo "WARN: no series in catalog for episode smoke test"
fi

echo "==> Test library series (Californication / Boardwalk Empire)"
for TEST_ID in series-american-californication series-american-boardwalk-empire; do
  ITEM=$(curl -sf "${CATALOG_URL}/api/v1/catalog/${TEST_ID}")
  POSTER=$(echo "$ITEM" | python3 -c "import sys,json; print(json.load(sys.stdin).get('poster_url') or '')")
  TMDB=$(echo "$ITEM" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tmdb_id') or '')")
  if [ -z "$POSTER" ]; then
    echo "WARN: ${TEST_ID} missing poster_url (run enrich-full-catalog.sh)"
  else
    echo "OK: ${TEST_ID} poster_url set"
  fi
  if [ -z "$TMDB" ]; then
    echo "WARN: ${TEST_ID} missing tmdb_id"
  fi

  EPISODES=$(curl -sf "${CATALOG_URL}/api/v1/catalog/${TEST_ID}/episodes?season=1")
  HAS_LOCAL=$(echo "$EPISODES" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for ep in d.get('items', []):
    if ep.get('season_number') == 1 and ep.get('episode_number') == 1:
        print('yes' if ep.get('has_local_media') else 'no')
        break
else:
    print('missing')
")
  if [ "$HAS_LOCAL" = "yes" ]; then
    echo "OK: ${TEST_ID} S01E01 has_local_media"
  else
    echo "WARN: ${TEST_ID} S01E01 has_local_media=${HAS_LOCAL} (run bootstrap-test-library.sh)"
  fi
done

echo "==> Local library endpoint"
curl -sf "${CATALOG_URL}/api/v1/catalog/local-library?limit=5" | python3 -m json.tool

echo "==> Frontend home"
curl -sf -o /dev/null -w "HTTP %{http_code}\n" "${BASE_URL}/"

echo "==> All catalog checks passed"
