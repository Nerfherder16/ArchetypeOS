"""Mandatory execution envelope (AOS-AUTHORITY-ENVELOPE-001 P0-6; hardened by
AOS-AUTHORITY-HARDEN-001).

Turns the advisory authority evaluator into a structural gate. A high-impact
action is created through :func:`request_action` (which runs the policy),
approved through :func:`authorize_action`, and only then may an execution
chokepoint run it (:func:`enqueue_job` refuses a high-impact action without an
authorized envelope). Low-impact actions auto-authorize so the common path is
unchanged.

Hardening (WP4): the envelope is bound to its ``repository_id`` / ``payload_digest``
so an approval for one target cannot authorize another; :func:`consume_action` is an
ATOMIC one-use compare-and-swap (``authorized`` → ``executed``) that also stamps the
consuming ``job_id`` — concurrent consumers produce exactly one winner; and an
``expires_at`` bounds how long an approval stays valid.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import or_, update

from ..models import ActionRequest, now_utc
from .authority import requires_approval

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def request_action(
    db: "Session",
    *,
    action_class: str,
    actor: str = "system",
    agent: str | None = None,
    project_id: str | None = None,
    repository_id: str | None = None,
    target: str | None = None,
    sensitivity: str = "public",
    requested_capability: str | None = None,
    payload_digest: str | None = None,
    expires_at: datetime | None = None,
) -> ActionRequest:
    """Create an execution envelope and run the policy (raises on unknown class).

    If the policy does not require approval the envelope auto-authorizes; otherwise
    it is left ``pending`` / ``requested`` for a human decision. Bind it to the
    concrete ``repository_id`` / ``payload_digest`` so a later consume can prove the
    approval matches the action it is about to run.
    """
    needs = requires_approval(
        action_class, target=target, sensitivity=sensitivity, capability=requested_capability
    )
    ar = ActionRequest(
        action_class=action_class,
        actor=actor,
        agent=agent,
        project_id=project_id,
        repository_id=repository_id,
        target=target,
        sensitivity=sensitivity,
        requested_capability=requested_capability,
        payload_digest=payload_digest,
        expires_at=expires_at,
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


def is_authorized(ar: ActionRequest | None, *, now: datetime | None = None) -> bool:
    """True iff the envelope is authorized AND not expired (never executed/rejected)."""
    if ar is None or ar.execution_state != "authorized":
        return False
    if ar.expires_at is not None and _as_utc(ar.expires_at) <= (now or now_utc()):
        return False
    return True


def matches(ar: ActionRequest, *, action_class: str, repository_id: str | None = None,
            payload_digest: str | None = None) -> bool:
    """Verify a (typically operator-supplied) envelope is bound to THIS action.

    An approval for one repository/payload/class must not authorize another
    (AOS-AUTHORITY-HARDEN-001).
    """
    if ar.action_class != action_class:
        return False
    if repository_id is not None and ar.repository_id != repository_id:
        return False
    if payload_digest is not None and ar.payload_digest is not None and ar.payload_digest != payload_digest:
        return False
    return True


def consume_action(db: "Session", ar: ActionRequest, *, job_id: str | None = None,
                   now: datetime | None = None) -> bool:
    """Atomically consume an authorized envelope EXACTLY once (compare-and-swap).

    ``UPDATE ... WHERE execution_state='authorized' AND not expired`` — the DB row
    lock serializes concurrent consumers, so only the first flips it to ``executed``
    (and stamps ``job_id``); every other caller affects 0 rows and gets ``False``.
    The caller commits (so the consume can share a job-creation transaction and stay
    atomic with it). A rejected / expired / already-executed envelope returns False.
    """
    now = now or now_utc()
    stmt = (
        update(ActionRequest)
        .where(
            ActionRequest.id == ar.id,
            ActionRequest.execution_state == "authorized",
            or_(ActionRequest.expires_at.is_(None), ActionRequest.expires_at > now),
        )
        .values(execution_state="executed", job_id=job_id)
    )
    # synchronize_session=False: let the DB evaluate the WHERE (incl. the expiry
    # comparison) — avoids SQLAlchemy's Python-side eval comparing a naive stored
    # datetime against an aware ``now``. The caller does not use the ORM object after.
    result = db.execute(stmt, execution_options={"synchronize_session": False})
    return result.rowcount == 1


def mark_executed(db: "Session", ar: ActionRequest, *, job_id: str | None = None) -> bool:
    """Backward-compatible alias for the one-use :func:`consume_action` CAS."""
    return consume_action(db, ar, job_id=job_id)


__all__ = [
    "request_action",
    "authorize_action",
    "reject_action",
    "is_authorized",
    "matches",
    "consume_action",
    "mark_executed",
]
