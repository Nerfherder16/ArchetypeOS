"""AOS-NODE-EXECUTION-001 — multi-node claim enforcement against real PostgreSQL.

Node assignment + eligibility are enforced in the claim's compare-and-swap, so the
guarantee only holds under real row-locking concurrency. These run against the CI
"Vector store tests" Postgres service (``AOS_TEST_DATABASE_URL``) and skip when it
is absent, exactly like the fencing PG suite.
"""

from __future__ import annotations

import os
import threading

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.models import Job, Node, NodeCapability, now_utc
from aos_core.services.jobs import claim_job_for_node

pytestmark = pytest.mark.pgvector

_DB_URL = os.environ.get("AOS_TEST_DATABASE_URL", "")


def _is_postgres(url: str) -> bool:
    try:
        return bool(url) and make_url(url).get_backend_name() == "postgresql"
    except Exception:
        return False


@pytest.fixture()
def pg_sessionmaker():
    if not _is_postgres(_DB_URL):
        pytest.skip("AOS_TEST_DATABASE_URL not set to a postgresql database")
    engine = create_engine(_DB_URL, pool_pre_ping=True, pool_size=12, max_overflow=12)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield Session
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _mk_node(Session, name, caps):
    with Session() as db:
        node = Node(name=name, node_type="worker", node_status="healthy",
                    max_sensitivity="private", write_access=True, last_seen_at=now_utc())
        db.add(node)
        db.flush()
        for c in caps:
            db.add(NodeCapability(node_id=node.id, capability=c))
        db.commit()
        return node.id


def _mk_job(Session, *, capability, assigned_node_id):
    with Session() as db:
        job = Job(job_type="test", status="queued", required_capability=capability,
                  sensitivity="public", assigned_node_id=assigned_node_id)
        db.add(job)
        db.commit()
        return job.id


def test_only_assigned_node_claims_under_concurrency(pg_sessionmaker):
    # A job routed to node A: many workers on BOTH nodes race to claim it. Only a
    # worker on node A can win, and exactly one does.
    node_a = _mk_node(pg_sessionmaker, "a", ["scan"])
    node_b = _mk_node(pg_sessionmaker, "b", ["scan"])
    job_id = _mk_job(pg_sessionmaker, capability="scan", assigned_node_id=node_a)

    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(10)

    def worker(i):
        # Half claim as node A, half as node B.
        assign = node_a if i % 2 == 0 else node_b
        barrier.wait()
        with pg_sessionmaker() as db:
            node = db.get(Node, assign)
            claim = claim_job_for_node(db, job_id, f"w{i}", node=node)
        with lock:
            results.append((assign, claim))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    winners = [(assign, c) for assign, c in results if c is not None]
    assert len(winners) == 1, f"exactly one winner, got {len(winners)}"
    assert winners[0][0] == node_a, "the winner must be a worker on the assigned node A"


def test_ineligible_node_never_claims_under_concurrency(pg_sessionmaker):
    # An unassigned job requiring 'scan': a node WITHOUT 'scan' can never win it,
    # even racing many attempts.
    _mk_node(pg_sessionmaker, "hascap", ["scan"])
    nocap = _mk_node(pg_sessionmaker, "nocap", ["digest"])
    job_id = _mk_job(pg_sessionmaker, capability="scan", assigned_node_id=None)

    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(6)

    def worker(i):
        barrier.wait()
        with pg_sessionmaker() as db:
            node = db.get(Node, nocap)
            claim = claim_job_for_node(db, job_id, f"w{i}", node=node)
        with lock:
            results.append(claim)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(c is None for c in results), "a node lacking the capability must never claim"
