"""AOS-AUTHORITY-HARDEN-001 — one-use consume under real PostgreSQL concurrency.

The one-use guarantee is a compare-and-swap on the DB row, so it only truly holds
under row-locking concurrency. Runs against the CI "Vector store tests" Postgres
service; skips when absent.
"""

from __future__ import annotations

import os
import threading

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.services.authority_envelope import authorize_action, consume_action, request_action

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


def test_concurrent_consume_has_exactly_one_winner(pg_sessionmaker):
    with pg_sessionmaker() as db:
        ar = request_action(db, action_class="repo_write")
        authorize_action(db, ar.id)
        action_id = ar.id

    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(10)

    def worker(i):
        barrier.wait()
        with pg_sessionmaker() as db:
            from aos_core.models import ActionRequest

            ar = db.get(ActionRequest, action_id)
            won = consume_action(db, ar, job_id=None)
            db.commit()
        with lock:
            results.append(won)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(1 for w in results if w) == 1, f"exactly one consumer wins, got {sum(results)}"
