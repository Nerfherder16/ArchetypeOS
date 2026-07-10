#!/usr/bin/env bash
#
# AOS-SELFHEAL-002b — reconcile nightly (local-cron path).
#
# The deterministic gate for the doc-staleness self-heal loop's *correct* half.
# Runs the detector; only if the state docs have drifted does it wake a headless
# `claude` to apply the narrative reconciliation and OPEN a PR for human review.
# It never merges and never edits over a dirty tree.
#
# Cloud path: the same logic runs as a `/schedule` routine whose prompt is
# scripts/nightly/reconcile_state.prompt.md — see docs/runbooks/nightly-routines.md.
#
# Env:
#   CLAUDE_BIN    claude executable (default: claude)
#   CLAUDE_FLAGS  flags for headless run (default: --permission-mode acceptEdits)
#   DRY_RUN=1     detect + log only; do not invoke claude
#
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$REPO_ROOT"

LOG=".archetype/reconciliation/nightly.log"
mkdir -p "$(dirname "$LOG")"
log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG" >&2; }

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_FLAGS="${CLAUDE_FLAGS:---permission-mode acceptEdits --model sonnet}"
DRY_RUN="${DRY_RUN:-0}"

# 1. Never reconcile over uncommitted local work.
if [ -n "$(git status --porcelain)" ]; then
  log "SKIP: working tree dirty — refusing to reconcile over local changes."
  exit 0
fi

# 2. Sync main.
git fetch --quiet origin main
git checkout --quiet main
git pull --quiet --ff-only origin main

# 3. Deterministic gate: detect drift. Clear any stale draft first so we act only
#    on today's real drift (mirrors the CI workflow's fresh-checkout semantics).
rm -f .archetype/reconciliation/PENDING.md
python3 tools/doc_staleness.py --fix >/dev/null 2>&1 || true
if [ ! -f .archetype/reconciliation/PENDING.md ]; then
  log "FRESH: state docs current with git — nothing to reconcile."
  exit 0
fi
log "DRIFT: reconciliation draft written ($(wc -l < .archetype/reconciliation/PENDING.md) lines)."

# 4. One fresh branch per day; if a reconcile PR is already open, do nothing.
BRANCH="laptop/nightly-reconcile-$(date -u +%Y%m%d)"
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  log "SKIP: $BRANCH already on origin — today's reconcile PR is already open."
  exit 0
fi
git checkout --quiet -b "$BRANCH"

# 5. Reasoned tier: headless claude applies the narrative reconciliation, runs the
#    guardian, and opens a PR for review. It never merges (see the prompt).
if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN: would invoke '$CLAUDE_BIN $CLAUDE_FLAGS' on $BRANCH with the reconcile prompt."
  exit 0
fi

if ! command -v "$CLAUDE_BIN" >/dev/null 2>&1; then
  log "ERROR: '$CLAUDE_BIN' not found — draft is at .archetype/reconciliation/PENDING.md for manual /reconcile-state."
  exit 1
fi

log "Invoking headless claude on $BRANCH ..."
# shellcheck disable=SC2086
"$CLAUDE_BIN" -p "$(cat scripts/nightly/reconcile_state.prompt.md)" $CLAUDE_FLAGS >>"$LOG" 2>&1
log "Done — review the opened PR (nothing was merged)."
