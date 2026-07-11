# AOS-WORKER-HANDLERS-001 — Handler Module Split + Richer HandlerSpec

## Status

Proposed

## Origin

Closes AOS-REVIEW-002 finding P1-1 (worker registry still centralizes every handler), verified in [[LES-033]]. Replaces/closes PR #179 (which proposed an unsafe `merge=union` on `worker.py`). Should land first or alongside AOS-JOBS-RELIABILITY-001 Slice 3 (which needs `HandlerSpec.idempotency_strategy`).

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `apps/worker/app/worker.py` — if/elif dispatch replaced by a `JOB_HANDLERS` dict (:138), but all handler imports (:12-19), functions (`_run_repository_scan`…`_run_test`, :68-118), and registrations (:121-126) are inline in this one file.
- `HandlerSpec` `worker.py:46-58` declares only `job_type`, `capability`, `sensitivity`, `run` — no timeout/retry/idempotency/execution-mode/result-schema. `sensitivity` is read only by `apps/worker/tests/test_worker.py:371`, never enforced.
- No `apps/worker/app/handlers/` package exists.
- PR #179 documents the `worker.py` merge-conflict hotspot; LES-026/LES-L03 establish that `merge=union` is safe only for append-only logs, never Python source.

## In-Scope Files

- `apps/worker/app/handlers/__init__.py`, `registry.py`, `repository_scan.py`, `project_digest.py`, `council_review.py`, `research.py`, `research_run.py`, `test.py` (new — one immutable `HandlerSpec` export each).
- `apps/worker/app/worker.py` — import the registry (known module list or entry points); remove inline handlers.
- `HandlerSpec` (moved to `handlers/registry.py`) — add `timeout: int`, `retry_policy`, `idempotency_strategy: str`, `result_schema` (optional).
- `apps/worker/tests/test_worker.py` + new `apps/worker/tests/test_handler_registry.py`.
- PR #179: close/replace; do NOT add `apps/worker/app/worker.py` to `.gitattributes merge=union`.
- Lesson (LES-026 cited), state docs, this spec.

## Out-of-Scope

- Implementing lease/outbox behavior (AOS-JOBS-RELIABILITY-001) — this package only carries the *declarations* (`idempotency_strategy`, `timeout`) those fields need; the enforcement lands there.
- Node capability routing (AOS-NODE-AGENT-001) — it consumes `HandlerSpec.capability`/`sensitivity`, added-value here is that the fields exist per-module.

## Acceptance Criteria

- Adding a job type touches only a new `handlers/*.py` + the registry list — evidence: `test_registry_discovers_all_specs` (registry lists the 6 job types from modules, not an inline block).
- `HandlerSpec` carries timeout/retry/idempotency/result-schema — evidence: `test_handler_spec_fields` asserts the new fields on every registered spec.
- Behavior unchanged — evidence: existing `apps/worker/tests` green; each handler produces the same result as before.
- `sensitivity`/`capability` still declared per handler — evidence: parametrized assertion over the registry.
- PR #179 closed/superseded; `worker.py` not union-merged — evidence: `.gitattributes` unchanged for `*.py`; PR #179 closed with a pointer to this package.

## Verification Plan

Level 2: ruff/compileall/pytest (worker suite). Behavior-preservation is the oracle (no result change). One PR, Manual Merge Gate. Builder ≠ verifier.

## Suggested Delegation

Sonnet builder (mechanical extraction, behavior-preserving) — must prove the full worker suite green before returning. Orchestrator: review the registry loading mechanism, confirm no duplicate/lost registration, close PR #179, lesson, PR, gate.

## Board Linkage

- Plane: unassigned (Sprint "Make execution trustworthy")
- Branch: TBD, cut off latest main per `aos-ship-pr`
