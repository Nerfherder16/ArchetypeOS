# AOS-NODE-IDENTITY-001 — Per-Node Service Identity, Enrollment, Signed Claims

## Status

Proposed

## Origin

Closes AOS-REVIEW-002 finding P0-5 (node registration/heartbeat mutation has no service identity), verified in [[LES-033]]. Wave 2 — prerequisite for AOS-NODE-AGENT-001 (signed claims).

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `apps/api/app/routes/nodes.py:19,32` — `POST /nodes/register` and `POST /nodes/{id}/heartbeat` depend only on `Depends(get_db)`; imports (:7) are `APIRouter, Depends, HTTPException` — no auth. `register()` passes attacker-controlled `write_access`/`max_sensitivity`/`capabilities` into `register_node` (`services/nodes.py:29-52`), which overwrites any node *by name*; `record_heartbeat` (:58-71) sets `node_status` from the payload.
- `apps/api/app/routes/connectors.py:40-44` — `POST /connectors/{name}/health` similarly unauthenticated.
- `apps/api/app/main.py:13-19,48-49` — only CORS middleware; routers included with no `dependencies=`.
- Precedent for a token check exists: `apps/api/app/routes/audits.py:22` uses `x_telemetry_token` — the pattern is present but not applied to node/connector mutation.

## In-Scope Files

- `packages/aos_core/aos_core/services/node_identity.py` (new) — enrollment (operator-approved), per-node credential issue, hash storage, verify, rotate, revoke; sign/verify job claims.
- `packages/aos_core/aos_core/models.py` — `NodeCredential(node_id, credential_hash, issued_at, rotated_at, revoked_at)`; separate operator-policy fields (`write_access`, `max_sensitivity`) from node-reported capability so a node cannot self-grant.
- `apps/api/app/routes/nodes.py` — require a node token (or mTLS identity) dependency on register-renew/heartbeat/claim/result/capability-change; enrollment route is operator-gated.
- `apps/api/app/routes/connectors.py` — gate `POST /connectors/{name}/health` behind node/service identity.
- `apps/api/app/deps.py` or similar — a reusable `require_node_token` dependency (mirror `x_telemetry_token`).
- `apps/api/alembic/versions/0019_node_credentials.py` (new).
- Tests: `apps/api/tests/test_node_identity.py` (unauth register rejected; self-grant rejected; rotation/revocation; signed claim validated). Route inventory updated (LES-L05).

## Out-of-Scope

- The node daemon / claim protocol itself (AOS-NODE-AGENT-001) — this package provides the identity it uses.
- Operator (human) auth for the dashboard (Track F).
- Concurrency constraints on the node tables (AOS-NODE-CONSTRAINTS-001).

## Acceptance Criteria

- Unauthenticated register/overwrite is rejected — evidence: `test_register_requires_node_token` (401/403 without a valid token).
- A node cannot self-grant write access or raise its sensitivity ceiling — evidence: `test_node_cannot_escalate` (operator policy wins over node-reported values).
- Connector-health POST requires identity — evidence: `test_connector_health_requires_token`.
- Credentials rotate and revoke — evidence: `test_credential_rotation_and_revocation`.
- Job claims are signed and result ownership validated — evidence: `test_signed_claim_and_result_ownership`.
- Route inventory + guardian updated in the same change — evidence: `test_route_inventory` passes with the new routes.

## Verification Plan

Level 2 + full API suite. Security-sensitive: Orchestrator reviews every new dependency wiring and the credential-hash storage (never store plaintext). Level 3: CI. One PR, Manual Merge Gate. Builder ≠ verifier.

## Suggested Delegation

Opus or senior Sonnet builder (auth/credential handling is high-stakes — mismatched dependency wiring is a security bug). Orchestrator: adversarial review (can any mutation route still be reached unauthenticated? can a node escalate?), lesson, PR, gate.

## Board Linkage

- Plane: unassigned (Sprint "Make distributed runtime real")
- Branch: TBD, cut off latest main per `aos-ship-pr`
