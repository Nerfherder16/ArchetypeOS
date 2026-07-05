"""Unit test for the control-plane scheduler tick (RFC-0007 / AOS-SCHED-001)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.models import Job, Project, Schedule, now_utc
from aos_core.services.scheduler import run_due_schedules


class FakeRedis:
    """Captures lpush calls so the scheduler tick needs no real Redis."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append(value)


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'sched.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_run_due_schedules(db):
    now = now_utc()
    project = Project(name="Sched", slug="sched")
    db.add(project)
    db.flush()

    due = Schedule(
        project_id=project.id,
        name="due digest",
        job_type="project_digest",
        interval_seconds=3600,
        enabled=True,
        next_run_at=now - timedelta(minutes=5),
    )
    not_due = Schedule(
        project_id=project.id,
        name="future digest",
        job_type="project_digest",
        interval_seconds=3600,
        enabled=True,
        next_run_at=now + timedelta(hours=1),
    )
    db.add_all([due, not_due])
    db.commit()
    due_id = due.id
    not_due_id = not_due.id

    fake = FakeRedis()
    job_ids = run_due_schedules(db, fake, now)

    # exactly one schedule was due -> one job enqueued
    assert len(job_ids) == 1
    assert fake.queue == job_ids

    jobs = db.query(Job).all()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.status == "queued"
    assert job.job_type == "project_digest"
    assert job.project_id == project.id
    assert job.id == job_ids[0]

    # the due schedule advanced ~1h; last_run_at stamped
    refreshed_due = db.get(Schedule, due_id)
    assert refreshed_due.last_run_at == now
    assert refreshed_due.next_run_at == now + timedelta(seconds=3600)

    # the not-due schedule was untouched
    refreshed_not_due = db.get(Schedule, not_due_id)
    assert refreshed_not_due.last_run_at is None
    assert refreshed_not_due.next_run_at == now + timedelta(hours=1)


def test_disabled_schedule_not_enqueued(db):
    now = now_utc()
    disabled = Schedule(
        name="disabled",
        job_type="test",
        interval_seconds=60,
        enabled=False,
        next_run_at=now - timedelta(minutes=5),
    )
    db.add(disabled)
    db.commit()

    fake = FakeRedis()
    job_ids = run_due_schedules(db, fake, now)

    assert job_ids == []
    assert fake.queue == []
    assert db.query(Job).count() == 0
