#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"

echo "==> Frontend HTML"
curl -sf "${BASE_URL}/" | grep -q "Streaming Platform"
echo "OK: index.html served"

echo "==> Frontend JS"
curl -sf "${BASE_URL}/js/app.js" | grep -q "Hls"
echo "OK: app.js served"

echo "==> Frontend CSS"
curl -sf "${BASE_URL}/css/style.css" | grep -q "0d0f14"
echo "OK: dark theme CSS served"

echo "==> All frontend checks passed"
