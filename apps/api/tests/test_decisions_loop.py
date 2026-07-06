"""API tests for the Council → Decision loop (AOS-COUNCIL-PHASEC).

The loop: a persisted ``CouncilReview`` is drafted into a governed ``Decision``
that links back to the review as evidence, then a named human approves or
rejects it — with the transition recorded in an ``ApprovalRecord``. A decision
drafted from an **abstained** review is ``needs_evidence`` and cannot be
approved (LES-019). Reviews are seeded directly on the same sqlite file the
`client` fixture uses; the provider is never called.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.models import ApprovalRecord, CouncilAgentOutput, CouncilReview

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def _same_file_session(tmp_path):
    """A session on the same sqlite file the `client` fixture uses, for direct seeding."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _seed_review(session, project_id: str, *, verdict: str, confidence: float) -> str:
    """Persist a CouncilReview (with two agent outputs) and return its id."""
    review = CouncilReview(
        project_id=project_id,
        question="Should we adopt the proposed direction?",
        verdict=verdict,
        confidence=confidence,
        agreements=[{"point": "no blocking concerns", "agents": ["a", "b"]}],
        disagreements=[{"topic": "overall assessment", "favorable": ["a"], "unfavorable": ["b"]}],
        unsupported_claims=[{"agent": "a", "claim": "unproven finding"}],
        follow_up=["Verify: the risk flag"],
        agent_outputs=[
            CouncilAgentOutput(
                agent_name="research_librarian",
                agent_type="research",
                status="Complete",
                summary="ok",
                findings=["f1"],
                evidence=["e1"],
                concerns=[],
                confidence=confidence,
            ),
            CouncilAgentOutput(
                agent_name="security_agent",
                agent_type="security",
                status="Complete",
                summary="ok",
                findings=["f2"],
                evidence=["e2"],
                concerns=[],
                confidence=confidence,
            ),
        ],
    )
    session.add(review)
    session.commit()
    return review.id


def _project(client) -> str:
    return client.post("/projects", json={"name": "Loop", "slug": "loop"}).json()["id"]


def test_draft_from_cleared_floor_review(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        review_id = _seed_review(session, project_id, verdict="Accept", confidence=0.8)
    finally:
        session.close()

    resp = client.post(f"/council-reviews/{review_id}/draft-decision")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert body["project_id"] == project_id
    # Links back to the review as evidence, plus per-agent-output ids.
    assert {"type": "council_review", "id": review_id} in body["evidence"]
    assert any(entry["type"] == "council_agent_output" for entry in body["evidence"])
    assert body["approved_by"] is None
    assert body["approved_at"] is None


def test_draft_from_abstained_review_is_needs_evidence(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        review_id = _seed_review(session, project_id, verdict="Insufficient evidence", confidence=0.1)
    finally:
        session.close()

    resp = client.post(f"/council-reviews/{review_id}/draft-decision")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "needs_evidence"


def test_draft_is_idempotent(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        review_id = _seed_review(session, project_id, verdict="Accept", confidence=0.8)
    finally:
        session.close()

    first = client.post(f"/council-reviews/{review_id}/draft-decision")
    second = client.post(f"/council-reviews/{review_id}/draft-decision")
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    # Exactly one decision references this review.
    listing = client.get(f"/projects/{project_id}/decisions")
    linked = [
        d
        for d in listing.json()
        if {"type": "council_review", "id": review_id} in d["evidence"]
    ]
    assert len(linked) == 1


def test_approve_draft_records_approval(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        review_id = _seed_review(session, project_id, verdict="Accept", confidence=0.8)
    finally:
        session.close()

    decision_id = client.post(f"/council-reviews/{review_id}/draft-decision").json()["id"]

    resp = client.post(
        f"/decisions/{decision_id}/approve",
        json={"approver": "operator@example.com", "rationale": "Evidence clears the floor."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == "operator@example.com"
    assert body["approved_at"] is not None

    # An ApprovalRecord captures the approval.
    session = _same_file_session(tmp_path)
    try:
        records = (
            session.query(ApprovalRecord)
            .filter(ApprovalRecord.target == decision_id, ApprovalRecord.approval_status == "approved")
            .all()
        )
        assert len(records) == 1
        assert records[0].actor == "operator@example.com"
        assert records[0].requested_capability == "decision.approve"
        assert records[0].project_id == project_id
    finally:
        session.close()


def test_approve_needs_evidence_is_409(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        review_id = _seed_review(session, project_id, verdict="Insufficient evidence", confidence=0.1)
    finally:
        session.close()

    decision_id = client.post(f"/council-reviews/{review_id}/draft-decision").json()["id"]

    resp = client.post(f"/decisions/{decision_id}/approve", json={"approver": "operator@example.com"})
    assert resp.status_code == 409, resp.text
    # The message must name the evidence-gathering / re-draft path (LES-019).
    detail = resp.json()["detail"].lower()
    assert "evidence" in detail and "re-draft" in detail


def test_approve_already_approved_is_409(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        review_id = _seed_review(session, project_id, verdict="Accept", confidence=0.8)
    finally:
        session.close()

    decision_id = client.post(f"/council-reviews/{review_id}/draft-decision").json()["id"]
    first = client.post(f"/decisions/{decision_id}/approve", json={"approver": "op"})
    assert first.status_code == 200, first.text

    again = client.post(f"/decisions/{decision_id}/approve", json={"approver": "op"})
    assert again.status_code == 409, again.text


def test_reject_records_rejection(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        review_id = _seed_review(session, project_id, verdict="Accept", confidence=0.8)
    finally:
        session.close()

    decision_id = client.post(f"/council-reviews/{review_id}/draft-decision").json()["id"]

    resp = client.post(
        f"/decisions/{decision_id}/reject",
        json={"approver": "operator@example.com", "rationale": "Direction is premature."},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"

    session = _same_file_session(tmp_path)
    try:
        records = (
            session.query(ApprovalRecord)
            .filter(ApprovalRecord.target == decision_id, ApprovalRecord.approval_status == "rejected")
            .all()
        )
        assert len(records) == 1
        assert records[0].reason == "Direction is premature."
    finally:
        session.close()

    # A rejected decision cannot be re-transitioned.
    again = client.post(f"/decisions/{decision_id}/reject", json={"approver": "op", "rationale": "again"})
    assert again.status_code == 409, again.text


def test_draft_missing_review_404(client) -> None:
    assert client.post(f"/council-reviews/{UNKNOWN_ID}/draft-decision").status_code == 404


def test_approve_reject_missing_decision_404(client) -> None:
    assert client.post(f"/decisions/{UNKNOWN_ID}/approve", json={"approver": "op"}).status_code == 404
    assert (
        client.post(f"/decisions/{UNKNOWN_ID}/reject", json={"approver": "op", "rationale": "x"}).status_code
        == 404
    )
