#!/usr/bin/env bash
#
# AOS-SELFHEAL-006 — session-pain self-learn nightly (local-cron path).
#
# The fourth self-learn probe (sibling of conflict/toil/coherence). Runs the
# session-pain harvester (tools/session_pain_digest.py) over the day's Claude Code
# transcripts; only if the day carried real friction — repeated tool errors, file
# thrash, command-retry loops, or explicit user corrections — does it wake a
# headless `claude` to propose a LESSON, skill, or fix that removes the pain, and
# OPEN a PR for review. It never merges and never edits over a dirty tree.
#
# Env:
#   CLAUDE_BIN    claude executable (default: claude)
#   CLAUDE_FLAGS  flags for headless run (default: --permission-mode acceptEdits)
#   MIN_EDITS     min edits to one file to count as thrash (default: 3)
#   MIN_RETRIES   min repeats of one command to count as a retry loop (default: 3)
#   DRY_RUN=1     harvest + log only; do not invoke claude
#
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$REPO_ROOT"

LOG=".archetype/session-pain/nightly.log"
mkdir -p "$(dirname "$LOG")"
log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG" >&2; }

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_FLAGS="${CLAUDE_FLAGS:---permission-mode acceptEdits}"
MIN_EDITS="${MIN_EDITS:-3}"
MIN_RETRIES="${MIN_RETRIES:-3}"
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

# 3. Deterministic gate: harvest the day's session pain from the transcripts.
DAY="$(git log -1 --format=%cs)"
OUT=".archetype/session-pain/${DAY}.md"
SIGNAL="$(python3 tools/session_pain_digest.py --min-edits "$MIN_EDITS" --min-retries "$MIN_RETRIES" \
  --out "$OUT" --json ".archetype/session-pain/${DAY}.json" 2>>"$LOG" | sed -n 's/^signal=//p')"
if [ "$SIGNAL" != "true" ]; then
  log "QUIET: no recurring tool errors, thrash, loops, or corrections today."
  exit 0
fi
log "SIGNAL: session pain recorded — digest at $OUT."

# 4. One fresh branch per day; skip if today's session-pain PR already exists.
BRANCH="laptop/nightly-session-pain-learn-$(date -u +%Y%m%d)"
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  log "SKIP: $BRANCH already on origin — today's session-pain PR is already open."
  exit 0
fi
git checkout --quiet -b "$BRANCH"

# 5. Reasoned tier: headless claude turns a genuine recurring pain into a lesson,
#    skill, or fix and opens a PR for review. It never merges (see the prompt),
#    and writes nothing if the "pain" is noise or already captured (Article XII).
if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN: would invoke '$CLAUDE_BIN $CLAUDE_FLAGS' on $BRANCH with the session-pain prompt."
  exit 0
fi

if ! command -v "$CLAUDE_BIN" >/dev/null 2>&1; then
  log "ERROR: '$CLAUDE_BIN' not found — digest is at $OUT for manual review."
  exit 1
fi

log "Invoking headless claude on $BRANCH ..."
# shellcheck disable=SC2086
"$CLAUDE_BIN" -p "$(cat scripts/nightly/session_pain_learn.prompt.md)" $CLAUDE_FLAGS >>"$LOG" 2>&1
log "Done — review the opened PR if a fix was proposed (nothing was merged)."
