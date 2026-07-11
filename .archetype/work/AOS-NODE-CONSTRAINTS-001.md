# AOS-NODE-CONSTRAINTS-001 — Concurrency-Safe Node & Heartbeat Constraints

## Status

Proposed

## Origin

Closes AOS-REVIEW-002 finding P1-3 (node/heartbeat DB constraints not concurrency-safe), verified in [[LES-033]]. Independent, low-risk quick win — no dependency on the job substrate.

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `packages/aos_core/aos_core/services/nodes.py:29-32` — `register_node` does `db.query(Node).filter(Node.name==name).first()` then insert-if-absent (query-then-insert race).
- `Node.name` `packages/aos_core/aos_core/models.py:519` — `String(255), nullable=False`, NO `unique=True`. Migration `0010_nodes.py` creates only non-unique indexes on `node_status`/`status`.
- `NodeCapability` `models.py:533-542` — no `UniqueConstraint`; `node_id` indexed non-unique → duplicate `(node_id, capability)` possible.
- `AuditHeartbeat` `models.py:222-232` — `UniqueConstraint("routine","project_id", name="uq_audit_heartbeats_routine_project")` but `project_id` is `nullable=True`. Postgres treats NULLs as distinct → concurrent `(routine, NULL)` inserts duplicate. Service `services/audit_heartbeat.py:34-41` does query-then-insert.

## In-Scope Files

- `packages/aos_core/aos_core/models.py` — `Node.name` `unique=True`; `UniqueConstraint(node_id, capability)` on `NodeCapability`; normalize global audit scope (sentinel non-null scope key) OR document a partial unique index for `project_id IS NULL`.
- `packages/aos_core/aos_core/services/nodes.py` — replace query-then-insert with a DB upsert (`ON CONFLICT`/`INSERT … ON CONFLICT DO UPDATE`).
- `packages/aos_core/aos_core/services/audit_heartbeat.py` — upsert; partial unique index for global scope.
- `apps/api/alembic/versions/0018_node_constraints.py` (new) — unique constraints + partial index; heartbeat retention/aggregation note.
- Tests: `packages/aos_core/tests/test_node_constraints.py`, `test_audit_heartbeat_constraints.py` (concurrent insert → one row).

## Out-of-Scope

- Node identity/auth (AOS-NODE-IDENTITY-001).
- Wiring the registry to execution (AOS-NODE-AGENT-001).

## Acceptance Criteria

- Concurrent `register_node` for one name yields one row — evidence: `test_concurrent_register_single_node` (two sessions; upsert or unique-violation-caught).
- Duplicate `(node_id, capability)` rejected — evidence: `test_capability_uniqueness`.
- Concurrent global `(routine, NULL)` heartbeats yield one row — evidence: `test_global_heartbeat_single_row` (partial unique index / sentinel scope enforced).
- Schema migrates cleanly on existing data — evidence: `alembic upgrade head` (with a dedupe step if duplicates exist); autogenerate → 0 ops.

## Verification Plan

Level 2 + Level 4 (partial-index / `ON CONFLICT` behavior needs real Postgres — run concurrency tests against compose Postgres; sqlite asserts the logical guard). Level 3: CI + compose-smoke. One PR, Manual Merge Gate.

## Suggested Delegation

Sonnet builder (migration + upsert are mechanical) — must prove the concurrency tests on real Postgres. Orchestrator: review the partial-index vs sentinel-scope choice, dedupe-before-constrain safety, PR, gate.

## Board Linkage

- Plane: unassigned (Sprint "Make execution trustworthy" — quick win)
- Branch: TBD, cut off latest main per `aos-ship-pr`
