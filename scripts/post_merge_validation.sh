#!/usr/bin/env bash
set -euo pipefail

TARGET_REF="${1:-origin/main}"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git fetch origin main >/dev/null 2>&1 || true
fi

if ! git rev-parse --verify "$TARGET_REF" >/dev/null 2>&1; then
  echo "Target ref '$TARGET_REF' not found. Run: git fetch origin main" >&2
  exit 2
fi

echo "Validating $TARGET_REF"

python -m compileall apps/api/app apps/api/tests apps/worker/app apps/worker/tests
PYTHONPATH=apps/api pytest apps/api/tests
PYTHONPATH=apps/worker pytest apps/worker/tests

if command -v npm >/dev/null 2>&1; then
  (cd apps/web && npm install && npm run build)
else
  echo "npm not found; skipping web build." >&2
fi

if command -v docker >/dev/null 2>&1; then
  docker compose config >/dev/null
else
  echo "docker not found; skipping docker compose config." >&2
fi

if command -v gh >/dev/null 2>&1; then
  echo "Latest CI run on main:"
  gh run list --branch main --workflow CI --limit 1 || true
else
  echo "gh not found; inspect GitHub Actions manually for latest main CI run." >&2
fi

echo "Post-merge validation checks completed."
