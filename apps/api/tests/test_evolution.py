"""Tests for the Evolution Engine (AOS-EVOLVE-001 — RFC-0015 Wave C).

Fully hermetic: no provider/LLM/network call anywhere in this module, and no
wall-clock coupling — every staleness pass is driven by an explicitly injected
``now`` (``services/evolution.py``'s ``find_stale_decisions`` /
``reevaluate_decision``). Service-level tests exercise the module directly on
a bare in-memory session (mirrors ``test_recommendation_engine.py``); the
route tests seed via a same-file sqlite session and drive
``routes/decisions.py``'s new ``GET .../decisions/stale`` and
``POST /decisions/{id}/reevaluate`` endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.models import Decision, Project, ResearchNote
from aos_core.services.evolution import find_stale_decisions, reevaluate_decision

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"
NOW = datetime(2026, 7, 11, tzinfo=timezone.utc)


def _project(db, slug: str) -> str:
    project = Project(name=slug, slug=slug)
    db.add(project)
    db.commit()
    return project.id


def _decision(db, project_id: str, *, status: str = "approved", approved_at=None, evidence=None, title="D") -> Decision:
    decision = Decision(
        project_id=project_id,
        title=title,
        status=status,
        approved_at=approved_at,
        approved_by="operator" if status == "approved" else None,
        evidence=evidence or [],
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def _note(db, project_id: str, *, question: str, created_at, title="N") -> ResearchNote:
    note = ResearchNote(project_id=project_id, title=title, question=question, created_at=created_at)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


# ---------------------------------------------------------------------------
# Service-level tests (bare in-memory session, no HTTP layer)
# ---------------------------------------------------------------------------


def test_find_stale_by_age(db_session) -> None:
    project_id = _project(db_session, "age-stale")
    old_decision = _decision(
        db_session, project_id, approved_at=NOW - timedelta(days=100)
    )

    stale = find_stale_decisions(db_session, project_id=project_id, max_age_days=90, now=NOW)

    assert len(stale) == 1
    record = stale[0]
    assert record["decision_id"] == old_decision.id
    assert record["title"] == old_decision.title
    assert record["age_days"] == 100
    assert "100d" in record["reason"] and "90d" in record["reason"]


def test_find_stale_by_superseded_evidence(db_session) -> None:
    project_id = _project(db_session, "supersede-stale")
    old_note = _note(db_session, project_id, question="Which DB?", created_at=NOW - timedelta(days=30))
    newer_note = _note(db_session, project_id, question="Which DB?", created_at=NOW - timedelta(days=5))
    decision = _decision(
        db_session,
        project_id,
        # recently approved -> not stale by age
        approved_at=NOW - timedelta(days=1),
        evidence=[{"type": "research_note", "id": old_note.id}],
    )

    stale = find_stale_decisions(db_session, project_id=project_id, max_age_days=90, now=NOW)

    assert len(stale) == 1
    record = stale[0]
    assert record["decision_id"] == decision.id
    assert old_note.id in record["reason"]
    assert newer_note.id in record["reason"]
    assert "superseded" in record["reason"]
    # not stale by age -> the age clause is absent from the reason
    assert "staleness threshold" not in record["reason"]


def test_find_stale_documents_both_reasons_when_both_apply(db_session) -> None:
    project_id = _project(db_session, "both-stale")
    old_note = _note(db_session, project_id, question="Which cache?", created_at=NOW - timedelta(days=200))
    newer_note = _note(db_session, project_id, question="Which cache?", created_at=NOW - timedelta(days=10))
    decision = _decision(
        db_session,
        project_id,
        approved_at=NOW - timedelta(days=365),
        evidence=[{"type": "research_note", "id": old_note.id}],
    )

    stale = find_stale_decisions(db_session, project_id=project_id, max_age_days=90, now=NOW)

    assert len(stale) == 1
    record = stale[0]
    assert record["decision_id"] == decision.id
    assert "staleness threshold" in record["reason"]
    assert "superseded" in record["reason"]
    assert newer_note.id in record["reason"]


def test_fresh_decision_not_stale(db_session) -> None:
    project_id = _project(db_session, "fresh")
    note = _note(db_session, project_id, question="Which framework?", created_at=NOW - timedelta(days=10))
    _decision(
        db_session,
        project_id,
        approved_at=NOW - timedelta(days=5),
        evidence=[{"type": "research_note", "id": note.id}],
    )

    stale = find_stale_decisions(db_session, project_id=project_id, max_age_days=90, now=NOW)

    assert stale == []


def test_only_approved_considered(db_session) -> None:
    project_id = _project(db_session, "draft-old")
    # A draft decision with a very old approved_at (e.g. re-drafted from an old
    # rejected attempt) must never be reported — staleness only applies once a
    # decision actually governs something (status == approved).
    _decision(
        db_session,
        project_id,
        status="draft",
        approved_at=NOW - timedelta(days=1000),
    )
    _decision(
        db_session,
        project_id,
        status="needs_evidence",
        approved_at=NOW - timedelta(days=1000),
    )

    stale = find_stale_decisions(db_session, project_id=project_id, max_age_days=90, now=NOW)

    assert stale == []


def test_find_stale_filters_by_project(db_session) -> None:
    project_a = _project(db_session, "proj-a")
    project_b = _project(db_session, "proj-b")
    _decision(db_session, project_a, approved_at=NOW - timedelta(days=200))
    _decision(db_session, project_b, approved_at=NOW - timedelta(days=200))

    stale_a = find_stale_decisions(db_session, project_id=project_a, max_age_days=90, now=NOW)

    assert len(stale_a) == 1
    assert all(r["decision_id"] for r in stale_a)


def test_reevaluate_flags_advisory(db_session) -> None:
    project_id = _project(db_session, "reeval")
    decision = _decision(db_session, project_id, approved_at=NOW - timedelta(days=200))

    updated = reevaluate_decision(db_session, decision_id=decision.id, reason="evidence looks dated", now=NOW)

    assert updated.status == "approved"  # advisory only — never mutated
    assert updated.meta["reevaluation_requested_at"] == NOW.isoformat()
    assert updated.meta["stale_reason"] == "evidence looks dated"

    # idempotent: calling again without a reason only refreshes the timestamp
    # and preserves the previously recorded reason.
    later = NOW + timedelta(days=1)
    again = reevaluate_decision(db_session, decision_id=decision.id, now=later)

    assert again.status == "approved"
    assert again.meta["reevaluation_requested_at"] == later.isoformat()
    assert again.meta["stale_reason"] == "evidence looks dated"

    stored = db_session.get(Decision, decision.id)
    assert stored.meta["reevaluation_requested_at"] == later.isoformat()


def test_reevaluate_missing_decision_404s(db_session) -> None:
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as excinfo:
        reevaluate_decision(db_session, decision_id=UNKNOWN_ID, now=NOW)
    assert excinfo.value.status_code == 404


# ---------------------------------------------------------------------------
# API-level tests (routes/decisions.py), mirroring test_recommendation_engine.py
# ---------------------------------------------------------------------------


def _same_file_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_stale_decisions_route(client, tmp_path) -> None:
    project_id = client.post("/projects", json={"name": "Route Evolve", "slug": "route-evolve"}).json()["id"]
    session = _same_file_session(tmp_path)
    try:
        old_decision = _decision(session, project_id, approved_at=datetime.now(timezone.utc) - timedelta(days=200))
    finally:
        session.close()

    resp = client.get(f"/projects/{project_id}/decisions/stale", params={"max_age_days": 90})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["decision_id"] == old_decision.id
    assert body[0]["age_days"] is not None
    assert "staleness threshold" in body[0]["reason"]


def test_stale_decisions_route_missing_project_404(client) -> None:
    resp = client.get(f"/projects/{UNKNOWN_ID}/decisions/stale")
    assert resp.status_code == 404


def test_reevaluate_route_missing_decision_404(client) -> None:
    resp = client.post(f"/decisions/{UNKNOWN_ID}/reevaluate", json={"reason": "x"})
    assert resp.status_code == 404


def test_reevaluate_route_success(client, tmp_path) -> None:
    project_id = client.post("/projects", json={"name": "Reeval Route", "slug": "reeval-route"}).json()["id"]
    session = _same_file_session(tmp_path)
    try:
        decision = _decision(session, project_id, approved_at=datetime.now(timezone.utc) - timedelta(days=1))
    finally:
        session.close()

    resp = client.post(f"/decisions/{decision.id}/reevaluate", json={"reason": "recheck vendor pricing"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == decision.id
    assert body["status"] == "approved"  # advisory only — status untouched

    # DecisionRead does not expose `meta`; verify the advisory flag landed by
    # reading straight from the (same-file) database the route committed to.
    verify_session = _same_file_session(tmp_path)
    try:
        stored = verify_session.get(Decision, decision.id)
        assert stored.meta.get("stale_reason") == "recheck vendor pricing"
        assert stored.meta.get("reevaluation_requested_at")
        assert stored.status == "approved"
    finally:
        verify_session.close()


def test_reevaluate_route_no_body(client, tmp_path) -> None:
    project_id = client.post("/projects", json={"name": "Reeval No Body", "slug": "reeval-no-body"}).json()["id"]
    session = _same_file_session(tmp_path)
    try:
        decision = _decision(session, project_id, approved_at=datetime.now(timezone.utc) - timedelta(days=1))
    finally:
        session.close()

    resp = client.post(f"/decisions/{decision.id}/reevaluate")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"
