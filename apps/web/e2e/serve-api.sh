#!/usr/bin/env bash
# Boot a throwaway ArchetypeOS API for the Playwright e2e suite.
#
# Playwright manages this process's lifecycle (starts it, polls /health, and
# kills it at the end of the run). Each boot resets a fresh scratch sqlite DB
# and artifact dir so serial specs run against clean state. REPOSITORY_ROOT
# points at the committed e2e fixtures so the scan flow (local_path:
# 'demo-repo') resolves to fixtures/demo-repo.
#
# An ephemeral Redis is started on port 9999 (below) so the job-origination
# path works end-to-end: the scheduling e2e spec's "Run now" / enqueue-now
# controls lpush onto the queue, which a dead port would 500. Redis runs with
# no persistence and is torn down with the API. If the port is already bound
# (a reused stack), the existing Redis is used instead.
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

# app.* resolves from apps/api; aos_core resolves from its source package so the
# stack boots whether or not aos_core is pip-installed into this interpreter.
export PYTHONPATH="${API_DIR}:${REPO_ROOT}/packages/aos_core"
export DATABASE_URL="sqlite:///${DB_PATH}"
export ARTIFACT_ROOT="${ARTIFACT_DIR}"
export REPOSITORY_ROOT="${FIXTURES_DIR}"
export REDIS_URL="redis://localhost:9999/0"

# Ephemeral Redis for the job queue. --save '' + --appendonly no keep it purely
# in-memory (no dump.rdb/AOF files). If binding 9999 fails because a prior stack
# left one running, that existing Redis serves the queue and enqueue still works.
redis-server --port 9999 --save '' --appendonly no --daemonize no >/dev/null 2>&1 &
REDIS_PID=$!

cleanup() {
  kill "${REDIS_PID}" 2>/dev/null || true
  [ -n "${API_PID:-}" ] && kill "${API_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Run from the scratch dir so pydantic's env_file=".env" never picks up a stray
# repo .env; the explicit exports above are authoritative.
cd "${SCRATCH_DIR}"

python3 -m uvicorn app.main:app --port 8000 &
API_PID=$!
wait "${API_PID}"
