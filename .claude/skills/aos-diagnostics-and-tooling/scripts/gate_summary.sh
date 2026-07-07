#!/usr/bin/env bash
# gate_summary.sh - one-screen, strictly read-only status of the ArchetypeOS local gates.
#
# Runs, in order:
#   1. tools/pr_guardian.py against <base>..HEAD (stub PR body if none supplied)
#   2. tools/doc_staleness.py (detect only, never --fix)
#   3. pytest --collect-only counts for apps/api/tests and apps/worker/tests
#
# Usage (from anywhere inside the repo):
#   bash .claude/skills/aos-diagnostics-and-tooling/scripts/gate_summary.sh [BASE_REF] [BODY_FILE]
#   BASE_REF defaults to origin/main. BODY_FILE defaults to a generated stub body.
#
# Read-only guarantees: no git writes, no --fix, pytest cache disabled
# (-p no:cacheprovider), bytecode writes disabled (PYTHONDONTWRITEBYTECODE=1).
# The only file written is a mktemp stub body, removed on exit.
#
# Exit codes: 0 = no blocking gate tripped (guardian PASS or PASS_WITH_WARNINGS,
# staleness FRESH or ADVISORY). 1 = guardian BLOCK and/or HARD staleness.
# 2 = base ref not found.
set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Not inside a git repository." >&2
  exit 2
}
cd "${REPO_ROOT}"

BASE_REF="${1:-origin/main}"
BODY_FILE="${2:-}"

if ! git rev-parse --verify "${BASE_REF}" >/dev/null 2>&1; then
  echo "Base ref '${BASE_REF}' not found. Run: git fetch origin main" >&2
  exit 2
fi

TMP_BODY=""
cleanup() { [[ -n "${TMP_BODY}" ]] && rm -f "${TMP_BODY}"; }
trap cleanup EXIT

if [[ -z "${BODY_FILE}" ]]; then
  TMP_BODY="$(mktemp)"
  BODY_FILE="${TMP_BODY}"
  cat > "${BODY_FILE}" <<'BODY'
Local gate summary run (stub body).

Verification Status: Verification pending
Verification Level: Level 2
Verification Method: gate_summary.sh local execution
Evidence: Local gate summary; real evidence must be written into the PR body.
Limitations: Stub body is not a substitute for PR evidence.
Required Next Verifier: PR author must update the PR body before opening the PR.
BODY
fi

# Display-only normalization: doc_staleness SOFT messages contain a Unicode
# em-dash; house style forbids it in docs, so quoted output stays paste-safe.
sanitize() { sed 's/\xe2\x80\x94/-/g; s/\xe2\x80\x93/-/g'; }

export PYTHONDONTWRITEBYTECODE=1

# --- 1. PR Guardian ---------------------------------------------------------
GUARDIAN_OUT="$(python3 tools/pr_guardian.py --base "${BASE_REF}" --head HEAD --body-file "${BODY_FILE}" 2>&1)"
GUARDIAN_EXIT=$?
GUARDIAN_VERDICT="$(printf '%s\n' "${GUARDIAN_OUT}" | grep -m1 '^Verdict:' || echo 'Verdict: UNKNOWN (guardian crashed)')"
CHANGED_COUNT="$(printf '%s\n' "${GUARDIAN_OUT}" | grep -m1 '^Changed files:' || echo 'Changed files: ?')"

# --- 2. Doc staleness (detect only) -----------------------------------------
STALE_OUT="$(python3 tools/doc_staleness.py 2>&1)"
STALE_EXIT=$?
STALE_VERDICT="$(printf '%s\n' "${STALE_OUT}" | grep -m1 '^Verdict:' || echo 'Verdict: UNKNOWN (detector crashed)')"

# --- 3. Test collection counts ----------------------------------------------
# packages/aos_core is on PYTHONPATH so collection works even without the
# editable install; -p no:cacheprovider keeps this read-only.
API_COLLECT="$(PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests --collect-only -q -p no:cacheprovider 2>&1 | tail -1)"
WORKER_COLLECT="$(PYTHONPATH=apps/worker:packages/aos_core pytest apps/worker/tests --collect-only -q -p no:cacheprovider 2>&1 | tail -1)"

# --- Summary -----------------------------------------------------------------
echo "==============================================="
echo " ArchetypeOS gate summary  (read-only)"
echo " Range: ${BASE_REF}..HEAD ($(git rev-parse --short HEAD))"
echo "==============================================="
echo ""
echo "[1] PR Guardian   exit=${GUARDIAN_EXIT}   ${GUARDIAN_VERDICT}"
echo "    ${CHANGED_COUNT}"
printf '%s\n' "${GUARDIAN_OUT}" | grep '^- \[' | sanitize | sed 's/^/    /'
echo ""
echo "[2] Doc staleness  exit=${STALE_EXIT}   ${STALE_VERDICT}"
printf '%s\n' "${STALE_OUT}" | grep '^- \[' | sanitize | sed 's/^/    /'
echo ""
echo "[3] Test collection"
echo "    api:    ${API_COLLECT}"
echo "    worker: ${WORKER_COLLECT}"
echo ""

OVERALL=0
if [[ ${GUARDIAN_EXIT} -ne 0 || ${STALE_EXIT} -ne 0 ]]; then
  OVERALL=1
  echo "OVERALL: ATTENTION (guardian BLOCK and/or HARD staleness above)"
else
  echo "OVERALL: OK (no blocking gate tripped; warnings above still need reading)"
fi
exit ${OVERALL}
