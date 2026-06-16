#!/usr/bin/env bash
# Push recovered Streaming repo to a private remote (run after creating empty repo on GitHub/GitLab).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

REMOTE_URL="${1:-}"

if [[ -z "$REMOTE_URL" ]]; then
  cat <<'EOF'
Usage: bash deploy/scripts/setup-remote.sh <git-remote-url>

Examples:
  bash deploy/scripts/setup-remote.sh git@github.com:USER/streaming.git
  bash deploy/scripts/setup-remote.sh https://github.com/USER/streaming.git

Create an empty private repository first, then run this script.
EOF
  exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

git push -u origin main
echo "Pushed to $REMOTE_URL"
