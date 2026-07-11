"""Mandatory execution envelope (AOS-AUTHORITY-ENVELOPE-001, finding P0-6).

Turns the advisory authority evaluator into a structural gate. A high-impact
action is created through :func:`request_action` (which runs the policy),
approved through :func:`authorize_action`, and only then may an execution
chokepoint run it (:func:`enqueue_job` refuses a high-impact action without an
authorized envelope). Low-impact actions auto-authorize so the common path is
unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import ActionRequest
from .authority import requires_approval

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


def request_action(
    db: "Session",
    *,
    action_class: str,
    actor: str = "system",
    agent: str | None = None,
    project_id: str | None = None,
    target: str | None = None,
    sensitivity: str = "public",
    requested_capability: str | None = None,
    payload_digest: str | None = None,
) -> ActionRequest:
    """Create an execution envelope and run the policy (raises on unknown class).

    If the policy does not require approval the envelope auto-authorizes; otherwise
    it is left ``pending`` / ``requested`` for a human decision.
    """
    needs = requires_approval(
        action_class, target=target, sensitivity=sensitivity, capability=requested_capability
    )
    ar = ActionRequest(
        action_class=action_class,
        actor=actor,
        agent=agent,
        project_id=project_id,
        target=target,
        sensitivity=sensitivity,
        requested_capability=requested_capability,
        payload_digest=payload_digest,
        policy_decision="needs_approval" if needs else "allow",
        approval_state="pending" if needs else "auto_approved",
        execution_state="requested" if needs else "authorized",
    )
    db.add(ar)
    db.commit()
    db.refresh(ar)
    return ar


def authorize_action(db: "Session", action_id: str, *, approver: str = "operator") -> ActionRequest | None:
    """Operator approval: flip a pending envelope to authorized. None if unknown."""
    ar = db.get(ActionRequest, action_id)
    if ar is None:
        return None
    if ar.approval_state == "pending":
        ar.approval_state = "approved"
        ar.execution_state = "authorized"
        ar.updated_by = approver
        db.commit()
        db.refresh(ar)
    return ar


def reject_action(db: "Session", action_id: str, *, approver: str = "operator") -> ActionRequest | None:
    """Operator rejection: the action may never execute. None if unknown."""
    ar = db.get(ActionRequest, action_id)
    if ar is None:
        return None
    ar.approval_state = "rejected"
    ar.execution_state = "rejected"
    ar.updated_by = approver
    db.commit()
    db.refresh(ar)
    return ar


def is_authorized(ar: ActionRequest | None) -> bool:
    return ar is not None and ar.execution_state == "authorized"


def mark_executed(db: "Session", ar: ActionRequest) -> None:
    ar.execution_state = "executed"
    # Committed by the caller's transaction (e.g. enqueue_job) so the envelope's
    # executed state and the job it authorized commit together.


__all__ = [
    "request_action",
    "authorize_action",
    "reject_action",
    "is_authorized",
    "mark_executed",
]
