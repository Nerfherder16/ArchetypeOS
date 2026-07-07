# Runbook: Nightly self-heal routines

ArchetypeOS runs unattended nightly routines that keep the repo honest with
itself (Article XX — "ArchetypeOS Must Improve Itself"). Each routine has a
**deterministic gate** (cheap, runs every night) and only wakes a headless
`claude` when the gate finds real signal. **No routine ever merges** — the human
gate stays on the morning review of an opened PR.

There are two runners; pick whichever fits your setup.

## Runner A — `/schedule` cloud routine (recommended)

Register the routine's prompt as a scheduled cloud agent:

```
/schedule create --name "aos-reconcile-nightly" \
  --cron "17 7 * * *" \
  --prompt-file scripts/nightly/reconcile_state.prompt.md
```

The cloud agent needs permission to run `git`, `gh`, `python3`, and to edit
files — grant those in the routine's permission config. It opens a PR titled
`AOS-RECONCILE-<date>: nightly state-doc reconciliation`; you review + merge.

## Runner B — local cron (headless `claude -p`)

For a machine that has the repo cloned and the `claude` CLI on PATH:

```
17 7 * * *  /home/nerfherder/Dev/ArchetypeOS/scripts/nightly/reconcile_state.sh >> /home/nerfherder/Dev/ArchetypeOS/.archetype/reconciliation/nightly.log 2>&1
```

Unattended runs need `claude` to be allowed to call `git`/`gh` without a prompt.
Set that in the routine's permission config, or export
`CLAUDE_FLAGS="--permission-mode acceptEdits"` (the default) plus a settings
allowlist for `Bash(git*)` and `Bash(gh*)`. `DRY_RUN=1` does a detect-only dress
rehearsal (no branch, no claude).

## Routine: reconcile-state (AOS-SELFHEAL-002b)

**Gate:** `python3 tools/doc_staleness.py --fix` — writes
`.archetype/reconciliation/PENDING.md` only when the state docs lag git.
**Action on drift:** headless `claude` follows
`scripts/nightly/reconcile_state.prompt.md` — applies the narrative
reconciliation (union-safe `RECENT_CHANGES.md` append + `CURRENT_STATE.md`
watermark; never the "Current sprint" line or `HANDOFF.md`), re-runs the detector
to FRESH, runs the PR Guardian, and opens a PR.
**Self-closing:** merging that PR is the merge that makes the CI detector
(`.github/workflows/doc-staleness-reconcile.yml`) see FRESH and auto-close the
`doc-staleness` tracking issue.

## Cadence

Per `docs/NIGHTLY_SELF_LEARNING_LOOP.md`: nightly local review, weekly portfolio
review, monthly evolution review. Stagger the cron minute off `:00`/`:30` so
parallel fleets don't all hit the API at once.
