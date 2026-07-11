"""Tests for Decision → Plan (AOS-BUILD-PLAN-001, RFC-0015 Design §1).

An approved ``Decision`` drafts a governed, draft-only ``ImplementationPlan``
(``services/build_plan.py:plan_from_decision``), idempotently, with a
deterministic CI-hermetic fallback when the provider output does not parse.
A named human then approves the draft (``approve_plan``), recording an
``ApprovalRecord``. Service-level tests exercise ``build_plan.py`` directly on
a bare in-memory session; API tests exercise the same flow through
``routes/plans.py`` (seeding via a same-file sqlite session, mirroring
``test_decisions_loop.py``).
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.models import ApprovalRecord, Decision, ImplementationPlan, Project
from aos_core.services.build_plan import approve_plan, plan_from_decision

import pytest
from fastapi import HTTPException

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Service-level tests (bare in-memory session, no HTTP layer)
# ---------------------------------------------------------------------------


def _approved_decision(db) -> Decision:
    project = Project(name="Build Plan", slug="build-plan")
    db.add(project)
    db.commit()
    decision = Decision(
        project_id=project.id,
        title="Adopt the proposed direction",
        context="Context for the decision.",
        decision="Implement the proposed direction.",
        consequences=["Update the service layer.", "Add API routes."],
        tradeoffs=["Some short-term migration cost."],
        evidence=[{"type": "council_review", "id": "rev-1"}],
        confidence=0.8,
        status="approved",
        approved_by="operator@example.com",
    )
    db.add(decision)
    db.commit()
    return decision


def test_plan_from_approved_decision(db_session) -> None:
    decision = _approved_decision(db_session)

    plan = plan_from_decision(db_session, decision_id=decision.id)

    assert plan.status == "draft"
    assert plan.decision_id == decision.id
    assert plan.project_id == decision.project_id
    assert plan.objective
    assert isinstance(plan.tasks, list) and len(plan.tasks) >= 1
    for task in plan.tasks:
        assert {"id", "description", "acceptance", "target_paths"} <= set(task.keys())
    assert isinstance(plan.acceptance_criteria, list) and len(plan.acceptance_criteria) >= 1
    assert isinstance(plan.verification_requirements, list) and len(plan.verification_requirements) >= 1
    assert {"type": "decision", "id": decision.id} in plan.evidence
    assert plan.meta.get("decision_id") == decision.id


def test_plan_requires_approved_decision(db_session) -> None:
    project = Project(name="Not Approved", slug="not-approved")
    db_session.add(project)
    db_session.commit()
    decision = Decision(project_id=project.id, title="Draft decision", status="draft")
    db_session.add(decision)
    db_session.commit()

    with pytest.raises(HTTPException) as excinfo:
        plan_from_decision(db_session, decision_id=decision.id)
    assert excinfo.value.status_code == 409


def test_plan_missing_decision_404(db_session) -> None:
    with pytest.raises(HTTPException) as excinfo:
        plan_from_decision(db_session, decision_id=UNKNOWN_ID)
    assert excinfo.value.status_code == 404


def test_plan_idempotent(db_session) -> None:
    decision = _approved_decision(db_session)

    first = plan_from_decision(db_session, decision_id=decision.id)
    second = plan_from_decision(db_session, decision_id=decision.id)

    assert first.id == second.id
    plans = db_session.query(ImplementationPlan).filter(ImplementationPlan.decision_id == decision.id).all()
    assert len(plans) == 1


def test_approve_plan_transitions_draft_to_approved(db_session) -> None:
    decision = _approved_decision(db_session)
    plan = plan_from_decision(db_session, decision_id=decision.id)

    approved = approve_plan(db_session, plan_id=plan.id, approver="operator@example.com", rationale="Looks good.")

    assert approved.status == "approved"
    assert approved.approved_by == "operator@example.com"
    assert approved.approved_at is not None

    records = (
        db_session.query(ApprovalRecord)
        .filter(ApprovalRecord.target == plan.id, ApprovalRecord.approval_status == "approved")
        .all()
    )
    assert len(records) == 1
    assert records[0].requested_capability == "plan.approve"
    assert records[0].actor == "operator@example.com"
    assert records[0].reason == "Looks good."
    assert records[0].project_id == decision.project_id


def test_approve_plan_missing_404(db_session) -> None:
    with pytest.raises(HTTPException) as excinfo:
        approve_plan(db_session, plan_id=UNKNOWN_ID, approver="op")
    assert excinfo.value.status_code == 404


def test_approve_plan_not_draft_409(db_session) -> None:
    decision = _approved_decision(db_session)
    plan = plan_from_decision(db_session, decision_id=decision.id)
    approve_plan(db_session, plan_id=plan.id, approver="op")

    with pytest.raises(HTTPException) as excinfo:
        approve_plan(db_session, plan_id=plan.id, approver="op")
    assert excinfo.value.status_code == 409


# ---------------------------------------------------------------------------
# API-level tests (routes/plans.py), mirroring test_decisions_loop.py
# ---------------------------------------------------------------------------


def _same_file_session(tmp_path):
    """A session on the same sqlite file the `client` fixture uses, for direct seeding."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _seed_approved_decision(session, project_id: str) -> str:
    decision = Decision(
        project_id=project_id,
        title="Adopt the proposed direction",
        context="Context for the decision.",
        decision="Implement the proposed direction.",
        consequences=["Update the service layer.", "Add API routes."],
        tradeoffs=["Some short-term migration cost."],
        evidence=[{"type": "council_review", "id": "rev-1"}],
        confidence=0.8,
        status="approved",
        approved_by="operator@example.com",
    )
    session.add(decision)
    session.commit()
    return decision.id


def _seed_draft_decision(session, project_id: str) -> str:
    decision = Decision(project_id=project_id, title="Not yet approved", status="draft")
    session.add(decision)
    session.commit()
    return decision.id


def _project(client) -> str:
    return client.post("/projects", json={"name": "Plans", "slug": "plans"}).json()["id"]


def test_draft_plan_route(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        decision_id = _seed_approved_decision(session, project_id)
    finally:
        session.close()

    resp = client.post(f"/decisions/{decision_id}/plan")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert body["decision_id"] == decision_id
    assert body["project_id"] == project_id
    assert {"type": "decision", "id": decision_id} in body["evidence"]
    assert body["approved_by"] is None
    assert body["approved_at"] is None


def test_draft_plan_missing_decision_404(client) -> None:
    resp = client.post(f"/decisions/{UNKNOWN_ID}/plan")
    assert resp.status_code == 404


def test_draft_plan_unapproved_decision_409(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        decision_id = _seed_draft_decision(session, project_id)
    finally:
        session.close()

    resp = client.post(f"/decisions/{decision_id}/plan")
    assert resp.status_code == 409, resp.text


def test_draft_plan_idempotent_route(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        decision_id = _seed_approved_decision(session, project_id)
    finally:
        session.close()

    first = client.post(f"/decisions/{decision_id}/plan")
    second = client.post(f"/decisions/{decision_id}/plan")
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_get_plan_route(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        decision_id = _seed_approved_decision(session, project_id)
    finally:
        session.close()

    plan_id = client.post(f"/decisions/{decision_id}/plan").json()["id"]
    resp = client.get(f"/plans/{plan_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == plan_id


def test_get_plan_missing_404(client) -> None:
    assert client.get(f"/plans/{UNKNOWN_ID}").status_code == 404


def test_list_plans_route(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        decision_id = _seed_approved_decision(session, project_id)
    finally:
        session.close()

    plan_id = client.post(f"/decisions/{decision_id}/plan").json()["id"]
    listing = client.get(f"/projects/{project_id}/plans")
    assert listing.status_code == 200, listing.text
    ids = [item["id"] for item in listing.json()]
    assert plan_id in ids


def test_list_plans_missing_project_404(client) -> None:
    assert client.get(f"/projects/{UNKNOWN_ID}/plans").status_code == 404


def test_approve_plan_route(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        decision_id = _seed_approved_decision(session, project_id)
    finally:
        session.close()

    plan_id = client.post(f"/decisions/{decision_id}/plan").json()["id"]
    resp = client.post(
        f"/plans/{plan_id}/approve",
        json={"approver": "operator@example.com", "rationale": "Ready to build."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == "operator@example.com"
    assert body["approved_at"] is not None

    session = _same_file_session(tmp_path)
    try:
        records = (
            session.query(ApprovalRecord)
            .filter(ApprovalRecord.target == plan_id, ApprovalRecord.approval_status == "approved")
            .all()
        )
        assert len(records) == 1
        assert records[0].requested_capability == "plan.approve"
        assert records[0].actor == "operator@example.com"
    finally:
        session.close()


def test_approve_plan_missing_404_route(client) -> None:
    assert (
        client.post(f"/plans/{UNKNOWN_ID}/approve", json={"approver": "op"}).status_code == 404
    )


def test_approve_plan_already_approved_409_route(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        decision_id = _seed_approved_decision(session, project_id)
    finally:
        session.close()

    plan_id = client.post(f"/decisions/{decision_id}/plan").json()["id"]
    first = client.post(f"/plans/{plan_id}/approve", json={"approver": "op"})
    assert first.status_code == 200, first.text

    again = client.post(f"/plans/{plan_id}/approve", json={"approver": "op"})
    assert again.status_code == 409, again.text
