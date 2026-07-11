# AOS-RESEARCH-COUNCIL-001 — Deep research run reaches the council

## Status

Proposed (2026-07-11). Wave A of RFC-0015 (Build Intelligence). Ready — no dependency.

## Origin

Closes AOS-REVIEW-003 seam #5 (deep research run → council data-type mismatch). Smallest diff / highest leverage in the re-centering backlog: it improves the evidence feeding every downstream decision.

## Verified Baseline

Confirmed by inspection of `main` @ `70dfccb`:

- `services/research_run.py:68 execute_research_run(db, plan, *, job_id=None) -> ResearchRun` writes **one `ResearchRun`** row (`:102-114`) and follow-up `ResearchPlan`s; it does **not** write a `ResearchNote`.
- `services/council.py:73-92 _select_research` reads exactly `ResearchNote` (latest 10) + `Decision` (latest 10). It does **not** read `ResearchRun`. So multi-phase research never becomes council evidence.
- `ResearchNote` (`models.py:152-168`) has `UniqueConstraint("job_id", name="uq_research_notes_job_id")`; fields `project_id, title, question, summary, sources, findings, freshness, confidence, job_id`.

## In-Scope Files

- `packages/aos_core/aos_core/services/research_run.py` — after persisting the `ResearchRun`, get-or-create one `ResearchNote` keyed on `job_id` (when `job_id` is provided), populated from the run: `question=plan.question`, `summary=<run synthesis>`, `sources`, `findings` (map from run findings), `confidence`, `freshness`. Get-or-create keeps it idempotent under redelivery and coexists with the `ResearchRun`'s own `job_id` uniqueness (different tables).
- `apps/api/tests/` (or `packages/aos_core` tests) — new hermetic test: running `execute_research_run` with a `job_id` produces a `ResearchNote` the council's `_select_research` then returns as evidence.

## Out-of-Scope

- No council-side change (it already reads `ResearchNote`).
- No migration (reuses `research_notes`).
- No change to the `ResearchRun` shape or the follow-up-plan behavior.

## Acceptance Criteria

- `execute_research_run(..., job_id="j1")` creates exactly one `ResearchNote` with `job_id="j1"` summarizing the run — evidence: `test_research_run_emits_research_note`.
- Re-running with the same `job_id` does not create a second note (get-or-create) — evidence: idempotency assertion in the same test.
- A council review after a research run includes the run's note in its evidence — evidence: `test_council_sees_research_run_note` asserting `_select_research` returns the note ref.
- When `job_id is None` (direct call, no job), behavior is unchanged (no note) — evidence: negative assertion.
- Full API/core suite green; ruff clean.

## Verification Plan

Level 2 (hermetic tests, sqlite). Builder ≠ verifier: Sonnet builds; Opus reviews the diff for the get-or-create race and the findings mapping.

## Suggested Delegation

Sonnet subagent (small mechanical service edit + test) in a dedicated worktree; Opus reviews.

## Board Linkage

Branch: `<session>/aos-research-council-001`. One PR.
