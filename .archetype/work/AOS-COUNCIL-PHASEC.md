# AOS-COUNCIL-PHASEC — The decision loop: Council review → draft decision → human approve/reject → durable memory

## Status

In Progress

## Origin

Operator direction: "phase c". The first real Council run (AOS-COUNCIL-PHASEA, PR #54) proved Intelligence Phase 1 and, via **LES-019**, named the highest-signal next move: the Council abstains until it is fed the right evidence, then a human must turn a cleared-floor verdict into a **recorded, approved decision with memory**. This package builds the **Decision stage** of `docs/DECISION_LIFECYCLE.md` (the Research → Decision → Knowledge arc) and the Council→Decision link — RFC-0005 Phase 2 (Intelligence Layer). It closes the exact gap the pydantic-ai run exposed.

## Governing constraints (from CLAUDE.md / the Constitution)

- **Human approval is required** — a Council review is advisory and drafts only; a decision becomes real only when a human approves it.
- **Every significant decision needs memory** — an approved decision is durably recorded with approver, timestamp, rationale, and evidence linking back to the Council review that seeded it.
- **Evidence over opinion (LES-019 teeth)** — a decision drafted from an **abstained** review (verdict `Insufficient evidence` / confidence below the floor) is **not approvable**; the loop forces the operator to gather evidence and re-draft from a cleared-floor review.

## Verified Baseline (what already exists — do not rebuild)

- `Decision` model (`packages/aos_core/aos_core/models.py:122`) already has `approved_by`, `approved_at`, `alternatives`/`tradeoffs`/`consequences`/`evidence` (JSON), `confidence`, and inherits `AuditMixin.status` (String(64), default `"active"`). **No schema change / migration is needed.**
- `ApprovalRecord` model (`:358`) exists for the audit trail (`actor`, `reason`, `approval_status`, `target`, `requested_capability`, `output`).
- `CouncilReview` (`:307`) carries `verdict`, `confidence`, `agreements`, `disagreements`, `unsupported_claims`, `follow_up`, and `agent_outputs` (findings/concerns/confidence per persona).
- `council.py` service exposes `ABSTAIN_CONFIDENCE = 0.35` and `VERDICTS`; the abstention verdict string is `"Insufficient evidence"`.
- `apps/api/app/routes/decisions.py` has create/list/get for decisions, research-notes, recommendations; `routes/council.py` has enqueue/list/get reviews. **Neither links a review to a decision, and there is no approve/reject endpoint.**
- `DecisionRead` schema (`apps/api/app/schemas.py:208`) exposes `status` but **not** `approved_by`/`approved_at`.
- Digest (`services/digest.py`) appends typed `changes` and `draft_recommendations`; rule 5 surfaces open lessons — the model to mirror for a "decisions awaiting approval" nudge.

## Decision status vocabulary (via AuditMixin.status — no new column)

`draft` → (`approved` | `rejected`); `needs_evidence` → (`rejected`) — an abstained-review draft is a dead end until re-drafted. Define these as module constants in the new service. Manually-created decisions keep their existing `"active"` default and are outside this governance gate (the endpoints operate on loop states only).

## In-Scope Files

- **`packages/aos_core/aos_core/services/decisions.py`** (new):
  - `DECISION_DRAFT="draft"`, `DECISION_NEEDS_EVIDENCE="needs_evidence"`, `DECISION_APPROVED="approved"`, `DECISION_REJECTED="rejected"`.
  - `draft_decision_from_review(db, *, review_id) -> Decision`: load the `CouncilReview` (404 → `HTTPException`/`ValueError`); **idempotent** — if a decision already references this review (stored in `Decision.meta["council_review_id"]`), return it. Map review → Decision: `title` from the question (truncated), `context` summarizing verdict/confidence/agreements, `decision` = the proposed direction OR, when the review abstained (`verdict == "Insufficient evidence"` or `confidence < ABSTAIN_CONFIDENCE`), a "gather evidence first" note; `alternatives`/`tradeoffs`/`consequences` seeded from disagreements/unsupported_claims/follow_up; `evidence` includes `{"type":"council_review","id":review_id}` plus per-agent-output ids; `confidence = review.confidence`; `meta={"council_review_id": review_id}`; status = `DECISION_NEEDS_EVIDENCE` if abstained else `DECISION_DRAFT`.
  - `approve_decision(db, *, decision_id, approver, rationale=None) -> Decision`: 404 if missing; **409/ValueError if status != `draft`** (message must name the abstention path for `needs_evidence`). Set `approved_by=approver`, `approved_at=now_utc()`, `status=DECISION_APPROVED`; write an `ApprovalRecord` (`actor=approver`, `reason=rationale`, `requested_capability="decision.approve"`, `target=decision_id`, `approval_status="approved"`, `project_id`).
  - `reject_decision(db, *, decision_id, approver, rationale) -> Decision`: 404 if missing; allowed from `draft` or `needs_evidence`; set `status=DECISION_REJECTED`; write an `ApprovalRecord` (`approval_status="rejected"`, `reason=rationale`). Idempotent-safe.
  - Guard all transitions so an already-approved/rejected decision cannot be re-transitioned (clear error).
- **`apps/api/app/routes/decisions.py`**: add `POST /council-reviews/{review_id}/draft-decision` → `DecisionRead`; `POST /decisions/{decision_id}/approve` (body `DecisionApprove`) → `DecisionRead`; `POST /decisions/{decision_id}/reject` (body `DecisionReject`) → `DecisionRead`. Map the service's not-found → 404 and invalid-transition → 409.
- **`apps/api/app/schemas.py`**: add `approved_by: str | None` and `approved_at: datetime | None` to `DecisionRead`; add `DecisionApprove{approver: str, rationale: str | None = None}` and `DecisionReject{approver: str, rationale: str}`.
- **`packages/aos_core/aos_core/services/digest.py`**: rule 6 — decisions in status `draft`/`needs_evidence` surface as a `changes` entry (`type:"decision_pending"`) + a `draft_recommendations` nudge ("Approve or reject the drafted decision …"), mirroring the open-lessons rule. Count-agnostic.
- **`apps/api/tests/test_decisions_loop.py`** (new): draft from a **cleared-floor** review → `draft`; draft from an **abstained** review → `needs_evidence`; idempotent re-draft returns the same decision; approve a `draft` → `approved` + `approved_by`/`approved_at` set + an `ApprovalRecord` row; **approve a `needs_evidence` → 409**; approve an already-approved → 409; reject → `rejected` + record; 404s for missing review/decision. Hermetic (sqlite, `DeterministicProvider` for any review setup or construct the `CouncilReview` directly).
- **`apps/api/tests/test_digests_api.py`**: add a count-agnostic assertion that a pending drafted decision surfaces in the digest (derive the count from live state — LES-012 discipline).
- **Docs**: `docs/DECISION_LIFECYCLE.md` (mark the Decision stage implemented + the abstention-blocks-approval rule), `docs/CAPABILITY_MAP.md` (Decision-loop capability + `services/decisions.py`), `.archetype/work/AOS-COUNCIL-PHASEC.md` (this spec), state docs.

## Out-of-Scope

- **No new tables / migration** — reuse `Decision` + `ApprovalRecord`.
- **Rendering an ADR into the repo vault** (source of truth) — file/git I/O is Phase C Part 2 (follow-up). Part 1's durable memory is the approved `Decision` row + `ApprovalRecord`.
- **Frontend** — the Control Tower decision-approval view is a follow-up (folds into AOS-COUNCIL-002). No `apps/web` change; no e2e.
- Re-running the live Council; scanner gaps (LES-013/014/016/017); AuthorityGrant enforcement.

## Acceptance Criteria

- A `CouncilReview` can be turned into a draft `Decision` that links back to the review as evidence; the draft is idempotent (one per review).
- A `draft` decision can be **approved by a named human** (sets `approved_by`/`approved_at`/`status=approved` + writes an `ApprovalRecord`) or **rejected** (status + rationale record).
- A decision drafted from an **abstained** review is `needs_evidence` and **cannot be approved** (409 with a message that names the evidence-gathering path) — LES-019 operationalized.
- Draft/pending decisions surface in the digest so the human gate is active, not passive.
- api + worker suites green on the CI-scope venv; ruff full CI scope + compileall clean; guardian PASS/PASS_WITH_WARNINGS. No schema migration introduced.

## Verification (Orchestrator, independent — builder ≠ verifier)

Re-run the full api+worker suites; assert the abstention-blocks-approval 409 explicitly; confirm an `ApprovalRecord` is written on approve/reject; confirm no new Alembic migration and no `apps/web` change; ruff full CI scope + compileall; guardian.
