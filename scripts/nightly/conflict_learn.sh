#!/usr/bin/env bash
#
# AOS-SELFHEAL-003 — conflict self-learn nightly (local-cron path).
#
# Deterministic gate for the "learn from the day's merge friction" loop. Runs the
# harvester (tools/conflict_digest.py); only if there is real signal does it wake
# a headless `claude` to distill RECURRING patterns into an LES-L## draft lesson
# and OPEN a PR for review. It never merges and never edits over a dirty tree.
#
# Cloud path: the same logic runs as a `/schedule` routine whose prompt is
# scripts/nightly/conflict_learn.prompt.md — see skills/ci_devops/conflict_distill.md.
#
# Env:
#   CLAUDE_BIN    claude executable (default: claude)
#   CLAUDE_FLAGS  flags for headless run (default: --permission-mode acceptEdits)
#   SINCE         git reflog window (default: midnight — today's session)
#   DRY_RUN=1     harvest + log only; do not invoke claude
#
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$REPO_ROOT"

LOG=".archetype/conflicts/nightly.log"
mkdir -p "$(dirname "$LOG")"
log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG" >&2; }
# AOS-SELFHEAL observability: post a heartbeat so a missed run is visible.
source "$(dirname "${BASH_SOURCE[0]}")/heartbeat.sh"

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_FLAGS="${CLAUDE_FLAGS:---permission-mode acceptEdits --model sonnet}"
SINCE="${SINCE:-midnight}"
DRY_RUN="${DRY_RUN:-0}"

# 1. Never work over uncommitted local changes.
if [ -n "$(git status --porcelain)" ]; then
  log "SKIP: working tree dirty — refusing to run over local changes."
  exit 0
fi

# 2. Sync main (so the digest + any lesson PR are cut from latest).
git fetch --quiet origin main
git checkout --quiet main
git pull --quiet --ff-only origin main

# 3. Deterministic gate: harvest the day's conflict friction.
DAY="$(git log -1 --format=%cs)"
OUT=".archetype/conflicts/${DAY}.md"
SIGNAL="$(python3 tools/conflict_digest.py --since "$SINCE" --out "$OUT" \
  --json ".archetype/conflicts/${DAY}.json" 2>>"$LOG" | sed -n 's/^signal=//p')"
if [ "$SIGNAL" != "true" ]; then
  log "QUIET: no conflict or merge friction today — nothing to distill."
  aos_heartbeat conflict clean "$DAY"
  exit 0
fi
log "SIGNAL: friction recorded — digest at $OUT."

# 4. One fresh branch per day; skip if today's lesson PR already exists.
BRANCH="laptop/nightly-conflict-learn-$(date -u +%Y%m%d)"
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  log "SKIP: $BRANCH already on origin — today's conflict-learn PR is already open."
  exit 0
fi
git checkout --quiet -b "$BRANCH"

# 5. Reasoned tier: headless claude distills RECURRING patterns into an LES-L##
#    draft lesson and opens a PR for review. It never merges (see the prompt), and
#    writes nothing if the friction is one-off noise (Article XII).
if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN: would invoke '$CLAUDE_BIN $CLAUDE_FLAGS' on $BRANCH with the distill prompt."
  exit 0
fi

if ! command -v "$CLAUDE_BIN" >/dev/null 2>&1; then
  log "ERROR: '$CLAUDE_BIN' not found — digest is at $OUT for manual distillation."
  exit 1
fi

log "Invoking headless claude on $BRANCH ..."
# shellcheck disable=SC2086
"$CLAUDE_BIN" -p "$(cat scripts/nightly/conflict_learn.prompt.md)" $CLAUDE_FLAGS >>"$LOG" 2>&1
log "Done — review the opened PR if a lesson was proposed (nothing was merged)."
