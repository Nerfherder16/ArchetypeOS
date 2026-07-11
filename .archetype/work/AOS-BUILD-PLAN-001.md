# AOS-BUILD-PLAN-001 — Implementation Plan from an approved Decision

## Status

Proposed (2026-07-11). Wave B (stage 1) of RFC-0015 (Build Intelligence). Ready — no execution, no external dependency.

## Origin

Closes AOS-REVIEW-003 seam #1 (Decision → Plan hard break). Opens the right-of-decision half of the loop **without introducing any code execution** — safe to build immediately; useful even while builds stay human.

## Verified Baseline

Confirmed by inspection of `main` @ `70dfccb`:

- `services/decisions.py:126 approve_decision` transitions a `Decision` `draft → approved`, sets `approved_by/approved_at`, writes `ApprovalRecord(requested_capability="decision.approve")`. Status vocab: `draft`/`needs_evidence`/`approved`/`rejected` on `AuditMixin.status` (`decisions.py:31-34`).
- `adr.py:147 export_decision_adr` is the current terminus; nothing consumes an approved decision to plan implementation.
- `Decision` (`models.py:136-149`) carries `context, decision, alternatives, tradeoffs, consequences, evidence, confidence`.
- Pattern to mirror: `draft_decision_from_review` idempotency via `meta["council_review_id"]` (`decisions.py:50`); `AuditMixin` gives `id/status/version/meta` free (`models.py:48-56`).

## In-Scope Files

- `packages/aos_core/aos_core/models.py` — new `ImplementationPlan(AuditMixin, Base)` (`implementation_plans`): `decision_id` FK, `project_id` FK, `title` String(255), `objective` Text, `tasks` JSON, `acceptance_criteria` JSON, `verification_requirements` JSON, `target_repository_id` FK nullable, `risk` Text, `effort` String(128), `evidence` JSON. Status via `AuditMixin.status` (`draft`/`approved`/`rejected`/`superseded`).
- `packages/aos_core/aos_core/services/build_plan.py` — `plan_from_decision(db, *, decision_id) -> ImplementationPlan` (requires `decision.status=="approved"`, else 409; drafts via the `Provider`; `status="draft"`; idempotent on `meta["decision_id"]`) and `approve_plan(db, *, plan_id, approver, rationale=None)` (draft→approved, writes `ApprovalRecord(requested_capability="plan.approve")`).
- `apps/api/app/routes/plans.py` (new) + register in the app router — `POST /decisions/{id}/plan`, `GET /plans/{id}`, `GET /projects/{id}/plans`, `POST /plans/{id}/approve`.
- `apps/api/alembic/versions/0024_implementation_plans.py` — additive table (head currently `0023`); `import aos_core.models`.
- Tests: `apps/api/tests/test_build_plan.py` + service tests.
- Route inventory bump (frozen inventory count).

## Out-of-Scope

- **No `job_type`, no build/execute, no code execution** — that is AOS-BUILD-EXEC-001.
- No web UI (a later slice).
- No provider change — reuse the deterministic `Provider` in CI, `ClaudeCodeProvider` on the authed node.

## Acceptance Criteria

- `plan_from_decision` on an approved decision drafts an `ImplementationPlan(status="draft")` with objective + tasks + acceptance criteria — evidence: `test_plan_from_approved_decision`.
- On a non-approved decision → 409 — evidence: `test_plan_requires_approved_decision`.
- Idempotent: a second call for the same decision returns the existing plan — evidence: `test_plan_idempotent`.
- `approve_plan` transitions draft→approved and writes an `ApprovalRecord` — evidence: `test_approve_plan`.
- Routes: `POST /decisions/{id}/plan` (404 missing / 409 unapproved), `GET`s, `POST /plans/{id}/approve` — evidence: API tests.
- `alembic upgrade head` on fresh sqlite includes `implementation_plans`; autogenerate probe → 0 ops — evidence: alembic round-trip. Full suite green; ruff clean; `tsc && vite build` unaffected.

## Verification Plan

Level 2 (hermetic API + service tests). Builder ≠ verifier: Sonnet builds model+service+routes+migration+tests; Opus reviews the migration (no-drift, `import aos_core.models`), the 409 gate, and the idempotency key.

## Suggested Delegation

Sonnet subagent (medium, well-specified CRUD+service+migration, mirrors existing `decisions`/`research_plans` patterns) in a dedicated worktree; Opus reviews before PR.

## Board Linkage

Branch: `<session>/aos-build-plan-001`. One PR. Precedes AOS-BUILD-EXEC-001 (which consumes an approved `ImplementationPlan`).
