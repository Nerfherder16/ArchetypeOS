"""Shared, durable job-origination path (AOS-JOBS-RELIABILITY-001, RFC-0014).

Both the API (``POST /jobs``) and the control-plane scheduler create jobs
through :func:`enqueue_job`, so there is a single code path that writes the
``Job`` row and its delivery intent.

Durability (finding P0-1): the ``Job`` and a ``JobOutbox`` row are committed in
**one** transaction, *before* any Redis call. Delivery to the Redis queue is a
separate, best-effort step: on the happy path :func:`enqueue_job` pushes
immediately (preserving latency), but if Redis is unavailable the job is already
durable and the outbox row stays undelivered — :func:`dispatch_outbox` (run by
the worker loop) delivers it later. A Redis outage can no longer orphan a queued
job, and origination never fails because Redis is down.

The Redis client is duck-typed (only ``lpush`` is used) — ``aos_core`` does not
depend on redis.
"""

from __future__ import annotations

import logging

from ..models import Job, JobOutbox, now_utc

QUEUE = "archetypeos:jobs"

logger = logging.getLogger("archetypeos.jobs")


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
    """Create a queued ``Job`` + its outbox row atomically, then best-effort deliver.

    The job is durable once this returns, whether or not Redis accepted the push.
    """
    job = Job(
        job_type=job_type,
        project_id=project_id,
        repository_id=repository_id,
        payload=payload or {},
        priority=priority,
        status="queued",
    )
    db.add(job)
    db.flush()  # assign job.id so the outbox row can reference it in the same txn
    outbox = JobOutbox(job_id=job.id)
    db.add(outbox)
    db.commit()  # Job + JobOutbox committed together — durable before any Redis touch
    db.refresh(job)

    # Best-effort immediate delivery keeps happy-path latency. A failure here does
    # not lose the job (it is already committed) and does not fail origination —
    # dispatch_outbox will deliver the undelivered row on a later worker tick.
    _deliver(db, client, outbox)
    return job


def _deliver(db, client, outbox: JobOutbox) -> bool:
    """Push one outbox row's job id to Redis and stamp ``delivered_at``.

    Returns ``True`` on delivery, ``False`` if Redis was unavailable (the row is
    left undelivered for a later retry). Never raises on a Redis failure.
    """
    try:
        client.lpush(QUEUE, outbox.job_id)
    except Exception:  # noqa: BLE001 — any Redis/transport error defers delivery
        logger.warning("outbox delivery deferred (redis unavailable): job %s", outbox.job_id)
        return False
    outbox.delivered_at = now_utc()
    db.commit()
    return True


def dispatch_outbox(db, client, *, limit: int = 100) -> int:
    """Deliver undelivered outbox rows to the Redis queue; return the count delivered.

    Ordered oldest-first. Stops at the first Redis failure so the remaining rows
    are retried on the next call rather than spinning against a dead broker.
    """
    rows = (
        db.query(JobOutbox)
        .filter(JobOutbox.delivered_at.is_(None))
        .order_by(JobOutbox.created_at, JobOutbox.id)
        .limit(limit)
        .all()
    )
    delivered = 0
    for row in rows:
        if _deliver(db, client, row):
            delivered += 1
        else:
            break  # broker unavailable — leave the rest undelivered for next tick
    return delivered


__all__ = ["QUEUE", "enqueue_job", "dispatch_outbox"]
