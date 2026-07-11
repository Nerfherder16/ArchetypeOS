"""Evolution Engine: decision staleness detection + advisory re-evaluation.

RFC-0015 Wave C (AOS-EVOLVE-001). Closes the Evolution stage of AOS-REVIEW-003
(a name-only engine) and serves Article X (Continuous Evolution) and Article
XVIII (a :class:`~aos_core.models.Decision` is a hypothesis until re-validated,
not a permanent fact). Today nothing revisits an ``approved`` decision as time
passes or as the evidence that justified it changes.

``find_stale_decisions`` is a pure, deterministic read: it considers only
**approved** decisions (draft/needs_evidence/rejected decisions are not yet —
or no longer — governing anything, so staleness does not apply to them) and
flags one of two independent conditions, either of which can fire alone or
together:

- **age**: ``approved_at`` is older than ``max_age_days`` relative to ``now``.
- **evidence supersession**: the decision cites a
  :class:`~aos_core.models.ResearchNote` (``evidence`` entry
  ``{"type": "research_note", "id": ...}``) for which a strictly NEWER note on
  the exact same ``question`` now exists — the fact base the decision was
  approved on has since been updated.

``now`` is always accepted as an override (defaulting to
:func:`~aos_core.models.now_utc`) so the pass is deterministic and hermetic in
tests — no wall-clock coupling.

``reevaluate_decision`` is **advisory only** (Article IX: human approval gates
destructive/status-changing actions; this module performs neither). It stamps
``meta["reevaluation_requested_at"]`` / ``meta["stale_reason"]`` and returns
the decision unchanged otherwise — ``status`` is never mutated, nothing is
deleted, and no re-approval or auto-rejection happens here. Re-flagging is
idempotent: it only ever updates the timestamp (and the reason, when a new one
is supplied), never duplicates state.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Decision, ResearchNote, now_utc

DEFAULT_MAX_AGE_DAYS = 90


def _as_utc(value: datetime) -> datetime:
    """Normalize to timezone-aware UTC (sqlite drops tzinfo; Postgres preserves it)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _age_days(*, approved_at, now) -> int | None:
    if approved_at is None:
        return None
    return (_as_utc(now) - _as_utc(approved_at)).days


def _superseding_note(db: Session, note: ResearchNote) -> ResearchNote | None:
    """Return a strictly newer note on the same question, if one exists.

    A note with no recorded ``question`` cannot be meaningfully compared
    against other notes (an empty/NULL question is not "the same question" as
    another empty/NULL question), so it never triggers supersession.
    """
    if not note.question:
        return None
    return (
        db.query(ResearchNote)
        .filter(
            ResearchNote.project_id == note.project_id,
            ResearchNote.question == note.question,
            ResearchNote.created_at > note.created_at,
            ResearchNote.id != note.id,
        )
        .order_by(ResearchNote.created_at.desc())
        .first()
    )


def _supersession_reasons(db: Session, decision: Decision) -> list[str]:
    reasons: list[str] = []
    for pointer in decision.evidence or []:
        if not isinstance(pointer, dict) or pointer.get("type") != "research_note":
            continue
        note_id = pointer.get("id")
        if not note_id:
            continue
        note = db.get(ResearchNote, note_id)
        if note is None:
            continue
        newer = _superseding_note(db, note)
        if newer is not None:
            reasons.append(
                f"evidence research_note {note.id} superseded by newer note "
                f"{newer.id} on the same question ({newer.created_at.isoformat()})"
            )
    return reasons


def find_stale_decisions(
    db: Session,
    *,
    project_id: str | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    now=None,
) -> list[dict]:
    """Return staleness records for every stale, **approved** decision.

    Deterministic: ``now`` defaults to :func:`~aos_core.models.now_utc` but a
    caller (tests) may inject a fixed clock. Only ``status == "approved"``
    decisions are considered — a draft/needs_evidence/rejected decision is
    never reported. Each returned record is
    ``{"decision_id", "title", "reason", "age_days"}``; ``reason`` documents
    age staleness, evidence-supersession staleness, or both when both apply.
    """
    now = _as_utc(now or now_utc())
    query = db.query(Decision).filter(Decision.status == "approved")
    if project_id is not None:
        query = query.filter(Decision.project_id == project_id)

    results: list[dict] = []
    for decision in query.order_by(Decision.created_at, Decision.id).all():
        age_days = _age_days(approved_at=decision.approved_at, now=now)
        stale_by_age = age_days is not None and age_days > max_age_days

        supersession_reasons = _supersession_reasons(db, decision)
        stale_by_supersession = bool(supersession_reasons)

        if not stale_by_age and not stale_by_supersession:
            continue

        reason_parts: list[str] = []
        if stale_by_age:
            reason_parts.append(
                f"approved {age_days}d ago, older than the {max_age_days}d staleness threshold"
            )
        reason_parts.extend(supersession_reasons)

        results.append(
            {
                "decision_id": decision.id,
                "title": decision.title,
                "reason": "; ".join(reason_parts),
                "age_days": age_days,
            }
        )
    return results


def reevaluate_decision(db: Session, *, decision_id: str, reason: str | None = None, now=None) -> Decision:
    """Advisory-flag a decision for re-evaluation (Article IX: no status mutation).

    404s a missing decision. Sets ``meta["reevaluation_requested_at"]`` (an ISO
    timestamp derived from ``now``, defaulting to
    :func:`~aos_core.models.now_utc`) and, when ``reason`` is supplied,
    ``meta["stale_reason"]``. Never changes ``status`` and never deletes the
    decision. Idempotent: calling again just refreshes the timestamp (and the
    reason, if a new one is given) rather than accumulating duplicate state.
    The ``meta`` dict is reassigned wholesale (``{**old, **updates}``) so
    SQLAlchemy detects the JSON-column mutation.
    """
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    now = _as_utc(now or now_utc())
    updates: dict = {"reevaluation_requested_at": now.isoformat()}
    if reason is not None:
        updates["stale_reason"] = reason

    decision.meta = {**(decision.meta or {}), **updates}
    db.commit()
    db.refresh(decision)
    return decision


__all__ = [
    "DEFAULT_MAX_AGE_DAYS",
    "find_stale_decisions",
    "reevaluate_decision",
]
