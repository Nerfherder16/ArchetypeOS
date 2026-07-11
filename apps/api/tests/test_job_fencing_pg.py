"""AOS-JOB-FENCING-001 — concurrency fault injection against real PostgreSQL.

SQLite serializes writes, so the claim/fence compare-and-swap is only truly
exercised under a database with row-level locking. These tests run against the CI
"Vector store tests" Postgres service (``AOS_TEST_DATABASE_URL``); they skip when
that is absent, exactly like the pgvector suite. They prove the fencing invariants
LES-033 says unit-on-SQLite tests cannot: a real two-worker race yields exactly one
claim, and a stale worker cannot mutate a reclaimed job.
"""

from __future__ import annotations

import os
import threading
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.models import Job, now_utc
from aos_core.services.jobs import claim_job, complete_job, fail_job

pytestmark = pytest.mark.pgvector

_DB_URL = os.environ.get("AOS_TEST_DATABASE_URL", "")


def _is_postgres(url: str) -> bool:
    try:
        return bool(url) and make_url(url).get_backend_name() == "postgresql"
    except Exception:
        return False


@pytest.fixture()
def pg_engine():
    if not _is_postgres(_DB_URL):
        pytest.skip("AOS_TEST_DATABASE_URL not set to a postgresql database")
    engine = create_engine(_DB_URL, pool_pre_ping=True, pool_size=16, max_overflow=16)
    # create_all builds every table, including knowledge_pages.embedding (pgvector);
    # ensure the extension exists first, like the pgvector store suite does — this
    # suite may run before it and the type would otherwise be undefined.
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _seed_job(engine) -> str:
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        job = Job(job_type="test", status="queued")
        db.add(job)
        db.commit()
        return job.id


def test_two_workers_race_produces_one_claim(pg_engine):
    # 12 workers race to claim the same job on real Postgres. Exactly one wins the
    # compare-and-swap; the other 11 get None.
    job_id = _seed_job(pg_engine)
    Session = sessionmaker(bind=pg_engine, expire_on_commit=False)
    results: list[object] = []
    lock = threading.Lock()
    barrier = threading.Barrier(12)

    def worker(i: int) -> None:
        barrier.wait()  # maximize contention: everyone claims at once
        with Session() as db:
            claim = claim_job(db, job_id, f"w{i}")
        with lock:
            results.append(claim)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    winners = [c for c in results if c is not None]
    assert len(winners) == 1, f"exactly one winner, got {len(winners)}"
    with Session() as db:
        row = db.get(Job, job_id)
        assert row.status == "running"
        assert row.claim_token == winners[0].claim_token
        assert row.attempts == 1  # only the winning claim incremented


def test_stale_worker_cannot_complete_after_pg_reclaim(pg_engine):
    # Worker A claims; its lease is force-expired; worker B reclaims (new token).
    # A's completion must be refused under real concurrency — B's row is untouched.
    job_id = _seed_job(pg_engine)
    Session = sessionmaker(bind=pg_engine, expire_on_commit=False)

    with Session() as db:
        claim_a = claim_job(db, job_id, "wA")
    # Force A's lease to look expired so B can reclaim.
    with Session() as db:
        row = db.get(Job, job_id)
        row.lease_expires_at = now_utc() - timedelta(seconds=1)
        db.commit()
    with Session() as db:
        claim_b = claim_job(db, job_id, "wB")
    assert claim_b is not None and claim_b.claim_token != claim_a.claim_token

    with Session() as db:
        assert complete_job(db, job_id, {"stale": True}, claim=claim_a) is False
        assert fail_job(db, job_id, "stale", claim=claim_a) is False
    with Session() as db:
        row = db.get(Job, job_id)
        assert row.status == "running" and row.claimed_by == "wB"
        assert row.result is None

    with Session() as db:
        assert complete_job(db, job_id, {"ok": True}, claim=claim_b) is True
        assert db.get(Job, job_id).status == "completed"
