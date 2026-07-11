# AOS-STATE-SEMANTIC-001 — Derive Execution State; CI Rejects Stale Semantic Fields

## Status

Proposed

## Origin

Closes AOS-REVIEW-002 finding P1-4 (state docs syntactically fresh but semantically stale), verified in [[LES-033]]. Recurrence of the *semantic* half [[LES-L09]] (AOS-STATE-RECON-001) did not close — that package auto-derived the watermark (branch/PR-lag drift), not the human narrative (truth drift). Independent, low-risk.

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `docs/CURRENT_STATE.md` — watermark `#183` is numerically current, but the Objective (:19-21) still names AOS-STATE-RECON-001 / VOICE-PROJECT-001 / CONTRACT-001 as the "next" sequence; Open Decisions (:58-60) mark Node/Connector/Authority "Proposed" though `services/{nodes,connectors,authority}.py` + routes exist.
- `docs/ACTIVE_WORK.md` — 787 lines; many merged items still `Status: In Review` (e.g. :23, :49, :79, :85, :92, :100, :109-131); the AOS-REVIEW-001 backlog (:28) still "Proposed" though registries are coded.
- `origin/main` HEAD is `chore(state): refresh canonical fields [skip ci]` — one of 12 `[skip ci]` state commits in the last 30; the state-canonical-refresh workflow pushes directly to main.
- `tools/doc_staleness.py` exists (AOS-20) and checks the canonical block; it does NOT check semantic labels (a shipped module marked "Proposed").

## In-Scope Files

- `tools/doc_staleness.py` — add a `semantic-label-stale` check: a module that exists under `packages/aos_core/aos_core/services/` or `apps/api/app/routes/` while the state docs mark its package "Proposed"/"not yet in code" is a HARD finding in the originating PR.
- `docs/CURRENT_STATE.md`, `docs/ACTIVE_WORK.md` — correct the Node/Connector/Authority labels (they are implemented per LES-033); move merged items out of the board.
- Optionally introduce a derived execution view generated from `.archetype/work/*` `Status:` fields rather than hand-maintained board prose (design note; may be a follow-up slice).
- `tools/pr_guardian.py` — surface the new `doc_staleness` semantic finding as a WARN/BLOCK per existing convention.
- Tests: `apps/api/tests/test_doc_staleness.py` (new cases: shipped-module-marked-proposed → HARD; correct labels → FRESH).
- Lesson (closes the semantic half of LES-L09), this spec.

## Out-of-Scope

- Removing the `[skip ci]` watermark workflow entirely — the recommendation is to *compute* the watermark in the dashboard/staleness command, but ripping out the existing mechanism is a separate decision; this package makes the *semantic* fields honest and CI-checked.
- Rewriting the board into a database (deferred; the derived-view note may seed a later package).

## Acceptance Criteria

- A shipped module marked "Proposed" in state docs fails the staleness check — evidence: `test_semantic_label_stale_blocks` (fixture: `nodes.py` exists + docs say Proposed → HARD).
- Correct labels pass — evidence: `test_semantic_labels_fresh`.
- Node/Connector/Authority relabeled to their real state — evidence: the docs diff in this PR + the check passing on it.
- Merged items no longer sit in the board as "In Review" — evidence: board diff; count of "In Review" items drops to only genuinely-open work.

## Verification Plan

Level 2: pytest over the doc_staleness tests; run `tools/doc_staleness.py` on the repo → the semantic check fires on the current stale labels, then passes after the doc fix. Level 3: CI. One PR, Manual Merge Gate.

## Suggested Delegation

Sonnet builder (detector + doc reconciliation are mechanical, follow `doc_staleness.py` conventions). Orchestrator: confirm the detector cannot false-positive on legitimately-proposed packages, review the doc diff for accuracy against code, lesson, PR, gate.

## Board Linkage

- Plane: unassigned (Sprint "Make execution trustworthy" — quick win)
- Branch: TBD, cut off latest main per `aos-ship-pr`
