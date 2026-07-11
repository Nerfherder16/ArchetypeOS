# AOS-AUTHORITY-ENVELOPE-001 — Mandatory Execution Envelope Around High-Impact Actions

## Status

Proposed

## Origin

Closes AOS-REVIEW-002 finding P0-6 (authority is an advisory evaluator, not a mandatory execution boundary), verified in [[LES-033]]. Wave 3. Depends on AOS-JOBS-RELIABILITY-001 giving a single atomic origination chokepoint to wrap.

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `packages/aos_core/aos_core/services/authority.py:89-102` — `requires_approval()` is a pure function; `evaluate()` (:105-129) wraps it with a reason.
- `apps/api/app/routes/authority.py` — three informational routes (`GET /authority/action-classes`, `POST /authority/evaluate`, `GET /authority/pending`); `POST /authority/evaluate` only reports, gates nothing.
- The only non-doc/non-test callers of the authority engine are the service itself and `routes/authority.py`. `jobs.py`, `worker.py`, and the research/distillation/repositories/nodes/connectors services make ZERO authority calls (grep of `worker.py` for `authority|requires_approval|ActionClass` → no matches).
- A caller can `POST /jobs` and the worker executes with no authority consultation; the engine's "cannot be silently bypassed" docstring (`authority.py:7-8`) is aspirational.

## In-Scope Files

- `packages/aos_core/aos_core/services/authority.py` — add the execution envelope: `ActionRequest` (id, action_class, actor, agent, project, target, sensitivity, requested_capability, payload_digest, policy_decision, approval_state, execution_state) and `request_action(...)` / `authorize_action(...)` / `execute_authorized_action(...)`.
- `packages/aos_core/aos_core/models.py` — `ActionRequest` table.
- `packages/aos_core/aos_core/services/jobs.py` — high-impact origination goes through `request_action`; `enqueue_job` requires an authorized `ActionRequest` or an internal capability token for high-impact classes.
- `apps/worker/app/worker.py` — side-effecting handlers (repo write, deploy, destructive, sensitive egress) execute only under an authorized envelope / internal token.
- `apps/api/app/routes/` — job/research/repo-write/deploy routes create an `ActionRequest`; pending actions surface for operator approval.
- `apps/api/alembic/versions/0021_action_request.py` (new).
- Tests: `apps/api/tests/test_authority_envelope.py` (a high-impact action with no authorized `ActionRequest` is rejected at the boundary; capture-only actions pass; approval flips execution_state). Route inventory updated (LES-L05).

## Out-of-Scope

- Connector egress *policy* enforcement mechanics (AOS-CONNECTOR-RUNTIME-001 owns the connector policy surface; this package consults it for egress actions).
- Human operator RBAC (Track F).
- Re-classifying every existing low-impact action — scope to the high-impact classes (write, deploy, destructive, sensitive egress) first; capture-only stays unblocked.

## Acceptance Criteria

- A high-impact action with no authorized `ActionRequest` is rejected at the execution boundary — evidence: `test_high_impact_requires_authorized_envelope` (direct `enqueue_job` of a write-class job without an envelope → rejected).
- The authority check is structural, not voluntary — evidence: `test_no_bypass_path` (the execution service refuses without an envelope/internal token; grep-style test that the write path calls `authorize_action`).
- Approval flips execution state and lets the action proceed — evidence: `test_approval_enables_execution`.
- Capture-only / low-impact actions are not gated — evidence: `test_capture_only_unblocked`.
- Route inventory + guardian updated — evidence: `test_route_inventory`.

## Verification Plan

Level 2 + full API/worker suites. Adversarial review: enumerate every high-impact execution path and prove each consults `authorize_action` (the exact gap LES-033 documents). Level 3: CI + compose-smoke. One PR (or a slice per action class), Manual Merge Gate. Builder ≠ verifier.

## Suggested Delegation

Opus design of the envelope + the chokepoint placement (subtle: it must be unavoidable, not a second door); Sonnet builds the `ActionRequest` model + routes. Orchestrator: adversarial "find the bypass" review, lesson, PR, gate.

## Board Linkage

- Plane: unassigned (Sprint "Unify governance")
- Branch: TBD, cut off latest main after AOS-JOBS-RELIABILITY-001 merges
