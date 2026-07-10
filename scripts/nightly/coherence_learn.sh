#!/usr/bin/env bash
#
# AOS-SELFHEAL-005 — contract-coherence self-learn nightly (local-cron path).
#
# The third self-learn probe (sibling of conflict_learn.sh and toil_learn.sh).
# Runs the coherence probe (tools/coherence_probe.py); only if a frontend type has
# drifted thinner than its backend schema (contract-lag) does it wake a headless
# `claude` to widen the frontend type(s) to match and OPEN a PR for review. It
# never merges and never edits over a dirty tree.
#
# Env:
#   CLAUDE_BIN    claude executable (default: claude)
#   CLAUDE_FLAGS  flags for headless run (default: --permission-mode acceptEdits)
#   DRY_RUN=1     harvest + log only; do not invoke claude
#
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$REPO_ROOT"

LOG=".archetype/coherence/nightly.log"
mkdir -p "$(dirname "$LOG")"
log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG" >&2; }
# AOS-SELFHEAL observability: post a heartbeat so a missed run is visible.
source "$(dirname "${BASH_SOURCE[0]}")/heartbeat.sh"

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_FLAGS="${CLAUDE_FLAGS:---permission-mode acceptEdits --model sonnet}"
DRY_RUN="${DRY_RUN:-0}"

# 1. Never work over uncommitted local changes.
if [ -n "$(git status --porcelain)" ]; then
  log "SKIP: working tree dirty — refusing to run over local changes."
  exit 0
fi

# 2. Sync main (so the digest + any fix PR are cut from latest).
git fetch --quiet origin main
git checkout --quiet main
git pull --quiet --ff-only origin main

# 3. Deterministic gate: detect frontend/backend contract-lag.
DAY="$(git log -1 --format=%cs)"
OUT=".archetype/coherence/${DAY}.md"
SIGNAL="$(python3 tools/coherence_probe.py --out "$OUT" \
  --json ".archetype/coherence/${DAY}.json" 2>>"$LOG" | sed -n 's/^signal=//p')"
if [ "$SIGNAL" != "true" ]; then
  log "QUIET: every mirrored frontend type covers its backend schema — no drift."
  aos_heartbeat coherence clean "$DAY"
  exit 0
fi
log "SIGNAL: contract-lag recorded — digest at $OUT."

# 4. One fresh branch per day; skip if today's coherence PR already exists.
BRANCH="laptop/nightly-coherence-learn-$(date -u +%Y%m%d)"
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  log "SKIP: $BRANCH already on origin — today's coherence PR is already open."
  exit 0
fi
git checkout --quiet -b "$BRANCH"

# 5. Reasoned tier: headless claude widens the drifted frontend type(s) to match
#    the backend schema and opens a PR for review. It never merges (see the
#    prompt), and writes nothing if the "drift" is an intentional omission.
if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN: would invoke '$CLAUDE_BIN $CLAUDE_FLAGS' on $BRANCH with the coherence prompt."
  exit 0
fi

if ! command -v "$CLAUDE_BIN" >/dev/null 2>&1; then
  log "ERROR: '$CLAUDE_BIN' not found — digest is at $OUT for manual review."
  exit 1
fi

log "Invoking headless claude on $BRANCH ..."
# shellcheck disable=SC2086
"$CLAUDE_BIN" -p "$(cat scripts/nightly/coherence_learn.prompt.md)" $CLAUDE_FLAGS >>"$LOG" 2>&1
log "Done — review the opened PR if a fix was proposed (nothing was merged)."
