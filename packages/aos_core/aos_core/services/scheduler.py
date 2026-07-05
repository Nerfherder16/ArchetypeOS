"""Control-plane scheduler tick.

:func:`run_due_schedules` is the tested unit of the scheduler service: it finds
enabled schedules whose ``next_run_at`` has arrived, materializes each into a
queued job via the shared :func:`enqueue_job` path, and advances the schedule's
``last_run_at`` / ``next_run_at``. It decides and writes (control plane); it
never executes jobs (that is the worker's role).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..models import Schedule
from .jobs import enqueue_job


def run_due_schedules(db, client, now: datetime) -> list[str]:
    """Enqueue a job for every enabled, due schedule; return the new job ids."""
    due = (
        db.query(Schedule)
        .filter(Schedule.enabled.is_(True), Schedule.next_run_at <= now)
        .all()
    )
    job_ids: list[str] = []
    for schedule in due:
        job = enqueue_job(
            db,
            client,
            job_type=schedule.job_type,
            project_id=schedule.project_id,
            payload=schedule.payload,
        )
        job_ids.append(job.id)
        schedule.last_run_at = now
        schedule.next_run_at = now + timedelta(seconds=schedule.interval_seconds)
    db.commit()
    return job_ids


__all__ = ["run_due_schedules"]
