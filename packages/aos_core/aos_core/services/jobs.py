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
from datetime import datetime, timedelta

from sqlalchemy import or_, update

from ..models import Job, JobOutbox, now_utc

QUEUE = "archetypeos:jobs"

# Default lease window a worker holds while executing a job. Sized well above a
# normal handler's runtime; long handlers renew (Slice 2). The reaper reclaims a
# job only after its lease has fully expired, so a live worker is never preempted.
DEFAULT_LEASE_SECONDS = 300

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


def claim_job(
    db,
    job_id: str,
    worker_id: str,
    *,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> bool:
    """Atomically claim a job with a lease (compare-and-swap). Returns True if won.

    The claim only succeeds when the job is ``queued``/``running`` AND its lease is
    absent or expired, so two workers racing the same id cannot both win — the
    second sees ``rowcount == 0`` and drops it (finding P0-1). Claiming increments
    ``attempts`` and stamps ``started_at``.
    """
    now = now or now_utc()
    stmt = (
        update(Job)
        .where(
            Job.id == job_id,
            Job.status.in_(("queued", "running")),
            or_(Job.lease_expires_at.is_(None), Job.lease_expires_at < now),
        )
        .values(
            status="running",
            claimed_by=worker_id,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
            started_at=now,
            attempts=Job.attempts + 1,
        )
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount == 1


def renew_lease(
    db,
    job_id: str,
    worker_id: str,
    *,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> bool:
    """Extend the lease for a job this worker still holds. Returns True if renewed."""
    now = now or now_utc()
    stmt = (
        update(Job)
        .where(Job.id == job_id, Job.claimed_by == worker_id, Job.status == "running")
        .values(lease_expires_at=now + timedelta(seconds=lease_seconds))
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount == 1


def complete_job(db, job_id: str, result: dict | None) -> None:
    """Mark a job completed and release its lease (same session as the handler)."""
    job = db.get(Job, job_id)
    if job is None:
        return
    now = now_utc()
    job.status = "completed"
    job.result = result
    job.finished_at = now
    job.updated_at = now
    job.claimed_by = None
    job.lease_expires_at = None
    db.commit()


def release_for_retry(db, job_id: str) -> None:
    """Reset a job to ``queued`` and release its lease so it can be re-claimed."""
    job = db.get(Job, job_id)
    if job is None:
        return
    job.status = "queued"
    job.claimed_by = None
    job.lease_expires_at = None
    job.updated_at = now_utc()
    db.commit()


def fail_job(db, job_id: str, error: str | None, *, status: str = "failed") -> None:
    """Mark a job terminal (``failed`` or ``dead_letter``) and release its lease."""
    job = db.get(Job, job_id)
    if job is None:
        return
    now = now_utc()
    job.status = status
    job.error = error
    job.finished_at = now
    job.updated_at = now
    job.claimed_by = None
    job.lease_expires_at = None
    db.commit()


def dead_letter_job(db, job_id: str, error: str | None) -> None:
    """Move a job to the ``dead_letter`` terminal state (retry budget exhausted)."""
    fail_job(db, job_id, error, status="dead_letter")


def reap_expired_leases(db, client, *, max_attempts: int, now: datetime | None = None) -> int:
    """Recover jobs whose worker died mid-execution (lease expired while running).

    Under the retry budget, the job is reset to ``queued`` and its outbox row is
    re-armed (``delivered_at = NULL``) so the single dispatch path redelivers it;
    over budget it is marked ``failed``. Returns the number re-queued for retry.
    """
    now = now or now_utc()
    stale = (
        db.query(Job)
        .filter(
            Job.status == "running",
            Job.lease_expires_at.isnot(None),
            Job.lease_expires_at < now,
        )
        .all()
    )
    requeued = 0
    for job in stale:
        job.claimed_by = None
        job.lease_expires_at = None
        if (job.attempts or 0) < max_attempts:
            job.status = "queued"
            outbox = db.query(JobOutbox).filter(JobOutbox.job_id == job.id).one_or_none()
            if outbox is None:
                db.add(JobOutbox(job_id=job.id))
            else:
                outbox.delivered_at = None  # re-arm for redelivery
            requeued += 1
        else:
            job.status = "dead_letter"
            job.error = "lease expired: max attempts exhausted"
            job.finished_at = now
    db.commit()
    # Deliver any re-armed rows now that the broker call is outside the reap txn.
    dispatch_outbox(db, client)
    return requeued


def reconcile(db, client, *, max_attempts: int, now: datetime | None = None) -> dict:
    """One repair sweep: deliver, reap, and restore jobs stranded from the broker.

    Beyond the per-tick drain + reap, this catches the case the outbox alone
    cannot: a job marked ``queued`` and previously delivered whose id is no longer
    in the Redis list (the broker was flushed / lost its data). Such jobs are
    re-armed and redelivered. Returns a summary count for operator surfacing.
    """
    now = now or now_utc()
    delivered = dispatch_outbox(db, client)
    requeued = reap_expired_leases(db, client, max_attempts=max_attempts, now=now)

    restored = 0
    try:
        raw = client.lrange(QUEUE, 0, -1)
    except Exception:  # noqa: BLE001 — broker unavailable; the outbox still guarantees eventual delivery
        raw = None
    if raw is not None:
        in_queue = {v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else v for v in raw}
        for job in db.query(Job).filter(Job.status == "queued").all():
            if job.id in in_queue:
                continue
            outbox = db.query(JobOutbox).filter(JobOutbox.job_id == job.id).one_or_none()
            if outbox is None:
                db.add(JobOutbox(job_id=job.id))
            else:
                outbox.delivered_at = None  # re-arm for redelivery
            restored += 1
        if restored:
            db.commit()
            delivered += dispatch_outbox(db, client)
    return {"delivered": delivered, "requeued": requeued, "restored": restored}


__all__ = [
    "QUEUE",
    "DEFAULT_LEASE_SECONDS",
    "enqueue_job",
    "dispatch_outbox",
    "reconcile",
    "claim_job",
    "renew_lease",
    "complete_job",
    "release_for_retry",
    "fail_job",
    "dead_letter_job",
    "reap_expired_leases",
]
