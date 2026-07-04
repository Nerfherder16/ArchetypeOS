#!/usr/bin/env bash
set -euo pipefail

BASE_REF="${1:-origin/main}"
HEAD_REF="${2:-HEAD}"
BODY_FILE="${3:-}"

if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  echo "Base ref '$BASE_REF' not found. Run: git fetch origin main" >&2
  exit 2
fi

TMP_BODY=""
if [[ -z "$BODY_FILE" ]]; then
  TMP_BODY="$(mktemp)"
  BODY_FILE="$TMP_BODY"
  cat > "$BODY_FILE" <<'BODY'
Local pre-PR run.
BODY
fi

python tools/pr_guardian.py --base "$BASE_REF" --head "$HEAD_REF" --body-file "$BODY_FILE"

python -m compileall apps/api/app apps/api/tests apps/worker/app apps/worker/tests
PYTHONPATH=apps/api pytest apps/api/tests
PYTHONPATH=apps/worker pytest apps/worker/tests

if command -v npm >/dev/null 2>&1; then
  (cd apps/web && npm run build)
else
  echo "npm not found; skipping web build in local pre-PR script." >&2
fi

if command -v docker >/dev/null 2>&1; then
  docker compose config >/dev/null
else
  echo "docker not found; skipping docker compose config in local pre-PR script." >&2
fi

if [[ -n "$TMP_BODY" ]]; then
  rm -f "$TMP_BODY"
fi
