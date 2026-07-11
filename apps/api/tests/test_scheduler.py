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

    # Nominal cadence (AOS-SCHEDULER-RELIABILITY-001): next_run_at advances from the
    # SCHEDULED time, not the wall-clock tick, so cadence cannot drift forward.
    refreshed_due = db.get(Schedule, due_id)
    assert refreshed_due.last_run_at == now
    assert refreshed_due.next_run_at == (now - timedelta(minutes=5)) + timedelta(seconds=3600)

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


# --- AOS-SCHEDULER-RELIABILITY-001 (finding P0-2) ---------------------------


def test_schedule_fires_exactly_once_on_retry(db):
    # A crash that fired the job but did not persist the advance re-observes the
    # same due occurrence on the next tick; the ScheduleFire uniqueness blocks a
    # second job.
    now = now_utc()
    s = Schedule(
        name="x", job_type="test", interval_seconds=3600, enabled=True,
        next_run_at=now - timedelta(minutes=1),
    )
    db.add(s)
    db.commit()
    nominal = s.next_run_at

    assert len(run_due_schedules(db, FakeRedis(), now)) == 1

    # Reset to the same nominal (simulate the un-persisted advance) and re-run.
    s = db.get(Schedule, s.id)
    s.next_run_at = nominal
    db.commit()
    assert run_due_schedules(db, FakeRedis(), now) == []  # dedup, no second job
    assert db.query(Job).count() == 1


def test_missed_occurrences_are_coalesced(db):
    # A long-overdue schedule fires ONCE and advances to the next FUTURE nominal.
    now = now_utc()
    original_nominal = now - timedelta(hours=5, minutes=30)
    s = Schedule(
        name="x", job_type="test", interval_seconds=3600, enabled=True,
        next_run_at=original_nominal,
    )
    db.add(s)
    db.commit()

    job_ids = run_due_schedules(db, FakeRedis(), now)
    assert len(job_ids) == 1  # fired once, not six times
    s = db.get(Schedule, s.id)
    assert s.next_run_at > now  # advanced to a future occurrence
    # Still on the nominal grid (original + k*interval), so cadence never drifts.
    delta = (s.next_run_at - original_nominal).total_seconds()
    assert delta % 3600 == 0


def test_schedule_fire_uniqueness_enforced(db):
    import pytest as _pytest
    from sqlalchemy.exc import IntegrityError

    from aos_core.models import ScheduleFire

    now = now_utc()
    s = Schedule(name="x", job_type="test", interval_seconds=60, enabled=True, next_run_at=now)
    db.add(s)
    db.commit()
    db.add(ScheduleFire(schedule_id=s.id, nominal_fire_at=now))
    db.commit()
    db.add(ScheduleFire(schedule_id=s.id, nominal_fire_at=now))
    with _pytest.raises(IntegrityError):
        db.commit()
