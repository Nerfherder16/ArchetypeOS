# AOS-SCHEDULER-RELIABILITY-001 — Reliable Scheduling: ScheduleFire, Single-Firer, Nominal Cadence

## Status

Proposed

## Origin

RFC-0014-adjacent (uses its outbox). Closes AOS-REVIEW-002 finding P0-2 (scheduler can duplicate jobs), verified in [[LES-033]]. Depends on AOS-JOBS-RELIABILITY-001 Slice 1 (transactional outbox).

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `packages/aos_core/aos_core/services/scheduler.py:18-38` — `run_due_schedules` queries `Schedule.enabled AND Schedule.next_run_at <= now` (plain `SELECT`, no locking), loops calling `enqueue_job` (each self-commits), then sets `last_run_at=now` / `next_run_at=now+interval` (:36) and a single `db.commit()` (:37) after the loop. A crash between per-job commit and the final commit re-fires next tick.
- `apps/scheduler/app/main.py:23-31` — unconditional `while True` with `TICK_SECONDS=30` (:17); no leader election, no advisory lock. Two replicas double-enqueue.
- No `ScheduleFire` entity anywhere. `Schedule` model `packages/aos_core/aos_core/models.py:304-314`; migration `0002_schedule.py` creates only PK + non-unique indexes.
- `next_run_at = now + interval` computes cadence from observed tick time, not nominal — missed runs coalesce, cadence drifts forward by up to one tick.

## In-Scope Files

- `packages/aos_core/aos_core/models.py` — `ScheduleFire(schedule_id, nominal_fire_at, job_id, created_at)` with `UniqueConstraint(schedule_id, nominal_fire_at)`.
- `packages/aos_core/aos_core/services/scheduler.py` — claim due schedules with `FOR UPDATE SKIP LOCKED` or a `pg_advisory_lock`; create `ScheduleFire` + enqueue (via outbox) in one txn; advance `next_run_at` from the nominal fire time; explicit catch-up policy.
- `apps/scheduler/app/main.py` — single-firer coordination.
- `apps/api/alembic/versions/0017_schedule_fire.py` (new).
- Tests: `packages/aos_core/tests/test_scheduler_reliability.py` (two-replica no-double-enqueue, crash-no-refire, catch-up policy, nominal cadence).
- State docs + this spec; lesson if a defect is self-found.

## Out-of-Scope

- Job durability itself (AOS-JOBS-RELIABILITY-001 owns the outbox/leases this consumes).
- Cron-expression scheduling (interval-only today; not expanding syntax here).

## Acceptance Criteria

- Two scheduler replicas do not double-enqueue a due schedule — evidence: `test_two_replicas_single_fire` (concurrent `run_due_schedules`; exactly one `ScheduleFire` + one job).
- A crash mid-tick does not re-fire the same nominal occurrence — evidence: `test_crash_no_refire` (partial commit; re-run sees the `ScheduleFire` uniqueness and skips).
- Catch-up policy is explicit and observable — evidence: `test_catchup_coalesces_missed_runs` (scheduler down N intervals → one fire, recorded reason).
- Nominal cadence preserved (no forward drift) — evidence: `test_nominal_cadence` (`next_run_at` derived from prior nominal, not `now`).
- Schema migrates cleanly — evidence: `alembic upgrade head`; autogenerate → 0 ops.

## Verification Plan

Level 2 + Level 4 (concurrency tests need a real Postgres for `SKIP LOCKED`/advisory locks — run against compose Postgres; sqlite path asserts the ScheduleFire uniqueness logically). Level 3: CI + compose-smoke. One PR, Manual Merge Gate. Builder ≠ verifier.

## Suggested Delegation

Senior Sonnet/Opus builder: the `SKIP LOCKED` claim + ScheduleFire uniqueness are Postgres-semantics-sensitive. Orchestrator independently re-runs the two-replica test on real Postgres, reviews, lesson, PR, gate.

## Board Linkage

- Plane: unassigned (Sprint "Make execution trustworthy")
- Branch: TBD, cut off latest main after AOS-JOBS-RELIABILITY-001 Slice 1 merges
