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
# A throwaway COPY of the committed vault (absolute path so it survives the
# `cd "${SCRATCH_DIR}"` below). POST /knowledge/sync still finds the real lessons
# index (copied verbatim), but the ADR-export flow (POST /decisions/{id}/adr,
# exercised by decision-loop.spec) writes ADR markdown under
# <knowledge_root>/wiki/decisions/ — pointing at the real repo vault would leave
# untracked ADR files in the committed tree and break the knowledge-sync counts.
KNOWLEDGE_DIR="${SCRATCH_DIR}/knowledge"
mkdir -p "${KNOWLEDGE_DIR}"
cp -a "${REPO_ROOT}/knowledge/." "${KNOWLEDGE_DIR}/"
export KNOWLEDGE_ROOT="${KNOWLEDGE_DIR}"
export REDIS_URL="redis://localhost:9999/0"
# AOS-VOICE-002: the CommandDeck now routes typed/spoken commands through
# POST /voice/turns. Pin the voice brain to the deterministic provider so e2e
# never shells out to a (absent) `claude` CLI — the turn resolves instantly via
# the keyword classifier + templated reply, keeping specs fast and hermetic.
export VOICE_LLM_PROVIDER="deterministic"

# Ephemeral Redis for the job queue. --save '' + --appendonly no keep it purely
# in-memory (no dump.rdb/AOF files). If binding 9999 fails because a prior stack
# left one running, that existing Redis serves the queue and enqueue still works.
redis-server --port 9999 --save '' --appendonly no --daemonize no >/dev/null 2>&1 &
REDIS_PID=$!

cleanup() {
  kill "${REDIS_PID}" 2>/dev/null || true
  [ -n "${WORKER_PID:-}" ] && kill "${WORKER_PID}" 2>/dev/null || true
  [ -n "${API_PID:-}" ] && kill "${API_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Run from the scratch dir so pydantic's env_file=".env" never picks up a stray
# repo .env; the explicit exports above are authoritative.
cd "${SCRATCH_DIR}"

python3 -m uvicorn app.main:app --port 8000 &
API_PID=$!

# Drain the job queue so enqueued council reviews (and scans/digests) actually
# complete in e2e. The worker shares this boot's sqlite DB + Redis via the same
# DATABASE_URL/REDIS_URL/REPOSITORY_ROOT/ARTIFACT_ROOT/KNOWLEDGE_ROOT exported
# above. It needs its OWN PYTHONPATH: apps/worker also ships an `app` package
# (app.worker), so it must precede apps/api's `app` package (app.main) here —
# hence a per-process override rather than reusing the exported API PYTHONPATH.
PYTHONPATH="${REPO_ROOT}/apps/worker:${REPO_ROOT}/packages/aos_core" python3 -m app.worker &
WORKER_PID=$!

wait "${API_PID}"
