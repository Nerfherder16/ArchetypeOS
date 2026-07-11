# AOS-EVOLVE-001 — Evolution Engine: decision staleness + re-evaluation

## Status

Proposed (2026-07-11). Wave C of RFC-0015. Unblocked, hermetic, no execution.

## Origin

Closes the Evolution stage of AOS-REVIEW-003 (name-only engine). Serves Article X (Continuous Evolution) and Article XVIII (decisions are hypotheses until re-validated), Roadmap Phase 7 ("monthly decision re-evaluation"). Today nothing revisits an approved decision as time/evidence changes.

## Verified Baseline

Confirmed on `main` @ `70dfccb`:

- `Decision` (`models.py:136-149`): `approved_at`, `evidence` (JSON list of typed pointers, e.g. `{"type":"council_review"|"research_note","id":...}`), status vocab `draft/needs_evidence/approved/rejected` on `AuditMixin.status`; `meta` (→ column "metadata") for advisory flags.
- `ResearchNote` (`models.py:152-168`): `question`, `created_at`, `job_id` (uniq).
- `now_utc()` in `models.py`.

## In-Scope Files

- `packages/aos_core/aos_core/services/evolution.py` (new):
  - `find_stale_decisions(db, *, project_id=None, max_age_days=90, now=None) -> list[dict]` — deterministic (inject `now` for tests). Returns staleness records `{decision_id, title, reason, age_days}` for **approved** decisions that are either (a) older than `max_age_days` by `approved_at`, or (b) evidence-superseded: an evidence pointer to a `ResearchNote` for which a NEWER `ResearchNote` on the same `question` now exists. Reason string documents which.
  - `reevaluate_decision(db, *, decision_id, reason=None, now=None) -> Decision` — advisory flag only (Article IX): sets `meta["reevaluation_requested_at"]`/`meta["stale_reason"]`; does NOT change status or delete. 404 if missing. Idempotent (re-flag updates the timestamp, no duplication).
- `apps/api/app/routes/decisions.py` — `GET /projects/{project_id}/decisions/stale?max_age_days=` and `POST /decisions/{decision_id}/reevaluate`. Update the frozen route inventory.
- `apps/api/tests/test_evolution.py` (new).

## Out-of-Scope

- No scheduled sweep job in this slice (a `job_type="evolution_sweep"` on the existing scheduler is a documented follow-up) — keep it synchronous + hermetic.
- No status mutation / auto-rejection of stale decisions (advisory only).
- No migration (reuses existing tables + `meta`).

## Acceptance Criteria

- An approved decision with `approved_at` older than `max_age_days` is reported stale with an age reason — evidence: `test_find_stale_by_age`.
- A decision whose evidence note is superseded by a newer note on the same question is reported stale with a supersession reason — evidence: `test_find_stale_by_superseded_evidence`.
- A fresh, recently-approved decision is NOT reported — evidence: `test_fresh_decision_not_stale`.
- Non-approved (draft/needs_evidence) decisions are never reported — evidence: `test_only_approved_considered`.
- `reevaluate_decision` sets the advisory meta flags without changing status; idempotent — evidence: `test_reevaluate_flags_advisory`.
- Routes: `GET .../decisions/stale`, `POST .../reevaluate` (404 missing) — evidence: route tests. Route inventory updated. Full suite green; ruff clean. Deterministic via injected `now`.

## Verification Plan

Level 2 (hermetic tests, injected clock). Builder ≠ verifier: Sonnet builds; Opus reviews the supersession logic (same-question newer-note detection) and confirms advisory-only (no status mutation).

## Suggested Delegation

Sonnet subagent; Opus reviews.

## Board Linkage

Branch: designated session branch.
