"""Tests for nightly audit heartbeats (AOS-SELFHEAL observability).

A nightly probe (conflict/toil/coherence/session-pain) posts a heartbeat on every
run — clean / findings / failed — so the operator can tell a clean night from a
MISSED run without reading logs. The endpoint upserts one row per routine; the
list surfaces the latest per routine for a dashboard.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.models import AuditHeartbeat
from aos_core.services.audit_heartbeat import list_heartbeats, record_heartbeat

import pytest


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'hb.db'}",
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


def test_record_heartbeat_creates_then_upserts(db):
    first = record_heartbeat(db, routine="coherence", status="clean", day="2026-07-09")
    assert first.routine == "coherence"
    assert first.heartbeat_status == "clean"
    assert first.day == "2026-07-09"

    # A second heartbeat for the same routine UPSERTS (one row per routine), so a
    # dashboard reads the latest run, not an ever-growing log.
    second = record_heartbeat(
        db, routine="coherence", status="findings", day="2026-07-10", pr_url="http://pr/1"
    )
    assert second.id == first.id
    assert second.heartbeat_status == "findings"
    assert second.day == "2026-07-10"
    assert second.pr_url == "http://pr/1"
    assert db.query(AuditHeartbeat).filter(AuditHeartbeat.routine == "coherence").count() == 1


def test_record_heartbeat_scoped_per_project(db):
    # The same routine for two different projects is two independent rows; a
    # global heartbeat (project_id=None, the ArchetypeOS self-audit) is a third.
    a = record_heartbeat(db, routine="coherence", status="clean", day="2026-07-09", project_id="p1")
    b = record_heartbeat(db, routine="coherence", status="findings", day="2026-07-09", project_id="p2")
    g = record_heartbeat(db, routine="coherence", status="clean", day="2026-07-09")
    assert len({a.id, b.id, g.id}) == 3
    assert db.query(AuditHeartbeat).filter(AuditHeartbeat.routine == "coherence").count() == 3

    # Upsert stays scoped: re-posting for p1 updates p1's row, not p2's or global.
    a2 = record_heartbeat(db, routine="coherence", status="failed", day="2026-07-10", project_id="p1")
    assert a2.id == a.id
    assert a2.heartbeat_status == "failed"
    assert db.query(AuditHeartbeat).filter(AuditHeartbeat.routine == "coherence").count() == 3


def test_post_heartbeat_carries_project_id(client):
    resp = client.post(
        "/audits/heartbeat",
        json={"routine": "coherence", "status": "findings", "day": "2026-07-09", "project_id": "proj-xyz", "pr_url": "http://pr/9"},
    )
    assert resp.status_code == 201
    assert resp.json()["project_id"] == "proj-xyz"

    listing = client.get("/audits/heartbeats").json()
    assert any(r["routine"] == "coherence" and r["project_id"] == "proj-xyz" for r in listing)


def test_list_heartbeats_returns_latest_per_routine(db):
    record_heartbeat(db, routine="coherence", status="clean", day="2026-07-09")
    record_heartbeat(db, routine="session-pain", status="findings", day="2026-07-09", pr_url="http://pr/2")
    rows = list_heartbeats(db)
    routines = {r.routine: r for r in rows}
    assert set(routines) == {"coherence", "session-pain"}
    assert routines["session-pain"].pr_url == "http://pr/2"


# --- API ---


def test_post_heartbeat_and_list(client):
    resp = client.post(
        "/audits/heartbeat",
        json={"routine": "toil", "status": "clean", "day": "2026-07-09"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["routine"] == "toil"
    assert body["heartbeat_status"] == "clean"

    listing = client.get("/audits/heartbeats")
    assert listing.status_code == 200
    assert any(r["routine"] == "toil" for r in listing.json())


def test_post_heartbeat_rejects_unknown_status(client):
    resp = client.post(
        "/audits/heartbeat",
        json={"routine": "toil", "status": "exploded", "day": "2026-07-09"},
    )
    assert resp.status_code == 422


def test_post_heartbeat_rejects_empty_routine(client):
    resp = client.post(
        "/audits/heartbeat",
        json={"routine": "  ", "status": "clean", "day": "2026-07-09"},
    )
    assert resp.status_code == 422


def test_post_heartbeat_token_enforced_only_when_configured(client):
    from app.main import settings

    original = settings.audit_heartbeat_token
    settings.audit_heartbeat_token = "s3cret"
    try:
        # Missing/wrong token → 401 when a token is configured.
        denied = client.post(
            "/audits/heartbeat", json={"routine": "toil", "status": "clean", "day": "2026-07-09"}
        )
        assert denied.status_code == 401

        ok = client.post(
            "/audits/heartbeat",
            json={"routine": "toil", "status": "clean", "day": "2026-07-09"},
            headers={"x-telemetry-token": "s3cret"},
        )
        assert ok.status_code == 201
    finally:
        settings.audit_heartbeat_token = original
