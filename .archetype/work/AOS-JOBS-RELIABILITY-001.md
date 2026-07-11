# AOS-JOBS-RELIABILITY-001 — Durable Jobs: Outbox, Leases, Idempotency, Dead-Letter

## Status

Proposed

## Origin

RFC-0014 (Proposed). Closes AOS-REVIEW-002 findings P0-1 (non-atomic PG→Redis enqueue, no lease) and P0-3 (non-idempotent handlers), verified in [[LES-033]]. Foundation package — P0-2 (scheduler), P1-2 (node agent), and P0-6 (authority) all depend on the leased, atomic, recoverable execution this delivers.

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `packages/aos_core/aos_core/services/jobs.py:16-39` — `enqueue_job` does `db.add(job)` → `db.commit()` (:36) → `db.refresh(job)` (:37) → `client.lpush(QUEUE, job.id)` (:38); no try/except, no compensation on Redis failure.
- `apps/worker/app/worker.py:167` — `client.brpop(QUEUE, timeout=5)` removes the id before `run_job` (:173); `except` calls `handle_failure` (:150-160, `MAX_ATTEMPTS=3` at :25) which re-`lpush`es only on a *catchable* exception. No lease, no heartbeat, no DLQ.
- `apps/worker/app/worker.py:129-147` — `run_job` calls `spec.run(job, db)` (:146, commits domain output) then `mark_job(job_id,"completed")` (:147); `mark_job` (:28-43) opens its own `SessionLocal` (:30) and commits (:43) — separate transaction.
- Domain commits inside handlers: Council review `worker.py:91-92`; digest `:74-77`; research note `research.py:482-483`; research run `research_run.py:131`.
- `Job` model `packages/aos_core/aos_core/models.py:288-301` + `AuditMixin:48-56` — fields: `id,status,version,created_at,updated_at,created_by,updated_by,meta,project_id,repository_id,job_type,priority,payload,result,error,queued_at,started_at,finished_at,attempts`. No `claimed_by`/`lease_expires_at`/`idempotency_key`.
- `CouncilReview.job_id` (`models.py:411`), `ResearchRun.job_id` (:202), `Artifact.job_id` (:262) are `index=True`, NOT unique; `NightlyDigest`/`ResearchNote` have no `job_id`.
- No `job_outbox` table across migrations `0001`–`0015` (`apps/api/alembic/versions/`). No reconciliation sweep anywhere.

## In-Scope Files

- `packages/aos_core/aos_core/models.py` — `JobOutbox` model; `jobs` columns `claimed_by`, `lease_expires_at`, `idempotency_key`; `origin_job_id` (unique) on `CouncilReview`, `ResearchRun`, `NightlyDigest`, `ResearchNote`.
- `packages/aos_core/aos_core/services/jobs.py` — `enqueue_job` writes job+outbox in one txn (no Redis); `claim_job` (CAS), `complete_job`, `fail_job`, `reap_expired_leases`, `dispatch_outbox`, `reconcile` helpers.
- `apps/worker/app/worker.py` — claim-based loop; single-transaction completion; dispatcher + reaper loops (or a sidecar module `apps/worker/app/reliability.py`).
- `apps/scheduler/app/main.py` — dispatcher/reaper can co-run here (single-firer coordination lands in AOS-SCHEDULER-RELIABILITY-001).
- `apps/api/alembic/versions/0016_job_reliability.py` (new migration).
- Handlers (`worker.py` or the new `handlers/` package from AOS-WORKER-HANDLERS-001) — get-or-create on `origin_job_id`.
- Tests: `apps/worker/tests/test_job_reliability.py` (crash-path, redelivery, dead-letter), `packages/aos_core/tests/test_jobs_outbox.py`.
- `tools/pr_guardian.py` route/inventory only if a route is added (none planned). `knowledge/wiki/lessons/` — closing lesson for LES-033 + any self-found defect. State docs + this spec.

## Out-of-Scope

- Scheduler single-firer / ScheduleFire (AOS-SCHEDULER-RELIABILITY-001).
- Node identity, node agent, remote claims (AOS-NODE-IDENTITY-001 / AOS-NODE-AGENT-001) — but the lease primitives are designed to be reused by them.
- Authority envelope (AOS-AUTHORITY-ENVELOPE-001).
- Any change to a handler's *result contents* or job semantics beyond durability.

## Acceptance Criteria

- Killing Redis during origination does not lose the job — evidence: `test_enqueue_survives_redis_down` (job row + undelivered outbox persist; dispatcher delivers on recovery).
- Killing the worker mid-job does not lose it and does not duplicate output — evidence: `test_expired_lease_reaped_and_completes_once` (drop lease → reaper re-enqueues → exactly one artifact).
- A redelivered job produces exactly one Council review / digest / research note / research run — evidence: `test_handler_idempotent_on_redelivery` (parametrized per handler; asserts one row keyed on `origin_job_id`).
- Retry budget exhaustion lands `dead_letter` with last error — evidence: `test_dead_letter_after_max_attempts`.
- CAS claim prevents double-claim — evidence: `test_two_workers_claim_one_job` (second claim affects 0 rows).
- Schema migrates cleanly — evidence: `alembic upgrade head` on fresh sqlite includes `job_outbox` + new columns; autogenerate probe → 0 ops.
- No successful-result change — evidence: existing `apps/worker/tests` green.

## Verification Plan

Level 2: ruff/compileall/pytest over `packages tools apps`. Level 4 (local): alembic round-trip + no-drift; crash-path tests run against sqlite and (where feasible) a real Postgres+Redis via compose. Level 3: CI api-tests, worker tests, compose-smoke (the durable path exercised end-to-end). Land in the four RFC-0014 slices, each its own PR under a head-SHA-pinned Manual Merge Gate. Builder ≠ verifier.

## Suggested Delegation

Slice 1 (outbox + atomic enqueue): Sonnet builder under Opus design (RFC-0014 §1) — must prove the Redis-down origination test locally. Slices 2–3 (leases, idempotency): Opus or senior Sonnet — the CAS claim and single-transaction completion are subtle; Orchestrator independently re-runs crash-path tests. Orchestrator: RFC, spec, review of the migration + every transaction boundary, lesson, PR, gate.

## Board Linkage

- Plane: unassigned (create on board; Sprint "Make execution trustworthy")
- Branch: TBD per slice, cut fresh off latest main per `aos-ship-pr` (LES-029)
