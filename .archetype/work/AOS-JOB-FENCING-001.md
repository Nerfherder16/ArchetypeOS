# AOS-JOB-FENCING-001 — Fenced job leases + runtime enforcement of handler metadata

## Status

In Review

## Verified Baseline

Confirmed by reading `main` @ `267f50f` (see the wave gap report + LES-033):

- `packages/aos_core/aos_core/models.py:326-327` — `Job` had only `claimed_by`/`lease_expires_at`; no fencing token. A worker id (`hostname:pid`) can recur.
- `packages/aos_core/aos_core/services/jobs.py` — `claim_job` returned a bare `bool`; `complete_job`/`release_for_retry`/`fail_job` did `db.get(Job, id)` then mutate with **no** ownership guard, so a stale worker could overwrite a reclaimed job. `renew_lease` keyed on `worker_id` only and was **never called** at runtime.
- `apps/worker/app/worker.py` — `run_job` ran `spec.run` synchronously with no lease renewal, no `try/finally`, no timeout. `HandlerSpec.timeout_seconds` / `max_attempts` / `result_schema` (`registry.py:46-49`) were declared + shape-tested only; runtime used module-const `MAX_ATTEMPTS=3`.
- Job concurrency was tested on SQLite only (`test_claim_is_single_winner`); no stale-completion or PostgreSQL race test.

## In-Scope Files

- `packages/aos_core/aos_core/models.py` (add `Job.claim_token`)
- `apps/api/alembic/versions/0023_job_claim_token.py` (new)
- `packages/aos_core/aos_core/services/jobs.py` (Claim, fenced transitions, `rearm_outbox`)
- `apps/worker/app/worker.py` (LeaseRenewer, timeout, result-schema, fenced retry)
- `apps/api/tests/test_jobs_outbox.py`, `apps/api/tests/test_job_fencing_pg.py` (new), `apps/worker/tests/test_worker.py`
- `docs/capability-map/layer-11.md`, state docs, `knowledge/wiki/lessons/LES-034.md`

## Out-of-Scope

- Node-aware execution / routing (AOS-NODE-EXECUTION-001) — reuses these fencing primitives but is a separate package.
- Authority classification (AOS-AUTHORITY-HARDEN-001).

## Acceptance Criteria

- Two workers racing one job produce exactly one active claim — evidence: `test_two_workers_race_produces_one_claim` (PostgreSQL), `test_claim_is_single_winner`.
- A stale worker cannot complete a reclaimed job — evidence: `test_stale_worker_cannot_complete_after_reclaim`, `test_stale_worker_cannot_complete_after_pg_reclaim`.
- A stale worker cannot fail/requeue/dead-letter after losing ownership — evidence: `test_stale_worker_cannot_fail_or_requeue_after_reclaim`.
- A long handler's lease is renewed; renewer stops in `finally` — evidence: `test_lease_renewer_extends_lease`, `test_renewer_detects_lost_ownership`.
- Per-handler timeout enforced — evidence: `test_handler_timeout_is_enforced`.
- Per-handler max_attempts drives dead-letter — evidence: `test_per_handler_max_attempts_drives_dead_letter`.
- Per-handler result_schema enforced — evidence: `test_result_schema_is_enforced`.
- Reaper clears the fencing token — evidence: `test_reap_clears_fencing_token`.
- Existing idempotency + reap behavior intact — evidence: full `apps/api` + `apps/worker` suites green.
- PostgreSQL concurrency, not only SQLite — evidence: CI "Vector store tests" job runs `test_job_fencing_pg.py` (`-m pgvector`).

## Verification Plan

Level 2 (targeted + full suites) locally; CI runs the PostgreSQL concurrency tests via the Postgres-backed pgvector job.

## Board Linkage

- Branch: `claude/aos-job-fencing-001`
