"""Council → Decision loop (RFC-0005 Phase 2, Intelligence Layer).

A :class:`~aos_core.models.CouncilReview` is advisory: it *drafts*, it never
approves. This service closes the human gate the first live Council run named
(**LES-019**): turn a review into a draft :class:`~aos_core.models.Decision`
that links back to the review as evidence, then let a **named human** approve or
reject it — recording the transition in an
:class:`~aos_core.models.ApprovalRecord` so every approved decision carries
durable memory (approver, timestamp, rationale, evidence).

Governance teeth: a decision drafted from an **abstained** review (verdict
``Insufficient evidence`` or confidence below :data:`ABSTAIN_CONFIDENCE`) is
drafted as ``needs_evidence`` and is **not approvable** — the loop forces the
operator to gather evidence and re-draft from a cleared-floor review.

Status vocabulary rides the inherited ``AuditMixin.status`` column (no new
column / migration): ``draft`` → (``approved`` | ``rejected``);
``needs_evidence`` → (``rejected``). Manually created decisions keep their
``"active"`` default and are outside this governance gate.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import ApprovalRecord, CouncilReview, Decision, now_utc
from .council import ABSTAIN_CONFIDENCE

# Loop status vocabulary (via AuditMixin.status — no new column).
DECISION_DRAFT = "draft"
DECISION_NEEDS_EVIDENCE = "needs_evidence"
DECISION_APPROVED = "approved"
DECISION_REJECTED = "rejected"

_TITLE_MAX = 255


def _is_abstained(review: CouncilReview) -> bool:
    return review.verdict == "Insufficient evidence" or (review.confidence or 0.0) < ABSTAIN_CONFIDENCE


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _existing_draft(db: Session, review: CouncilReview) -> Decision | None:
    """Return a decision already drafted from this review, if any (idempotency)."""
    for decision in (
        db.query(Decision)
        .filter(Decision.project_id == review.project_id)
        .order_by(Decision.created_at, Decision.id)
        .all()
    ):
        meta = decision.meta or {}
        if meta.get("council_review_id") == review.id:
            return decision
    return None


def draft_decision_from_review(db: Session, *, review_id: str) -> Decision:
    """Draft a governed :class:`Decision` from a :class:`CouncilReview`.

    404s a missing review. **Idempotent**: if a decision already references this
    review (``Decision.meta["council_review_id"]``), it is returned unchanged
    rather than drafting a second. An abstained review yields a
    ``needs_evidence`` draft that cannot be approved until re-drafted from a
    cleared-floor review.
    """
    review = db.get(CouncilReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Council review not found")

    existing = _existing_draft(db, review)
    if existing is not None:
        return existing

    abstained = _is_abstained(review)
    question = (review.question or "").strip() or "Untitled council question"
    title = _truncate(f"Decision: {question}", _TITLE_MAX)

    confidence = review.confidence or 0.0
    context = (
        f"Drafted from council review {review.id}. "
        f"Verdict '{review.verdict}' at confidence {confidence:.2f}; "
        f"{len(review.agreements or [])} agreement(s), "
        f"{len(review.disagreements or [])} disagreement(s), "
        f"{len(review.unsupported_claims or [])} unsupported claim(s)."
    )

    if abstained:
        decision_text = (
            "Gather evidence first: the council abstained (insufficient evidence / "
            "confidence below the abstention floor). Do not approve — collect primary "
            "evidence and re-run the council, then re-draft from a cleared-floor review."
        )
    else:
        decision_text = f"Adopt the council direction: {review.verdict} (confidence {confidence:.2f})."

    evidence: list[dict] = [{"type": "council_review", "id": review.id}]
    for output in review.agent_outputs or []:
        evidence.append({"type": "council_agent_output", "id": output.id, "agent": output.agent_name})

    decision = Decision(
        project_id=review.project_id,
        title=title,
        context=context,
        decision=decision_text,
        alternatives=list(review.disagreements or []),
        tradeoffs=list(review.unsupported_claims or []),
        consequences=list(review.follow_up or []),
        evidence=evidence,
        confidence=confidence,
        status=DECISION_NEEDS_EVIDENCE if abstained else DECISION_DRAFT,
        meta={"council_review_id": review.id},
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def approve_decision(db: Session, *, decision_id: str, approver: str, rationale: str | None = None) -> Decision:
    """Approve a ``draft`` decision on behalf of a named human.

    404s a missing decision. Only a ``draft`` decision is approvable: a
    ``needs_evidence`` draft raises **409** naming the evidence-gathering /
    re-draft path (LES-019); an already ``approved``/``rejected`` decision raises
    **409**. On success sets ``approved_by``/``approved_at``/``status=approved``
    and writes an ``ApprovalRecord``.
    """
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status == DECISION_NEEDS_EVIDENCE:
        raise HTTPException(
            status_code=409,
            detail=(
                "Decision was drafted from an abstained council review and cannot be approved. "
                "Gather primary evidence, re-run the council, and re-draft from a cleared-floor "
                "review before approval."
            ),
        )
    if decision.status != DECISION_DRAFT:
        raise HTTPException(
            status_code=409,
            detail=f"Decision in status '{decision.status}' cannot be approved (only 'draft' is approvable).",
        )

    decision.status = DECISION_APPROVED
    decision.approved_by = approver
    decision.approved_at = now_utc()
    decision.updated_by = approver
    db.add(
        ApprovalRecord(
            project_id=decision.project_id,
            actor=approver,
            reason=rationale,
            requested_capability="decision.approve",
            target=decision_id,
            approval_status="approved",
        )
    )
    db.commit()
    db.refresh(decision)
    return decision


def reject_decision(db: Session, *, decision_id: str, approver: str, rationale: str) -> Decision:
    """Reject a ``draft`` or ``needs_evidence`` decision.

    404s a missing decision. Allowed only from ``draft`` or ``needs_evidence``;
    an already ``approved``/``rejected`` decision raises **409**. Sets
    ``status=rejected`` and writes an ``ApprovalRecord`` capturing the rationale.
    """
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status not in (DECISION_DRAFT, DECISION_NEEDS_EVIDENCE):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Decision in status '{decision.status}' cannot be rejected "
                "(only 'draft' or 'needs_evidence' decisions are rejectable)."
            ),
        )

    decision.status = DECISION_REJECTED
    decision.updated_by = approver
    db.add(
        ApprovalRecord(
            project_id=decision.project_id,
            actor=approver,
            reason=rationale,
            requested_capability="decision.reject",
            target=decision_id,
            approval_status="rejected",
        )
    )
    db.commit()
    db.refresh(decision)
    return decision


__all__ = [
    "DECISION_DRAFT",
    "DECISION_NEEDS_EVIDENCE",
    "DECISION_APPROVED",
    "DECISION_REJECTED",
    "draft_decision_from_review",
    "approve_decision",
    "reject_decision",
]
