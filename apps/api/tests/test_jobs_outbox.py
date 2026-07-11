"""AOS-JOBS-RELIABILITY-001 / RFC-0014 Slice 1 — durable job origination.

Proves the transactional outbox closes finding P0-1: a ``Job`` and its delivery
intent commit atomically, a Redis outage at origination cannot lose or fail the
job, and the dispatcher delivers deferred rows once the broker is reachable.
"""

from __future__ import annotations

from aos_core.models import Job, JobOutbox
from aos_core.services.jobs import QUEUE, dispatch_outbox, enqueue_job


class FakeRedis:
    """Captures lpush calls; a healthy broker."""

    def __init__(self) -> None:
        self.queue: list[tuple[str, str]] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append((name, value))


class DeadRedis:
    """A broker that is down — every lpush raises, as a real outage would."""

    def __init__(self) -> None:
        self.calls = 0

    def lpush(self, name: str, value: str) -> None:
        self.calls += 1
        raise ConnectionError("redis unavailable")


def test_enqueue_creates_job_and_outbox_atomically(db_session):
    client = FakeRedis()
    job = enqueue_job(db_session, client, job_type="test")

    row = db_session.get(Job, job.id)
    assert row is not None and row.status == "queued"

    outbox = db_session.query(JobOutbox).filter(JobOutbox.job_id == job.id).all()
    assert len(outbox) == 1, "exactly one outbox row per job"
    assert outbox[0].delivered_at is not None, "happy path delivers immediately"
    assert client.queue == [(QUEUE, job.id)]


def test_enqueue_survives_redis_down(db_session):
    # The core P0-1 property: Redis down at origination cannot lose or fail the job.
    client = DeadRedis()
    job = enqueue_job(db_session, client, job_type="test")  # must NOT raise

    assert client.calls == 1, "delivery was attempted"
    row = db_session.get(Job, job.id)
    assert row is not None and row.status == "queued", "job is durable"

    outbox = db_session.query(JobOutbox).filter(JobOutbox.job_id == job.id).one()
    assert outbox.delivered_at is None, "undelivered (not lost) — retried later"


def test_dispatch_outbox_delivers_deferred_rows(db_session):
    dead = DeadRedis()
    job = enqueue_job(db_session, dead, job_type="test")
    assert db_session.query(JobOutbox).filter_by(job_id=job.id).one().delivered_at is None

    # Broker recovers; the dispatcher delivers the deferred row exactly once.
    live = FakeRedis()
    assert dispatch_outbox(db_session, live) == 1
    assert live.queue == [(QUEUE, job.id)]
    assert db_session.query(JobOutbox).filter_by(job_id=job.id).one().delivered_at is not None

    # Idempotent: a second dispatch finds nothing undelivered.
    assert dispatch_outbox(db_session, live) == 0
    assert live.queue == [(QUEUE, job.id)]


def test_dispatch_outbox_stops_on_broker_failure(db_session):
    # Two deferred jobs; broker still down → nothing delivered, both remain.
    dead = DeadRedis()
    enqueue_job(db_session, dead, job_type="test")
    enqueue_job(db_session, dead, job_type="test")

    assert dispatch_outbox(db_session, DeadRedis()) == 0
    undelivered = db_session.query(JobOutbox).filter(JobOutbox.delivered_at.is_(None)).count()
    assert undelivered == 2
