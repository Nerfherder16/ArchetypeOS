# RFC-0014 — Durable Job Execution: Transactional Outbox, Leases, and Idempotency

## Status

Proposed (2026-07-11). Motivated by AOS-REVIEW-002 findings P0-1, P0-2, P0-3, verified against `main` and recorded in [[LES-033]].

## Problem

The job substrate is not durable under process crashes, Redis failures, or multiple schedulers. Verified on `main`:

- **Non-atomic origination (P0-1).** `enqueue_job` (`packages/aos_core/aos_core/services/jobs.py:36-38`) commits the `Job` row, then `client.lpush(QUEUE, job.id)`. A Redis failure after the commit orphans a `queued` row no worker will ever see. There is no outbox and no reconciliation sweep.
- **No lease / lost work on crash (P0-1).** The worker does `client.brpop(QUEUE, ...)` (`apps/worker/app/worker.py:167`), which removes the id before `run_job` executes. A SIGKILL/OOM between pop and completion loses the job entirely — the `except` handler never runs, and the `Job` model has no `claimed_by`/`lease_expires_at` to recover from. There is no worker heartbeat and no dead-letter state (terminal failure only flips `status="failed"`).
- **Non-idempotent handlers (P0-3).** `run_job` commits domain output inside `spec.run(job, db)` (`worker.py:146`) and then marks completion in a *separate* `SessionLocal` (`worker.py:30,43,147`). A crash between the two, followed by the in-process retry (`handle_failure`, `MAX_ATTEMPTS=3`), re-runs the handler and creates a second Council review / digest / research note. No domain output carries a unique `origin_job_id`.

Scheduler duplication (P0-2) shares the same root — `enqueue_job` commits before the schedule advances, and there is no fire-dedup key — but its fix lands in a sibling package (AOS-SCHEDULER-RELIABILITY-001) that depends on the outbox defined here.

The only mitigation today is a best-effort in-process retry that fires solely on a *catchable* Python exception; nothing survives process death.

## Goals

- At-least-once delivery with exactly-once *effect*: killing the worker or Redis during a job cannot lose the job or create duplicate domain output.
- A single, atomic origination path (job + intent to enqueue committed together).
- Crash recovery via leases, not luck.
- A dead-letter terminal state after the retry budget, inspectable by an operator.
- No behavior change to the *contents* of a successful job's result — only to durability.

## Non-Goals

- Distributed multi-node execution (AOS-NODE-AGENT-001) — this package makes single-node execution durable; the lease/claim primitives it introduces are the substrate the node agent later reuses.
- Authority enforcement around origination (AOS-AUTHORITY-ENVELOPE-001) — separate package; this RFC only makes origination *atomic*, giving that package a single chokepoint to wrap.
- Replacing Redis. Redis stays the fast delivery transport; Postgres becomes the source of truth.

## Design

### Mature-state target (per the roadmap "design to mature-state" rule)

Postgres is the durable source of truth for job state and delivery intent. Redis is a delivery accelerator, never the system of record. Every job transition is recoverable from Postgres alone; if Redis is wiped, a reconciliation sweep rebuilds the pending set. Each package below is a strict subset of this target.

### 1. Transactional outbox (closes P0-1 origination half)

New table `job_outbox`:

| column | notes |
|---|---|
| `id` | PK |
| `job_id` | FK → `jobs.id`, unique (one outbox row per job) |
| `delivered_at` | nullable; set when the dispatcher has pushed to Redis |
| `created_at` | for ordering / staleness |

`enqueue_job` becomes: create the `Job` **and** its `JobOutbox` row and commit them in **one** transaction. It no longer touches Redis. A separate **dispatcher** (a loop in the worker/scheduler process, or a thread) selects undelivered outbox rows (`delivered_at IS NULL`), `lpush`es each to Redis, and marks `delivered_at`. If Redis is down, rows accumulate undelivered and are retried — nothing is lost. Idempotent `lpush`: re-pushing a job id already claimed is caught by the lease (below), so double-dispatch is safe.

Idempotency key on origination: `enqueue_job` accepts an optional `idempotency_key`; a unique partial index on `jobs(idempotency_key)` (where not null) makes a retried origination return the existing job rather than create a second.

### 2. Leased claims + worker heartbeat + recovery (closes P0-1 execution half)

New columns on `jobs`: `claimed_by` (worker id), `lease_expires_at`, `attempts` (exists). New table `worker_heartbeat(worker_id, last_seen_at)` — or reuse the node heartbeat once AOS-NODE-AGENT-001 lands; for this package a minimal worker-liveness row.

Claim protocol (replaces bare `brpop`):

1. Worker `brpop`s a job id from Redis (fast path) **or** the reconciler hands it one.
2. Worker atomically claims it in Postgres: `UPDATE jobs SET status='running', claimed_by=:w, lease_expires_at=now()+:ttl, started_at=now() WHERE id=:id AND status IN ('queued','running') AND (lease_expires_at IS NULL OR lease_expires_at < now())` — the `WHERE` makes the claim a compare-and-swap; if another worker already holds a live lease, this affects 0 rows and the worker drops the id.
3. Worker renews the lease periodically for long jobs (heartbeat).
4. On completion, the lease is cleared as part of the completion transaction.

A **lease reaper** (in the reconciler) finds `status='running' AND lease_expires_at < now()`, increments `attempts`, and either re-enqueues (via outbox) if `attempts < MAX_ATTEMPTS` or moves to dead-letter. This recovers jobs from a killed worker.

### 3. Handler idempotency (closes P0-3)

Two layers, defense in depth:

- **Atomic completion.** `run_job` runs the handler's side effects **and** the job-completion update in the *same* session and *same* transaction, so they commit or roll back together. `mark_job` no longer opens its own `SessionLocal` for the completion path. A crash therefore leaves *neither* the domain artifact nor the completion — the retry re-runs cleanly.
- **Unique `origin_job_id`.** For domain outputs where the contract is one-per-job (Council review, research run, digest, research note), add a nullable `origin_job_id` FK with a unique constraint. The handler does a get-or-create keyed on `origin_job_id`, so even a belt-and-suspenders double-execution cannot create a second row — it returns the existing one.

`HandlerSpec` gains an `idempotency_strategy` field (declared by AOS-WORKER-HANDLERS-001) so each handler states how it is safe: `atomic_completion` (default), `origin_job_id`, or `naturally_idempotent`.

### 4. Dead-letter + reconciliation

- `status='dead_letter'` terminal state after `attempts >= MAX_ATTEMPTS`, with the last error retained. Surfaced in the operator queue (Track E).
- **Reconciliation sweep** (periodic): (a) outbox rows undelivered beyond a threshold → re-dispatch; (b) `queued` jobs absent from Redis → re-dispatch; (c) expired leases → reap (above). This is the repair process P0-1 says is missing.

### Migration & rollout

- Alembic migration adds `job_outbox`, the new `jobs` columns, `origin_job_id` on the four domain tables, and indexes. Single Alembic head preserved (LES-L05-adjacent governance).
- Backfill: existing `queued` jobs get outbox rows marked delivered (they're already in Redis or lost — the sweep will re-dispatch any truly missing).
- The dispatcher and reaper are additive loops; the fast `brpop` path is preserved for latency, so throughput is unchanged in the happy path.

## Alternatives considered

- **Redis Streams + consumer groups** instead of a PG outbox. Native `XCLAIM`/pending-entries-list give leases and acks for free. Rejected as the *primary* store because it puts the source of truth in Redis (against local-first and durability goals) and still needs an outbox bridge to stay consistent with the `jobs` table on origination. We keep Redis as transport only. *Trade-off:* our design runs a dispatcher loop Streams would not need.
- **DB-only polling (drop Redis).** Simplest to reason about (one store), but loses push latency and hammers Postgres with poll queries at scale. Rejected for now; the outbox design leaves this open as a fallback (the reconciler already polls).
- **Advisory-lock the whole `run_job`.** Coarse, doesn't survive process death (advisory locks release on disconnect — which is actually the wrong semantics here; we want the lease to *persist* past a crash so the reaper can see it). Rejected.

## Risks

- **Highest-risk package in the review** — touches every job path. Mitigation: land in reviewable slices (below), each behind CI + Guardian + a head-SHA-pinned Manual Merge Gate; crash-path tests are the oracle, not inference.
- **Double-dispatch under dispatcher retry** — mitigated by the CAS claim (step 2): a job already claimed with a live lease affects 0 rows on re-claim.
- **Lease TTL tuning** — too short reaps live long jobs; too long delays recovery. Mitigation: per-handler `timeout` (from `HandlerSpec`) sizes the TTL; long handlers renew.
- **Migration on a live deployment** — additive columns/tables only, no drops; safe forward migration.

## Slicing (implementation order)

1. **Slice 1 — Outbox + atomic origination.** `job_outbox` table, `enqueue_job` writes job+outbox in one txn (no Redis), dispatcher loop pushes + marks delivered. Crash-between-commit-and-push can no longer orphan a job. *Test:* simulate Redis-down at origination → job persists undelivered → dispatcher delivers on recovery.
2. **Slice 2 — Leased claims + reaper + heartbeat.** CAS claim replaces bare `brpop` execution, lease reaper recovers expired leases. *Test:* kill a worker mid-job (drop the lease) → reaper re-enqueues → job completes once.
3. **Slice 3 — Handler idempotency + dead-letter.** Atomic completion (single txn), `origin_job_id` unique on the four domain tables, `dead_letter` state. *Test:* force a redelivery → exactly one domain artifact; exhaust retries → `dead_letter`.
4. **Slice 4 — Reconciliation sweep + operator surfacing.** Periodic repair for undelivered outbox / missing-from-Redis / expired leases; expose counts.

Each slice is one PR = one work-package increment (roadmap non-negotiable).

## Acceptance criteria

- Killing the worker during a job does not lose it and does not duplicate domain output — evidence: crash-path integration test (Slice 2 + 3).
- Killing Redis during origination does not lose the job — evidence: Redis-down origination test (Slice 1).
- A redelivered job produces exactly one Council review / digest / research note / research run — evidence: idempotency test per handler (Slice 3).
- Retry budget exhaustion lands the job in `dead_letter` with the last error — evidence: dead-letter test (Slice 3).
- `alembic upgrade head` on fresh sqlite includes the new tables/columns; autogenerate probe → 0 schema ops — evidence: alembic round-trip.
- No change to a successful job's result contents — evidence: existing worker suite green.

## Effort

L (large). Four slices, ~1 sprint. Slice 1 is the smallest and unblocks AOS-SCHEDULER-RELIABILITY-001.

## Dependencies

- AOS-WORKER-HANDLERS-001 (richer `HandlerSpec` with `idempotency_strategy`, `timeout`) should land first or alongside Slice 3.
- RFC-0007 (Scheduling Control Plane) — the scheduler consumes the outbox this RFC defines.

## Final Judge Verdict

Pending operator approval.
