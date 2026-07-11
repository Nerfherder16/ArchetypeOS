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
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import or_, update

from ..models import ActionRequest, Job, JobOutbox, Node, now_utc
from .authority import requires_approval
from .job_requirements import get_requirement
from .routing import node_eligibility, route_job

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
    action_class: str = "read_only",
    sensitivity: str = "public",
    action_request: ActionRequest | None = None,
) -> Job:
    """Create a queued ``Job`` + its outbox row atomically, then best-effort deliver.

    The job is durable once this returns, whether or not Redis accepted the push.

    Authority gate (finding P0-6): origination is the single execution chokepoint,
    so a **high-impact** action (write/deploy/destructive/sensitive egress) is
    refused here unless it carries an authorized ``ActionRequest`` for the same
    class. Low-impact ``read_only`` jobs (the default, and every current job type)
    pass straight through, so the common path is unchanged.
    """
    if requires_approval(action_class, sensitivity=sensitivity):
        if (
            action_request is None
            or action_request.action_class != action_class
            or action_request.execution_state != "authorized"
        ):
            raise PermissionError(
                f"job_type {job_type!r} ({action_class}) requires an authorized ActionRequest"
            )

    job = Job(
        job_type=job_type,
        project_id=project_id,
        repository_id=repository_id,
        payload=payload or {},
        priority=priority,
        status="queued",
    )
    # AOS-NODE-EXECUTION-001: derive the job's execution requirements server-side
    # (from the registry, never the client) and route to an eligible node before
    # delivery, persisting the decision. An unknown job type has no capability
    # requirement (WP4 rejects unknown types before this point). ``sensitivity``
    # from the registry drives routing; the caller's ``sensitivity`` arg still
    # governs the authority check above.
    requirement = get_requirement(job_type)
    if requirement is not None:
        job.required_capability = requirement.capability
        job.sensitivity = requirement.sensitivity
        job.requires_write = requirement.requires_write
    else:
        job.sensitivity = sensitivity
    db.add(job)
    db.flush()  # assign job.id so the outbox row can reference it in the same txn
    _route(db, job)
    outbox = JobOutbox(job_id=job.id)
    db.add(outbox)
    if action_request is not None:
        # The envelope is consumed by exactly this job, committed in the same txn.
        action_request.execution_state = "executed"
    db.commit()  # Job + JobOutbox (+ envelope) committed together — durable before Redis
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


def _route(db, job: Job, *, now: datetime | None = None) -> None:
    """Route a job to an eligible node and persist the decision (AOS-NODE-EXECUTION-001).

    Sets ``assigned_node_id`` + ``routing_status`` (``routed`` / ``no_eligible_node``)
    + a deterministic ``routing_explanation`` + ``routed_at``. A job with no eligible
    node stays ``queued`` and unassigned — visibly waiting, never lost — and the
    reroute sweep assigns it once a node becomes eligible.
    """
    now = now or now_utc()
    decision = route_job(
        db,
        required_capability=job.required_capability,
        sensitivity=job.sensitivity,
        requires_write=job.requires_write,
        now=now,
    )
    job.assigned_node_id = decision.node_id
    job.routing_status = "routed" if decision.node_id is not None else "no_eligible_node"
    job.routing_explanation = decision.explanation
    job.routed_at = now


def reroute_waiting_jobs(db, *, now: datetime | None = None) -> int:
    """Re-route jobs that have no live eligible node assignment; return count routed.

    Covers two cases (finding: "restored node health allows waiting jobs to route";
    "node failure expires assignment"): a ``no_eligible_node`` job for which a node
    has since become eligible, and a still-``queued`` job whose assigned node is gone
    or no longer eligible. Only unclaimed queued jobs are touched — a running job's
    recovery is the WP1 lease reaper's job, not this sweep's.
    """
    now = now or now_utc()
    routed = 0
    waiting = (
        db.query(Job)
        .filter(Job.status == "queued", Job.claimed_by.is_(None))
        .all()
    )
    for job in waiting:
        # A job assigned to a node that is still eligible needs no re-routing.
        if job.assigned_node_id is not None:
            node = db.get(Node, job.assigned_node_id)
            if node is not None:
                ok, _reason = node_eligibility(
                    node,
                    required_capability=job.required_capability,
                    sensitivity=job.sensitivity,
                    requires_write=job.requires_write,
                    now=now,
                )
                if ok:
                    continue
        before = job.assigned_node_id
        _route(db, job, now=now)
        if job.assigned_node_id is not None and job.assigned_node_id != before:
            routed += 1
    db.commit()
    return routed


@dataclass(frozen=True)
class Claim:
    """Proof of active ownership returned by a winning :func:`claim_job`.

    Every subsequent worker-side transition for this job must present the
    ``claim_token`` so a stale worker (one whose lease expired and whose job was
    reclaimed) cannot mutate it — the transition compare-and-swaps on the token.
    """

    job_id: str
    worker_id: str
    claim_token: str
    lease_expires_at: datetime


def claim_job(
    db,
    job_id: str,
    worker_id: str,
    *,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> Claim | None:
    """Atomically claim a job with a lease + fresh fencing token (compare-and-swap).

    Returns a :class:`Claim` if won, else ``None``. The claim only succeeds when the
    job is ``queued``/``running`` AND its lease is absent or expired, so two workers
    racing the same id cannot both win — the second sees ``rowcount == 0`` and drops
    it (finding P0-1). Winning mints a NEW ``claim_token`` (AOS-JOB-FENCING-001), so
    any previously-issued token for this job is instantly stale. Claiming increments
    ``attempts`` and stamps ``started_at``.
    """
    now = now or now_utc()
    token = uuid4().hex
    expires = now + timedelta(seconds=lease_seconds)
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
            claim_token=token,
            lease_expires_at=expires,
            started_at=now,
            attempts=Job.attempts + 1,
        )
    )
    result = db.execute(stmt)
    db.commit()
    if result.rowcount == 1:
        return Claim(job_id=job_id, worker_id=worker_id, claim_token=token, lease_expires_at=expires)
    return None


def claim_job_for_node(
    db,
    job_id: str,
    worker_id: str,
    *,
    node: Node | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> Claim | None:
    """Claim a job ONLY if this node is assigned + eligible (AOS-NODE-EXECUTION-001).

    Layers node routing onto the WP1 fencing claim:

    * **Assignment** — the claim CAS is gated on ``assigned_node_id IN (NULL, this
      node)``, so a worker can never claim a job routed to a *different* node (the
      classic global-queue bypass). A worker with no node identity (``node=None``)
      can only claim unassigned jobs.
    * **Eligibility** — when the claiming node is known, it is re-validated at claim
      time (capability ∈ node caps ∧ sensitivity ≤ ceiling ∧ write ≤ policy ∧ fresh
      health), NOT trusted from the origination-time routing decision.
    * **Fencing** — on success a fresh ``claim_token`` is minted exactly as
      :func:`claim_job`, so all the WP1 ownership guarantees still hold.

    Returns a :class:`Claim` if won, else ``None``.
    """
    now = now or now_utc()
    claiming_node_id = node.id if node is not None else None

    job = db.get(Job, job_id)
    if job is None:
        return None
    # Assignment: refuse a job routed to another node before touching the row.
    if job.assigned_node_id is not None and job.assigned_node_id != claiming_node_id:
        return None
    # Eligibility: only enforceable when we know which node is claiming.
    if node is not None:
        eligible, _reason = node_eligibility(
            node,
            required_capability=job.required_capability,
            sensitivity=job.sensitivity,
            requires_write=job.requires_write,
            now=now,
        )
        if not eligible:
            return None

    token = uuid4().hex
    expires = now + timedelta(seconds=lease_seconds)
    stmt = (
        update(Job)
        .where(
            Job.id == job_id,
            Job.status.in_(("queued", "running")),
            or_(Job.lease_expires_at.is_(None), Job.lease_expires_at < now),
            or_(Job.assigned_node_id.is_(None), Job.assigned_node_id == claiming_node_id),
        )
        .values(
            status="running",
            claimed_by=worker_id,
            claim_token=token,
            lease_expires_at=expires,
            started_at=now,
            attempts=Job.attempts + 1,
        )
    )
    result = db.execute(stmt)
    db.commit()
    if result.rowcount == 1:
        return Claim(job_id=job_id, worker_id=worker_id, claim_token=token, lease_expires_at=expires)
    return None


def renew_lease(
    db,
    claim: Claim,
    *,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> bool:
    """Extend the lease for a job this worker still owns. Returns True if renewed.

    Guarded by the fencing token: if the job was reclaimed (new token) or moved off
    ``running``, this affects 0 rows and the owner learns it has lost the lease.
    """
    now = now or now_utc()
    stmt = (
        update(Job)
        .where(
            Job.id == claim.job_id,
            Job.claimed_by == claim.worker_id,
            Job.claim_token == claim.claim_token,
            Job.status == "running",
        )
        .values(lease_expires_at=now + timedelta(seconds=lease_seconds))
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount == 1


def _owned_transition(db, claim: Claim, values: dict) -> bool:
    """Apply a state transition only if ``claim`` still owns the running job (CAS).

    Returns True if the row was updated (ownership proven), False if a stale worker
    tried to mutate a job it no longer holds. Clears the lease + token as part of any
    terminal/requeue transition so the fence is released cleanly.
    """
    stmt = (
        update(Job)
        .where(
            Job.id == claim.job_id,
            Job.claimed_by == claim.worker_id,
            Job.claim_token == claim.claim_token,
            Job.status == "running",
        )
        .values(**values)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount == 1


def complete_job(db, job_id: str, result: dict | None, *, claim: Claim | None = None) -> bool:
    """Mark a job completed and release its lease — only if ``claim`` still owns it.

    Fenced (AOS-JOB-FENCING-001): a stale worker whose lease expired and whose job
    was reclaimed cannot overwrite the newer worker's result — the CAS affects 0
    rows and this returns ``False``. When ``claim`` is omitted (legacy/unfenced
    callers) the completion falls back to an id-only update for backward compat.
    """
    now = now_utc()
    values = dict(status="completed", result=result, finished_at=now, updated_at=now,
                  claimed_by=None, claim_token=None, lease_expires_at=None)
    if claim is not None:
        return _owned_transition(db, claim, values)
    job = db.get(Job, job_id)
    if job is None:
        return False
    for k, v in values.items():
        setattr(job, k, v)
    db.commit()
    return True


def release_for_retry(db, job_id: str, *, claim: Claim | None = None) -> bool:
    """Reset a job to ``queued`` and release its lease so it can be re-claimed.

    Fenced when ``claim`` is supplied: a stale worker cannot requeue a job it lost.
    """
    values = dict(status="queued", claimed_by=None, claim_token=None,
                  lease_expires_at=None, updated_at=now_utc())
    if claim is not None:
        return _owned_transition(db, claim, values)
    job = db.get(Job, job_id)
    if job is None:
        return False
    for k, v in values.items():
        setattr(job, k, v)
    db.commit()
    return True


def fail_job(db, job_id: str, error: str | None, *, status: str = "failed", claim: Claim | None = None) -> bool:
    """Mark a job terminal (``failed`` or ``dead_letter``) and release its lease.

    Fenced when ``claim`` is supplied: a stale worker cannot fail a job it lost.
    """
    now = now_utc()
    values = dict(status=status, error=error, finished_at=now, updated_at=now,
                  claimed_by=None, claim_token=None, lease_expires_at=None)
    if claim is not None:
        return _owned_transition(db, claim, values)
    job = db.get(Job, job_id)
    if job is None:
        return False
    for k, v in values.items():
        setattr(job, k, v)
    db.commit()
    return True


def dead_letter_job(db, job_id: str, error: str | None, *, claim: Claim | None = None) -> bool:
    """Move a job to the ``dead_letter`` terminal state (retry budget exhausted)."""
    return fail_job(db, job_id, error, status="dead_letter", claim=claim)


def rearm_outbox(db, job_id: str) -> None:
    """Re-arm (or create) a job's outbox row so the dispatcher redelivers it.

    Used by the fenced retry path: a job reset to ``queued`` must be redelivered
    through the durable outbox rather than a direct Redis push, so retry survives a
    broker outage exactly like origination does (RFC-0014).
    """
    outbox = db.query(JobOutbox).filter(JobOutbox.job_id == job_id).one_or_none()
    if outbox is None:
        db.add(JobOutbox(job_id=job_id))
    else:
        outbox.delivered_at = None
    db.commit()


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
        job.claim_token = None  # AOS-JOB-FENCING-001: kill the dead owner's fence
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
    # AOS-NODE-EXECUTION-001: assign waiting jobs to a node that has since become
    # eligible, and re-route jobs whose assigned node is gone/unhealthy.
    rerouted = reroute_waiting_jobs(db, now=now)
    return {"delivered": delivered, "requeued": requeued, "restored": restored, "rerouted": rerouted}


__all__ = [
    "QUEUE",
    "DEFAULT_LEASE_SECONDS",
    "Claim",
    "enqueue_job",
    "dispatch_outbox",
    "reconcile",
    "reroute_waiting_jobs",
    "claim_job",
    "claim_job_for_node",
    "renew_lease",
    "complete_job",
    "release_for_retry",
    "fail_job",
    "dead_letter_job",
    "rearm_outbox",
    "reap_expired_leases",
]
