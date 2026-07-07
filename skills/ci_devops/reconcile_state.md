# Skill: Reconcile State (doc-staleness self-heal)

## Purpose

Close the doc-staleness loop from **detect** to **correct** (AOS-SELFHEAL-001, Article XX). `tools/doc_staleness.py` (AOS-20) detects when the state docs lag reality; this skill applies the correction it drafts, so drift is fixed rather than only flagged. It is the judgment half that the deterministic `--fix` cannot safely do (rewriting human narrative prose).

## Owner

CI / DevOps Agent (or the reconciliation-owning Orchestrator).

## Inputs

- `tools/doc_staleness.py` findings and the generated draft `.archetype/reconciliation/PENDING.md`
- `git log` (the merged PRs since the newest one the state docs reference)
- `docs/CURRENT_STATE.md`, `docs/RECENT_CHANGES.md`, `.archetype/roadmap.md`

## Steps

1. Run `python3 tools/doc_staleness.py --fix`. If it reports FRESH, stop — nothing to do.
2. Read the draft at `.archetype/reconciliation/PENDING.md` (the deterministic list of PRs merged beyond what the docs reference, with provenance).
3. For each listed PR, gather the substance (title, one-line summary) from `gh pr view <n>` or the PR's own reconciliation notes, and update:
   - `docs/RECENT_CHANGES.md`: a dated entry (or fold the PRs into the newest entry).
   - `docs/CURRENT_STATE.md`: the "Current sprint" / status line so the newest-referenced PR matches git (this is the single-writer reconciliation line — do it only as the reconciliation owner).
   - `.archetype/roadmap.md`: only if the "Current phase" is genuinely stale (a roadmap-phase HARD finding).
4. Never fabricate: every reconciled claim must trace to a merged PR / its notes (Article XII — do not just bump a watermark to silence the detector).
5. Re-run `python3 tools/doc_staleness.py`; confirm the verdict is FRESH (or only SOFT within the reconciliation window). Delete `.archetype/reconciliation/PENDING.md`.
6. Commit the state-doc reconciliation (union-merge-safe files; LES-026).

## Triggers

- The `post-merge` git hook (`scripts/hooks/post-merge`, installed via `scripts/install-hooks.sh`) regenerates the draft whenever you pull a `main` that is ahead of the state docs.
- The PR Guardian's non-blocking `doc-staleness` WARN on any PR whose base has drifted.
- **CI-on-main** (AOS-SELFHEAL-002): `.github/workflows/doc-staleness-reconcile.yml` runs `--fix` on every merge and surfaces the draft in a single idempotent `doc-staleness` tracking issue (auto-closed once reconciled). The *detect + draft* half, no human in the loop.
- **Nightly automation** (AOS-SELFHEAL-002b) — the *correct* half. See below.
- Manual: run this skill after a batch of merges.

## Nightly automation (headless)

The reconciliation narrative is applied unattended by a nightly routine that
**opens a PR for human review and never merges**.

- **Prompt (source of truth):** `scripts/nightly/reconcile_state.prompt.md` — the
  self-contained contract a headless `claude -p` follows (apply narrative → re-run
  the detector to FRESH → guardian → open PR). It edits only
  `docs/RECENT_CHANGES.md` (union-safe append), the `docs/CURRENT_STATE.md`
  PR-watermark, and (if a roadmap-phase HARD fired) `.archetype/roadmap.md`. It
  deliberately does **not** touch the "Current sprint" line or `docs/HANDOFF.md` —
  a live Orchestrator owns those (cross-session single-writer discipline).
- **Local-cron path:** `scripts/nightly/reconcile_state.sh` — a deterministic gate
  (sync `main` → run the detector → act only on real drift → one fresh branch per
  day → invoke the prompt). Refuses to run over a dirty tree and skips if today's
  reconcile branch already exists. `DRY_RUN=1` for a detect-only dress rehearsal.
- **Cloud path:** register the prompt as a `/schedule` routine — see
  `docs/runbooks/nightly-routines.md`.

The loop closes on itself: the routine's PR, once a human merges it, is the merge
that makes the CI detector see FRESH and **auto-close** the `doc-staleness` issue.

## Non-goals

- Auto-editing prose without review (drafts are generated; a human/agent applies them).
- Silencing the detector without an actual reconciliation.
