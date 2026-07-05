#!/usr/bin/env bash
# Boot a throwaway ArchetypeOS API for the Playwright e2e suite.
#
# Playwright manages this process's lifecycle (starts it, polls /health, and
# kills it at the end of the run), so we exec uvicorn in the foreground. Each
# boot resets a fresh scratch sqlite DB and artifact dir so serial specs run
# against clean state. REPOSITORY_ROOT points at the committed e2e fixtures so
# the scan flow (local_path: 'demo-repo') resolves to fixtures/demo-repo.
#
# Redis is intentionally pointed at a dead port: /health returns 200 "degraded"
# without Redis (PR #39), which satisfies Playwright's readiness poll, and the
# e2e flows exercised here never enqueue jobs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# apps/web/e2e -> repo root is three levels up.
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
API_DIR="${REPO_ROOT}/apps/api"
FIXTURES_DIR="${SCRIPT_DIR}/fixtures"

# Fresh scratch state under a temp dir, reset on every boot.
SCRATCH_DIR="$(mktemp -d "${TMPDIR:-/tmp}/aos-web-e2e.XXXXXX")"
DB_PATH="${SCRATCH_DIR}/e2e.db"
ARTIFACT_DIR="${SCRATCH_DIR}/artifacts"
rm -f "${DB_PATH}"
mkdir -p "${ARTIFACT_DIR}"

export PYTHONPATH="${API_DIR}"
export DATABASE_URL="sqlite:///${DB_PATH}"
export ARTIFACT_ROOT="${ARTIFACT_DIR}"
export REPOSITORY_ROOT="${FIXTURES_DIR}"
export REDIS_URL="redis://localhost:9999/0"

# Run from the scratch dir so pydantic's env_file=".env" never picks up a stray
# repo .env; the explicit exports above are authoritative.
cd "${SCRATCH_DIR}"

exec python3 -m uvicorn app.main:app --port 8000
