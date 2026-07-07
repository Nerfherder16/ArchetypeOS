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
- Manual: run this skill after a batch of merges.

## Non-goals

- Auto-editing prose without review (drafts are generated; a human/agent applies them).
- Silencing the detector without an actual reconciliation.
