# AOS-SELFHEAL-001 — Close the doc-staleness loop: detect → correct

- Status: In Review (layers 1-2 built: `--fix` + hook + skill)
- Owner: laptop session
- Branch: `laptop/aos-selfheal-doc-loop` (fresh, from `origin/main` @ `8a7fd6a`)
- Motivation: Operator critique (2026-07-06) — AOS-20 detects doc drift but remediation is manual and deferred every time (a smoke alarm with no sprinkler). This violates Article XX ("ArchetypeOS Must Improve Itself"). Close the loop.

## Principle (avoid gaming the metric)

Per Article XII, `--fix` must NOT silence the detector by fiat (e.g. bumping a watermark). It generates the **correction content** deterministically from ground truth; a human/LLM applies it. Detection → auto-drafted correction → approve. The alarm only clears when the docs are actually reconciled.

## Design (three layers, this package ships layers 1-2)

1. **`tools/doc_staleness.py --fix` (deterministic draft generator).** For each HARD finding, emit a reconciliation DRAFT to `.archetype/reconciliation/PENDING.md` (machine-owned):
   - `state-docs-pr-lag`: from `git log`, list every merged PR since the newest one referenced in the state docs (number + title), formatted as a ready-to-paste RECENT_CHANGES/CURRENT_STATE reconciliation block. Does not edit prose itself.
   - `roadmap-phase-stale`: emit the current phase text + the completion markers found, flagged for human rewrite (narrative — never auto-rewritten).
   Reuses `evaluate()`/`extract_merged_prs()`/`check_state_pr_lag()`. Hermetic (git via subprocess, tolerant). Exit non-zero while HARD drift stands (drives the hook).
2. **`/reconcile-state` skill.** Reads `PENDING.md` + git, updates the narrative state docs (CURRENT_STATE sprint line, RECENT_CHANGES) with the merged-PR summary for human approval, then clears `PENDING.md`. The judgment half.
3. **A committed git `pre-push` hook** (`scripts/hooks/pre-push` + `scripts/install-hooks.sh` setting `core.hooksPath`, or a CI post-merge job) that runs `doc_staleness` and WARNs (non-blocking) on HARD drift, nudging `/reconcile-state`. Repo-owned + portable (not personal `settings.json`). A Claude Code Stop hook for the local session is an optional follow-up.

Deferred (follow-ups): wiring findings into the nightly self-learning loop; a Stop hook; auto-opening a reconciliation PR from CI.

## In-Scope (this package)
- `tools/doc_staleness.py` (`--fix` + draft generator), `apps/api/tests/test_doc_staleness.py` (TDD the draft generation, hermetic via fixtures).
- `scripts/hooks/pre-push` + `scripts/install-hooks.sh` (portable hook install).
- `skills/reconcile-state/` (the skill), `docs/CAPABILITY_MAP.md` Layer 8 note, spec + state docs + a lesson (closes the "detect-only" gap).

## Out-of-Scope
- Auto-editing human narrative prose (drafts only; human/LLM applies).
- Nightly-loop wiring + CI reconciliation-PR automation (follow-ups).
- Anything outside the doc-staleness subsystem.

## Acceptance Criteria (assertions)
1. `doc_staleness.py --fix` on a tree with HARD PR-lag writes `.archetype/reconciliation/PENDING.md` containing the merged-PRs-since-newest-referenced block, derived from git; a fresh tree writes nothing. — evidence: hermetic tests with injected git-log/state fixtures.
2. `--fix` never edits CURRENT_STATE/RECENT_CHANGES prose (draft-only). — evidence: test asserts those files unchanged.
3. The pre-push hook runs the detector and warns (non-blocking) on HARD drift. — evidence: hook script + a test/manual run.
4. `/reconcile-state` skill documented + invokable. — evidence: skill file.
5. Full gate green; guardian PASS. — evidence: CI.

## Verification Plan
- TDD the `--fix` draft generator (pure function over injected git-log + state text → draft string).
- Level 2: run `--fix` against a synthetic stale tree; confirm the draft + no prose edits. ruff/compileall/pytest.
- Level 3: CI green → Manual Merge Gate.
