#!/usr/bin/env bash
#
# AOS-SELFHEAL-004 — toil self-learn nightly (local-cron path).
#
# The second self-learn probe (sibling of conflict_learn.sh). Runs the toil
# harvester (tools/toil_digest.py); only if a multi-step git ritual recurred often
# enough does it wake a headless `claude` to propose a SKILL or SCRIPT that
# captures the ritual, and OPEN a PR for review. It never merges and never edits
# over a dirty tree.
#
# Env:
#   CLAUDE_BIN    claude executable (default: claude)
#   CLAUDE_FLAGS  flags for headless run (default: --permission-mode acceptEdits)
#   SINCE         git reflog window (default: midnight — today's session)
#   MIN_COUNT     min repetitions for a ritual to count as toil (default: 3)
#   DRY_RUN=1     harvest + log only; do not invoke claude
#
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$REPO_ROOT"

LOG=".archetype/toil/nightly.log"
mkdir -p "$(dirname "$LOG")"
log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG" >&2; }
# AOS-SELFHEAL observability: post a heartbeat so a missed run is visible.
source "$(dirname "${BASH_SOURCE[0]}")/heartbeat.sh"

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_FLAGS="${CLAUDE_FLAGS:---permission-mode acceptEdits --model sonnet}"
SINCE="${SINCE:-midnight}"
MIN_COUNT="${MIN_COUNT:-3}"
DRY_RUN="${DRY_RUN:-0}"

# 1. Never work over uncommitted local changes.
if [ -n "$(git status --porcelain)" ]; then
  log "SKIP: working tree dirty — refusing to run over local changes."
  exit 0
fi

# 2. Sync main (so the digest + any skill PR are cut from latest).
git fetch --quiet origin main
git checkout --quiet main
git pull --quiet --ff-only origin main

# 3. Deterministic gate: harvest the day's recurring rituals.
DAY="$(git log -1 --format=%cs)"
OUT=".archetype/toil/${DAY}.md"
SIGNAL="$(python3 tools/toil_digest.py --since "$SINCE" --min-count "$MIN_COUNT" --out "$OUT" \
  --json ".archetype/toil/${DAY}.json" 2>>"$LOG" | sed -n 's/^signal=//p')"
if [ "$SIGNAL" != "true" ]; then
  log "QUIET: no recurring ritual today — nothing to automate."
  aos_heartbeat toil clean "$DAY"
  exit 0
fi
log "SIGNAL: recurring ritual(s) recorded — digest at $OUT."

# 4. One fresh branch per day; skip if today's toil PR already exists.
BRANCH="laptop/nightly-toil-learn-$(date -u +%Y%m%d)"
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  log "SKIP: $BRANCH already on origin — today's toil PR is already open."
  exit 0
fi
git checkout --quiet -b "$BRANCH"

# 5. Reasoned tier: headless claude proposes a skill/script capturing the ritual
#    and opens a PR for review. It never merges (see the prompt), and writes
#    nothing if the ritual is not a genuine, generalizable workflow (Article XII).
if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN: would invoke '$CLAUDE_BIN $CLAUDE_FLAGS' on $BRANCH with the distill prompt."
  exit 0
fi

if ! command -v "$CLAUDE_BIN" >/dev/null 2>&1; then
  log "ERROR: '$CLAUDE_BIN' not found — digest is at $OUT for manual review."
  exit 1
fi

log "Invoking headless claude on $BRANCH ..."
# shellcheck disable=SC2086
"$CLAUDE_BIN" -p "$(cat scripts/nightly/toil_learn.prompt.md)" $CLAUDE_FLAGS >>"$LOG" 2>&1
log "Done — review the opened PR if automation was proposed (nothing was merged)."
