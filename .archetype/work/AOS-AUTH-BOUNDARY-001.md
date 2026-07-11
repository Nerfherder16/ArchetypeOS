# AOS-AUTH-BOUNDARY-001 — Operator + node authentication on the control plane

## Status

In Review

## Verified Baseline

Confirmed on `main` @ `267f50f` (wave gap report):

- `apps/api/app/routes/nodes.py:41` — `POST /nodes/enroll` had only `Depends(get_db)`; an anonymous caller could enroll a node AND set `write_access`/`max_sensitivity`. No credential rotation or revocation route existed (service-level only).
- `apps/api/app/routes/authority.py:75,83` — `authorize`/`reject` unauthenticated; approver hardcoded literal `"operator"` (`authority_envelope.py:61,75`).
- `config.py` — `audit_heartbeat_token`/`connector_write_token` default `""` → gates open unconditionally; no operator token; no fail-closed profile. Connector/audit gates used plain `!=` (not constant-time).
- No reusable operator-auth dependency existed.

## In-Scope Files

- `packages/aos_core/aos_core/config.py` (operator_token, auth_dev_mode)
- `apps/api/app/security.py` (new — `require_operator`)
- `apps/api/app/routes/nodes.py` (operator gate on enroll; rotate/revoke routes; node-token binding on re-register)
- `apps/api/app/routes/authority.py` (operator gate + actor on approve/reject)
- `apps/api/app/routes/connectors.py`, `apps/api/app/routes/audits.py` (constant-time compare)
- `apps/api/app/schemas.py` (`updated_by` on NodeRead/ActionRequestRead)
- `docker-compose.yml`, `.env.example` (fail-closed deployed profile)
- `apps/api/tests/test_auth_boundary.py` (new), `test_route_inventory.py`
- `docs/AUTHORITY_POLICY.md`, `docs/capability-map/layer-11.md`, `knowledge/wiki/lessons/LES-035.md`

## Out-of-Scope

- Server-owned action classification / one-use envelope (AOS-AUTHORITY-HARDEN-001, WP4 — reuses this operator gate).
- Node-aware execution / claim authentication (AOS-NODE-EXECUTION-001, WP3).

## Acceptance Criteria

- Anonymous enrollment rejected — evidence: `test_anonymous_enroll_rejected_when_token_set`.
- Deployed profile fails closed with no secret — evidence: `test_enroll_fails_closed_when_no_token_and_dev_mode_off`; dev-mode exception explicit — `test_enroll_open_in_dev_mode`.
- Enrollment records operator identity — evidence: `test_enroll_succeeds_with_operator_token_and_records_actor`.
- Anonymous authority approve/reject rejected; approval records operator — evidence: `test_anonymous_authorize_rejected`, `test_authorize_records_operator_identity`, `test_anonymous_reject_rejected`.
- Rotated credential invalidates the prior; revoked cannot heartbeat; both operator-only — evidence: `test_rotate_credential_invalidates_prior_token`, `test_revoke_credential_blocks_heartbeat`, `test_rotate_requires_operator`, `test_revoke_requires_operator`.
- A node cannot replace another (enrolled) node without its token; new node still bootstraps — evidence: `test_enrolled_node_cannot_be_reregistered_without_its_token`, `test_new_node_can_still_self_register`.
- Constant-time token comparison — evidence: `secrets.compare_digest` in `security.py`/`connectors.py`/`audits.py`.
- Deployed Compose fails closed — evidence: `docker-compose.yml` `AUTH_DEV_MODE=false`; compose-smoke config validates.

## Verification Plan

Level 2 — targeted security tests + full apps/api suite; compose-smoke validates the deployed profile.

## Board Linkage

- Branch: `claude/aos-auth-boundary-001`
