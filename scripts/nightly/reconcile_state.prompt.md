You are the ArchetypeOS **nightly reconciliation routine** (AOS-SELFHEAL-002b),
running unattended. The deterministic detector has already confirmed the state
docs have drifted from git and written a draft to
`.archetype/reconciliation/PENDING.md`. Your job is the narrative half the
deterministic `--fix` cannot safely do, then to open a PR for a human to merge.

You are on a fresh branch cut from an up-to-date `main`. Do NOT merge anything.

## Steps

1. Read `skills/ci_devops/reconcile_state.md` and follow its reconciliation
   procedure. Read `.archetype/reconciliation/PENDING.md` for the deterministic
   list of merged PRs the docs do not yet cover.
2. For each listed PR, gather substance from `gh pr view <n>` (title + the PR's
   own reconciliation notes / body). Never invent — every reconciled claim must
   trace to a merged PR (Article XII: do not just bump a watermark to silence
   the detector).
3. Apply the reconciliation to the state docs:
   - `docs/RECENT_CHANGES.md`: a dated entry (or fold the PRs into the newest
     entry). This file is union-merge-safe — append, do not rewrite history.
   - `docs/CURRENT_STATE.md`: update the "referenced through PR #N" watermark so
     it matches git. **Do NOT rewrite the "Current sprint" narrative line or
     `docs/HANDOFF.md`** — a live Orchestrator session owns those; touching them
     risks a cross-session conflict. Reconcile the watermark and the merged-PR
     list only.
   - `.archetype/roadmap.md`: only if a genuine roadmap-phase HARD finding fired.
4. Re-run `python3 tools/doc_staleness.py`. Confirm the verdict is FRESH (or only
   ADVISORY within the reconciliation window). Then delete
   `.archetype/reconciliation/PENDING.md`.
5. Commit the reconciliation (conventional commit, e.g.
   `docs(state): nightly reconciliation of PRs #N–#M`).
6. Write the PR body to a file with the required PR Guardian verification
   metadata as plain `Field: value` lines at the start of a line:
   `Verification Status`, `Verification Level`, `Verification Method`,
   `Evidence`, `Limitations`, `Required Next Verifier`. Use
   `Verification Status: Verified` and `Verification Level: Level 1` (doc-only
   reconciliation), Evidence = the re-run FRESH verdict.
7. Run `python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file <body>`.
   It must return PASS or PASS_WITH_WARNINGS. If it BLOCKs, fix the cause (do not
   use an override token).
8. Push the branch and open a PR with `gh pr create` (base `main`). **Do not
   merge.** Title: `AOS-RECONCILE-<date>: nightly state-doc reconciliation`.

## Abort conditions (stop and do nothing destructive)

- If `git status` is not clean at the start, stop — do not reconcile over local work.
- If the PENDING draft is empty or the detector reports FRESH, stop — nothing to do.
- If reconciliation would require editing the "Current sprint" line or HANDOFF,
  leave those untouched and note it in the PR body.
- If the guardian BLOCKs for a reason you cannot safely resolve, push the branch
  and open the PR as a **draft** with the guardian output in the body, then stop.

The next merge to `main` will auto-close the `doc-staleness` tracking issue
(AOS-SELFHEAL-002). You detect + draft deterministically; this routine corrects.
