# AOS-NODE-EXECUTION-001 — Node-enforced job execution (routing on the claim path)

## Status

In Review

## Verified Baseline

Re-verified against merged `main` (post WP1/WP2), not the pre-merge gap report:

- `services/routing.py` — `route_job`/`node_eligibility` existed but the ONLY caller was the read-only `GET /nodes/route`; neither `enqueue_job` nor the worker consulted it.
- `models.Job` — persisted no routing state (no `assigned_node_id`/`routing_status`/`required_capability`/`sensitivity`/`requires_write`).
- `services/jobs.py` — one global queue `archetypeos:jobs`; `claim_job` (WP1-fenced) checked only status+lease+token, never node assignment or eligibility.
- `routing._rank` — `except ValueError: return 0` → an unknown sensitivity failed OPEN (treated as `public`); sensitivity was an unvalidated free string.

## In-Scope Files

- `packages/aos_core/aos_core/sensitivity.py` (new — shared `Sensitivity` enum, fail-closed rank/validate)
- `packages/aos_core/aos_core/services/routing.py` (use shared fail-closed rank)
- `packages/aos_core/aos_core/services/job_requirements.py` (new — server-owned requirements registry)
- `packages/aos_core/aos_core/models.py` (Job routing fields) + `apps/api/alembic/versions/0024_job_routing.py` (new)
- `packages/aos_core/aos_core/services/jobs.py` (route at origination, `claim_job_for_node`, `reroute_waiting_jobs`, reconcile hook)
- `apps/worker/app/worker.py` (`_self_node`, claim via `claim_job_for_node`)
- `apps/api/app/routes/nodes.py` (validate sensitivity → 422), `apps/api/app/schemas.py` (JobRead routing fields)
- tests: `apps/api/tests/test_node_execution.py`, `apps/api/tests/test_node_execution_pg.py` (new), `apps/worker/tests/test_job_requirements.py` (new)
- `docs/capability-map/layer-11.md`, `knowledge/wiki/lessons/LES-036.md`

## Out-of-Scope

- Server-owned ACTION classification / one-use envelope (AOS-AUTHORITY-HARDEN-001, WP4 — extends the requirements registry with action_class).
- Per-node Redis delivery queues + remote HTTPS execution (follow-ups; the claim is the enforcement point).
- A web Control-Tower view (routing is surfaced via `GET /jobs/{id}` + `GET /nodes/route`; UI is a follow-up).

## Acceptance Criteria

- Job requiring capability X cannot be claimed by a node without X — evidence: `test_node_without_capability_cannot_claim`.
- Private work cannot be claimed by a public-only node — evidence: `test_private_work_rejected_by_public_only_node`.
- Write work cannot be claimed by a read-only node — evidence: `test_write_work_rejected_by_read_only_node`.
- Unhealthy/stale nodes cannot claim — evidence: `test_unhealthy_node_cannot_claim`, `test_stale_node_cannot_claim`.
- A worker cannot claim a job assigned to another node — evidence: `test_worker_cannot_claim_job_assigned_to_another_node`, `test_nodeless_worker_cannot_claim_assigned_job`, and PG `test_only_assigned_node_claims_under_concurrency`.
- Routing decisions persisted + auditable — evidence: `test_origination_routes_to_eligible_node`, `test_job_read_exposes_routing_fields`.
- No eligible node → job waits visibly (not lost); restored health routes it — evidence: `test_origination_with_no_eligible_node_waits`, `test_reroute_assigns_waiting_job_when_node_appears`, `test_reroute_reassigns_when_assigned_node_goes_stale`.
- Node failure mid-execution uses the WP1 fenced lease reaper — evidence: WP1 `test_reap_*` (unchanged) + `claim_job_for_node` mints a fresh `claim_token`.
- Unknown sensitivity fails closed — evidence: `test_unknown_sensitivity_ranks_above_every_ceiling`, `test_validate_sensitivity_rejects_unknown`, `test_route_endpoint_rejects_unknown_sensitivity`.
- Global queue cannot bypass assignment — evidence: the claim CAS gate `assigned_node_id ∈ (NULL, node)` (`test_worker_cannot_claim_job_assigned_to_another_node`).
- Multi-node PostgreSQL, not only SQLite — evidence: CI "Vector store tests" runs `test_node_execution_pg.py` (`-m pgvector`).
- Server-derived requirements agree with handlers — evidence: `test_job_requirements_match_handlers`.

## Verification Plan

Level 2 — targeted + full apps/api (544 passed / 7 skipped) + apps/worker (28 passed); multi-node PostgreSQL claim tests run in the CI Postgres job.

## Board Linkage

- Branch: `claude/aos-node-execution-001`
