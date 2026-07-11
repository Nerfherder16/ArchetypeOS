"""AOS-JOBS-RELIABILITY-001 / RFC-0014 Slice 1 — durable job origination.

Proves the transactional outbox closes finding P0-1: a ``Job`` and its delivery
intent commit atomically, a Redis outage at origination cannot lose or fail the
job, and the dispatcher delivers deferred rows once the broker is reachable.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aos_core.models import Job, JobOutbox
from aos_core.services.jobs import (
    QUEUE,
    Claim,
    claim_job,
    complete_job,
    dead_letter_job,
    dispatch_outbox,
    enqueue_job,
    fail_job,
    reap_expired_leases,
    reconcile,
    release_for_retry,
    renew_lease,
)


class FakeRedis:
    """Captures lpush calls; a healthy broker."""

    def __init__(self) -> None:
        self.queue: list[tuple[str, str]] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append((name, value))

    def lrange(self, name: str, start: int, end: int) -> list[str]:
        return [value for (_, value) in self.queue]


class DeadRedis:
    """A broker that is down — every call raises, as a real outage would."""

    def __init__(self) -> None:
        self.calls = 0

    def lpush(self, name: str, value: str) -> None:
        self.calls += 1
        raise ConnectionError("redis unavailable")

    def lrange(self, name: str, start: int, end: int) -> list[str]:
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


# --- Slice 2: leased claims + crash recovery (finding P0-1, execution half) ---


def test_claim_is_single_winner(db_session):
    job = enqueue_job(db_session, FakeRedis(), job_type="test")
    # AOS-JOB-FENCING-001: claim_job returns a Claim on win, None on loss.
    claim = claim_job(db_session, job.id, "w1")
    assert claim is not None
    assert claim.claim_token and claim.worker_id == "w1"
    assert claim_job(db_session, job.id, "w2") is None  # w1 holds a live lease
    row = db_session.get(Job, job.id)
    assert row.status == "running" and row.claimed_by == "w1"
    assert row.claim_token == claim.claim_token
    assert row.attempts == 1  # claim increments once; the losing claim does not


def test_reap_recovers_expired_lease(db_session):
    client = FakeRedis()
    job = enqueue_job(db_session, client, job_type="test")
    t0 = datetime(2026, 7, 11, tzinfo=timezone.utc)
    assert claim_job(db_session, job.id, "w1", now=t0) is not None  # lease -> t0 + 300s

    # Worker "dies"; reap runs well after the lease lapses.
    requeued = reap_expired_leases(db_session, client, max_attempts=3, now=t0 + timedelta(seconds=400))
    assert requeued == 1

    row = db_session.get(Job, job.id)
    assert row.status == "queued"
    assert row.claimed_by is None and row.lease_expires_at is None
    assert (QUEUE, job.id) in client.queue  # redelivered through the outbox


def test_reap_dead_letters_when_attempts_exhausted(db_session):
    client = FakeRedis()
    job = enqueue_job(db_session, client, job_type="test")
    row = db_session.get(Job, job.id)
    row.status = "running"
    row.attempts = 3
    row.lease_expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)  # long expired
    db_session.commit()

    assert reap_expired_leases(db_session, client, max_attempts=3) == 0
    row = db_session.get(Job, job.id)
    assert row.status == "dead_letter"  # Slice 3: exhausted retry budget → dead letter
    assert "lease expired" in (row.error or "")


# --- Slice 4: reconciliation sweep (jobs stranded from the broker) ---


def test_reconcile_restores_stranded_queued_job(db_session):
    client = FakeRedis()
    job = enqueue_job(db_session, client, job_type="test")  # delivered
    # Simulate a broker flush: the job is still queued in the DB but gone from Redis.
    client.queue.clear()

    summary = reconcile(db_session, client, max_attempts=3)
    assert summary["restored"] == 1
    assert (QUEUE, job.id) in client.queue  # redelivered

    # Idempotent once it is back in the broker.
    assert reconcile(db_session, client, max_attempts=3)["restored"] == 0


def test_reconcile_survives_broker_down(db_session):
    # A dead broker must not raise: the outbox still guarantees eventual delivery.
    dead = DeadRedis()
    enqueue_job(db_session, dead, job_type="test")
    summary = reconcile(db_session, dead, max_attempts=3)
    assert summary["restored"] == 0  # could not scan the broker; nothing lost


# --- AOS-JOB-FENCING-001: claim tokens fence every worker-side transition ---


def _stale_claim(real: Claim) -> Claim:
    """A claim carrying the right worker/job but a dead token (simulates a reclaim)."""
    return Claim(job_id=real.job_id, worker_id=real.worker_id, claim_token="stale-token", lease_expires_at=real.lease_expires_at)


def test_complete_requires_ownership(db_session):
    job = enqueue_job(db_session, FakeRedis(), job_type="test")
    claim = claim_job(db_session, job.id, "w1")
    assert complete_job(db_session, job.id, {"ok": True}, claim=claim) is True
    assert db_session.get(Job, job.id).status == "completed"


def test_stale_worker_cannot_complete_after_reclaim(db_session):
    # Worker A claims, its lease expires, worker B reclaims (new token). A's stale
    # completion must be rejected and must NOT overwrite B's ownership.
    job = enqueue_job(db_session, FakeRedis(), job_type="test")
    t0 = datetime(2026, 7, 11, tzinfo=timezone.utc)
    claim_a = claim_job(db_session, job.id, "wA", now=t0)
    claim_b = claim_job(db_session, job.id, "wB", now=t0 + timedelta(seconds=400))  # lease expired → reclaims
    assert claim_b is not None and claim_b.claim_token != claim_a.claim_token

    # Stale worker A tries to finish the job it no longer owns.
    assert complete_job(db_session, job.id, {"stale": True}, claim=claim_a) is False
    row = db_session.get(Job, job.id)
    assert row.status == "running"           # not completed by A
    assert row.claimed_by == "wB"            # B still owns it
    assert row.claim_token == claim_b.claim_token
    assert row.result is None                # A's result never landed

    # Worker B completes normally.
    assert complete_job(db_session, job.id, {"ok": True}, claim=claim_b) is True
    assert db_session.get(Job, job.id).status == "completed"


def test_stale_worker_cannot_fail_or_requeue_after_reclaim(db_session):
    job = enqueue_job(db_session, FakeRedis(), job_type="test")
    t0 = datetime(2026, 7, 11, tzinfo=timezone.utc)
    claim_a = claim_job(db_session, job.id, "wA", now=t0)
    claim_b = claim_job(db_session, job.id, "wB", now=t0 + timedelta(seconds=400))
    assert claim_b is not None  # B reclaimed the expired lease

    assert fail_job(db_session, job.id, "boom", claim=claim_a) is False
    assert release_for_retry(db_session, job.id, claim=claim_a) is False
    assert dead_letter_job(db_session, job.id, "boom", claim=claim_a) is False
    row = db_session.get(Job, job.id)
    assert row.status == "running" and row.claimed_by == "wB"  # B's ownership intact


def test_renew_lease_requires_token(db_session):
    job = enqueue_job(db_session, FakeRedis(), job_type="test")
    t0 = datetime(2026, 7, 11, tzinfo=timezone.utc)
    claim = claim_job(db_session, job.id, "w1", now=t0)
    # A live owner renews successfully; a stale token cannot.
    assert renew_lease(db_session, claim, now=t0 + timedelta(seconds=10)) is True
    assert renew_lease(db_session, _stale_claim(claim), now=t0 + timedelta(seconds=20)) is False


def test_reap_clears_fencing_token(db_session):
    # After the reaper recovers an expired lease, the old token is dead: the prior
    # owner can neither renew nor complete.
    client = FakeRedis()
    job = enqueue_job(db_session, client, job_type="test")
    t0 = datetime(2026, 7, 11, tzinfo=timezone.utc)
    claim = claim_job(db_session, job.id, "w1", now=t0)
    reap_expired_leases(db_session, client, max_attempts=3, now=t0 + timedelta(seconds=400))
    row = db_session.get(Job, job.id)
    assert row.claim_token is None and row.status == "queued"
    assert complete_job(db_session, job.id, {"stale": True}, claim=claim) is False
