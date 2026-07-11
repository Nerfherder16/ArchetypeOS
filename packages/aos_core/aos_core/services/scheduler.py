"""Control-plane scheduler tick (AOS-SCHEDULER-RELIABILITY-001, finding P0-2).

:func:`run_due_schedules` finds enabled schedules whose ``next_run_at`` has
arrived and materializes each due occurrence into a queued job — exactly once.
Reliability:

- **Exactly-once occurrence.** Each firing writes a ``ScheduleFire`` unique on
  ``(schedule_id, nominal_fire_at)``. A duplicate (a second replica, or a
  crash-and-retry that re-observes the same due time) hits the unique constraint
  and is skipped instead of enqueuing a second job.
- **Single-firer under replicas.** On Postgres the due query claims rows with
  ``FOR UPDATE SKIP LOCKED`` so concurrent schedulers take disjoint work; the
  ``ScheduleFire`` uniqueness is the hard backstop regardless of dialect.
- **Nominal cadence, no drift.** ``next_run_at`` advances from the nominal fire
  time (not the wall-clock tick), and missed occurrences are coalesced (fired once,
  then advanced to the next future nominal) rather than replayed or drifting.

It decides and writes (control plane); it never executes jobs (the worker's role).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from ..models import Schedule, ScheduleFire
from .jobs import enqueue_job


def _as_utc(value: datetime) -> datetime:
    """Normalize to timezone-aware UTC (sqlite drops tzinfo; Postgres preserves it)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _advance(schedule: Schedule, now: datetime) -> None:
    """Advance a schedule to its next FUTURE nominal fire time (coalescing misses)."""
    interval = timedelta(seconds=schedule.interval_seconds)
    schedule.last_run_at = now
    nxt = _as_utc(schedule.next_run_at) + interval
    now = _as_utc(now)
    # Coalesce: if the scheduler was down for several intervals, fire once (already
    # done by the caller) and skip the backlog rather than replaying each occurrence.
    while nxt <= now:
        nxt += interval
    schedule.next_run_at = nxt


def run_due_schedules(db, client, now: datetime) -> list[str]:
    """Enqueue a job for every enabled, due schedule (exactly once); return new job ids."""
    query = db.query(Schedule).filter(
        Schedule.enabled.is_(True), Schedule.next_run_at <= now
    )
    # Single-firer optimization on Postgres; the ScheduleFire uniqueness is the
    # real guarantee, so sqlite (hermetic tests) is correct without it.
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        query = query.with_for_update(skip_locked=True)
    due = query.all()

    job_ids: list[str] = []
    for schedule in due:
        job_id = _fire_once(db, client, schedule, now)
        if job_id is not None:
            job_ids.append(job_id)
    return job_ids


def _fire_once(db, client, schedule: Schedule, now: datetime) -> str | None:
    """Fire a single schedule's due occurrence exactly once; return the job id or None."""
    schedule_id = schedule.id
    nominal = schedule.next_run_at

    fire = ScheduleFire(schedule_id=schedule_id, nominal_fire_at=nominal)
    db.add(fire)
    try:
        db.flush()  # claim this (schedule, nominal) occurrence
    except IntegrityError:
        # Already fired (another replica, or a retry re-observing the same due time).
        # Advance so we do not keep re-checking it, but enqueue nothing.
        db.rollback()
        schedule = db.get(Schedule, schedule_id)
        if schedule is not None:
            _advance(schedule, now)
            db.commit()
        return None

    job = enqueue_job(
        db,
        client,
        job_type=schedule.job_type,
        project_id=schedule.project_id,
        payload=schedule.payload,
    )  # commits the job + outbox + this ScheduleFire together
    fire.job_id = job.id
    _advance(schedule, now)
    db.commit()
    return job.id


__all__ = ["run_due_schedules"]
