# AOS-AUTHORITY-HARDEN-001 — Server-classified, one-use, bound, resumable authority envelope

## Status

In Review

## Verified Baseline

Re-verified against merged `main` (post WP1/WP2/WP3):

- `services/jobs.py` `enqueue_job` — `action_class` defaulted `read_only` and was a client-suppliable param; no route derived it; unknown job types were persisted then failed at worker dispatch.
- `services/authority_envelope.py` — `mark_executed` was a bare assign (no CAS, no commit), so an authorized envelope could be consumed more than once; `ActionRequest` had no `repository_id`/`job_id`/`expires_at`.
- `routes/repositories.py` distill — minted a FRESH `ActionRequest` every call (retry storm), accepted no `action_request_id`, and hardcoded `sensitivity="public"`.
- `models.Repository` — no `sensitivity` policy field.

## In-Scope Files

- `packages/aos_core/aos_core/models.py` (ActionRequest: repository_id/job_id/expires_at; Repository.sensitivity) + `apps/api/alembic/versions/0025_authority_harden.py`
- `packages/aos_core/aos_core/services/authority_envelope.py` (binding params, `consume_action` CAS, `matches`, expiry)
- `packages/aos_core/aos_core/services/job_requirements.py` (server-owned `action_class`)
- `packages/aos_core/aos_core/services/jobs.py` (derive action_class, reject unknown type, one-use consume + job link)
- `apps/api/app/routes/jobs.py` (UnknownJobType→422, PermissionError→403), `apps/api/app/routes/repositories.py` (distill approve-and-resume + repo sensitivity), `apps/api/app/schemas.py`
- tests: `test_authority_harden.py`, `test_authority_harden_pg.py`, `test_authority_envelope.py`, `apps/worker/tests/test_job_requirements.py`
- `docs/capability-map/layer-11.md`, `knowledge/wiki/lessons/LES-037.md`

## Out-of-Scope

- Applying the envelope to every direct high-impact path beyond job origination + distillation (council/research egress classification) — a follow-up; the registry seam + `consume_action` are in place for it.
- A web approvals view (surfaced via the API).

## Acceptance Criteria

- A write-capable handler cannot be submitted as read_only — evidence: `action_class` server-derived (`test_registry_action_classes_are_valid`, `test_enqueue_high_impact_without_envelope_is_rejected`).
- Unknown job types rejected before persistence — evidence: `test_enqueue_unknown_job_type_is_rejected_before_persistence`, API 422 in `create_job`.
- A high-impact job without authorization is rejected — evidence: `test_enqueue_high_impact_without_envelope_is_rejected`, `test_enqueue_high_impact_with_unauthorized_envelope_is_rejected`.
- An authorized request can be consumed only once; concurrent consumers → one winner — evidence: `test_consume_action_is_one_use`, PG `test_concurrent_consume_has_exactly_one_winner`.
- A request approved for one target/payload cannot authorize another — evidence: `test_matches_rejects_wrong_repository_class_payload`, `test_distill_rejects_envelope_bound_to_another_repository`, `test_enqueue_envelope_class_mismatch_is_rejected`.
- A rejected/expired request cannot execute — evidence: `test_rejected_envelope_cannot_be_consumed`, `test_is_authorized_respects_expiry`.
- Distillation can be approved then resumed; does not mint a new pending request per approved retry — evidence: `test_private_repo_distill_requires_approval_then_resumes` (resume via `action_request_id`; replay refused).
- Private repository content is not auto-classified public — evidence: `test_private_repo_distill_requires_approval_then_resumes` (private → 403), `test_public_repo_distill_auto_authorizes` (public unchanged).
- Consumed envelope linked to its job (execution trace) — evidence: `test_enqueue_high_impact_with_authorized_envelope_runs_and_consumes_it` (`ar.job_id == job.id`).
- Never executed-on-failure — evidence: distill consumes only after `distill_repository` returns.

## Verification Plan

Level 2 — targeted + full apps/api + apps/worker; PostgreSQL one-use-consume concurrency test in the CI Postgres job.

## Board Linkage

- Branch: `claude/aos-authority-harden-001`
