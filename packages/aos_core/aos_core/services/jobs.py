"""Shared job-origination path.

Both the API (``POST /jobs``) and the control-plane scheduler create jobs
through :func:`enqueue_job`, so there is a single code path that writes the
``Job`` row and pushes its id onto the Redis queue. The Redis client is
duck-typed (only ``lpush`` is used) — ``aos_core`` does not depend on redis.
"""

from __future__ import annotations

from ..models import Job

QUEUE = "archetypeos:jobs"


def enqueue_job(
    db,
    client,
    *,
    job_type: str,
    project_id: str | None = None,
    repository_id: str | None = None,
    payload: dict | None = None,
    priority: int = 100,
) -> Job:
    """Create a queued ``Job`` row and push its id onto ``QUEUE``."""
    job = Job(
        job_type=job_type,
        project_id=project_id,
        repository_id=repository_id,
        payload=payload or {},
        priority=priority,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    client.lpush(QUEUE, job.id)
    return job


__all__ = ["QUEUE", "enqueue_job"]
