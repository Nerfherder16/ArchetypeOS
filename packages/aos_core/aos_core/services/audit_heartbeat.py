"""Nightly audit-heartbeat service (AOS-SELFHEAL observability).

Each self-learn probe posts a heartbeat on every run so a missed run is visible.
One row per routine, upserted — the store is a live status board, not a log.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import AuditHeartbeat

# The outcomes a probe reports: a clean night, findings (it opened a review PR),
# or a failed run. Anything else is rejected at the API boundary.
HEARTBEAT_STATUSES = frozenset({"clean", "findings", "failed"})


def record_heartbeat(
    db: Session,
    *,
    routine: str,
    status: str,
    day: str,
    pr_url: str | None = None,
    detail: str | None = None,
    project_id: str | None = None,
) -> AuditHeartbeat:
    """Upsert the latest heartbeat for a (routine, project) pair.

    A global routine (the ArchetypeOS self-audit) passes ``project_id=None``; a
    per-project audit scopes the same routine to a project so their heartbeats are
    upserted independently. ``filter_by(project_id=None)`` resolves to ``IS NULL``.
    """
    row = (
        db.query(AuditHeartbeat)
        .filter_by(routine=routine, project_id=project_id)
        .one_or_none()
    )
    if row is None:
        # Build the row fully (heartbeat_status is NOT NULL) before flushing so the
        # flush both satisfies the column and surfaces a uniqueness race.
        row = AuditHeartbeat(
            routine=routine,
            project_id=project_id,
            heartbeat_status=status,
            day=day,
            pr_url=pr_url,
            detail=detail,
        )
        db.add(row)
        try:
            db.flush()
            db.commit()
            db.refresh(row)
            return row
        except IntegrityError:
            # A concurrent writer won the (routine, project) / global slot first
            # (AOS-NODE-CONSTRAINTS-001). Fall through to update the winner's row.
            db.rollback()
            row = (
                db.query(AuditHeartbeat)
                .filter_by(routine=routine, project_id=project_id)
                .one()
            )
    row.heartbeat_status = status
    row.day = day
    row.pr_url = pr_url
    row.detail = detail
    db.commit()
    db.refresh(row)
    return row


def list_heartbeats(db: Session) -> list[AuditHeartbeat]:
    """All routines' latest heartbeats, most-recently-updated first."""
    return (
        db.query(AuditHeartbeat)
        .order_by(AuditHeartbeat.updated_at.desc(), AuditHeartbeat.routine)
        .all()
    )
