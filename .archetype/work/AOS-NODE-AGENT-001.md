# AOS-NODE-AGENT-001 — Node Agent: Leased Claim Protocol + Capability Routing

## Status

Proposed

## Origin

Closes AOS-REVIEW-002 finding P1-2 (node registry not connected to execution), verified in [[LES-033]]. Wave 2. Depends on AOS-JOBS-RELIABILITY-001 (leases) and AOS-NODE-IDENTITY-001 (signed claims).

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `apps/worker/app/worker.py` — grep for node/register_node/heartbeat/claim: the worker never registers as a node, never emits node heartbeats, never claims by capability (blind `brpop` on one `QUEUE`), never checks `max_sensitivity`/`write_access`, never reads `Node.endpoint`.
- No `aos-node`/`node-agent` daemon anywhere. `services/nodes.py` + `routes/nodes.py` are CRUD consumed only by the API/dashboard.
- `HandlerSpec` declares `capability`/`sensitivity` (`worker.py:46-58`) — the routing inputs exist but nothing consumes them for eligibility.

## In-Scope Files

- `apps/node_agent/` (new) — `aos-node` CLI: `register`, `heartbeat`, `poll`, `claim`, `execute`, `submit-result` over HTTPS polling + leased claims (reusing the AOS-JOBS-RELIABILITY-001 lease primitives and AOS-NODE-IDENTITY-001 signing).
- `apps/worker/app/worker.py` — the Compose worker becomes the first generic node (registers, heartbeats, claims by capability).
- `packages/aos_core/aos_core/services/routing.py` (new) — eligible-node calculation: `required capability ∈ node capabilities ∧ sensitivity ≤ ceiling ∧ write ≤ policy ∧ connectors available ∧ health fresh ∧ capacity`; deterministic routing explanation string.
- `apps/api/app/routes/nodes.py` — claim/result endpoints (identity-gated).
- Tests: `apps/node_agent/tests/…`, `packages/aos_core/tests/test_routing.py` (eligibility matrix, routing explanation), an integration test: a second node enrolls, receives only eligible work, survives disconnect, submits an auditable result.

## Out-of-Scope

- WebSockets (HTTPS polling is sufficient for v1 — the eval says so explicitly).
- Node identity/enrollment (AOS-NODE-IDENTITY-001) and lease durability (AOS-JOBS-RELIABILITY-001) — consumed, not built here.
- Connector-by-node availability probes (AOS-CONNECTOR-RUNTIME-001 feeds this).

## Acceptance Criteria

- A second machine enrolls, advertises a capability, and receives only eligible work — evidence: integration test `test_second_node_eligible_routing` (job requiring an unheld capability is not claimed).
- The node survives a disconnect and submits an auditable result — evidence: `test_node_reconnect_and_result` (lease reaped on disconnect, re-claimed, one result).
- Sensitivity and write policy are enforced at claim time — evidence: `test_sensitivity_and_write_gating` (a private-data job is not claimed by a public-only node).
- Routing is explainable — evidence: `test_routing_explanation` (the Control Tower string names capability, sensitivity, health, write for a routed job).

## Verification Plan

Level 4 (multi-process integration against compose Postgres/Redis with two node processes). Level 2 for the routing unit matrix. Level 3: CI + compose-smoke with a second node service. One PR (or a small slice set), Manual Merge Gate. Builder ≠ verifier.

## Suggested Delegation

Opus design of the claim protocol + routing; Sonnet builds the CLI scaffold and the deterministic routing matrix. Orchestrator: review the eligibility logic against the operator-policy vs node-capability split (LES-033 lesson 1), run the two-node integration test, lesson, PR, gate.

## Board Linkage

- Plane: unassigned (Sprint "Make distributed runtime real")
- Branch: TBD, cut off latest main after its dependencies merge
