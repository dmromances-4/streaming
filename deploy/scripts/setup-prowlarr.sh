#!/usr/bin/env bash
# Comprueba Prowlarr local (sin pedir cuentas externas).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/deploy/.env}"

echo "==> Prowlarr local (sin registro externo)"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/setup-keyless.ps1" -UpdateEnv || true

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

INDEXER_URL="${INDEXER_URL:-http://127.0.0.1:9696}"
if [[ "$INDEXER_URL" == *"prowlarr"* ]]; then
  INDEXER_URL="http://127.0.0.1:9696"
fi
API_KEY="${INDEXER_API_KEY:-}"

if [[ -z "$API_KEY" ]]; then
  echo "AVISO: sin API key de Prowlarr todavía."
  echo "  Arranca el stack: cd deploy && docker compose up -d"
  echo "  Vuelve a ejecutar este script; leerá la clave del config.xml automáticamente."
  echo "  Sin indexers en Prowlarr, las películas usarán YTS como respaldo."
  exit 0
fi

HTTP_CODE=$(curl -4 -s -o /tmp/prowlarr-indexers.json -w "%{http_code}" \
  -H "X-Api-Key: ${API_KEY}" \
  "${INDEXER_URL}/api/v1/indexer" || echo "000")

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "AVISO: Prowlarr respondió HTTP ${HTTP_CODE}"
  echo "  Las descargas pueden seguir funcionando vía YTS."
  exit 0
fi

ENABLED=$(python3 -c "
import json
data = json.load(open('/tmp/prowlarr-indexers.json'))
print(sum(1 for i in data if i.get('enable')))
")

echo "Indexers activos en Prowlarr: ${ENABLED}"
if [[ "$ENABLED" -lt 1 ]]; then
  echo "Sin indexers: OK igualmente — YTS cubre muchas películas internacionales."
else
  echo "OK: Prowlarr listo con indexers."
fi
