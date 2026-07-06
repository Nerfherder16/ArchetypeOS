"""API + service tests for ADR export (AOS-COUNCIL-PHASEC2A).

Decision → Knowledge: an **approved** ``Decision`` is rendered into an ADR
markdown file under ``knowledge/wiki/decisions/`` (repo vault = source of truth)
and projected as a re-syncable ``KnowledgePage`` (``page_type="decision"``).
Export is a separate explicit step from approval, approved-only (409 otherwise),
idempotent, and fails gracefully (409, not 500) on a non-writable vault without
mutating the decision.

CRITICAL: every test points ``settings.knowledge_root`` at ``tmp_path`` — the
export never writes into the real repo ``knowledge/`` vault.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.models import CouncilAgentOutput, CouncilReview, Decision, KnowledgePage

from app.main import settings

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def _same_file_session(tmp_path):
    """A session on the same sqlite file the `client` fixture uses, for seeding."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _project(client) -> str:
    return client.post("/projects", json={"name": "ADR", "slug": "adr"}).json()["id"]


def _seed_review(session, project_id: str) -> str:
    review = CouncilReview(
        project_id=project_id,
        question="Should we adopt the proposed direction?",
        verdict="Accept",
        confidence=0.83,
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
                confidence=0.83,
            ),
        ],
    )
    session.add(review)
    session.commit()
    return review.id


def _seed_decision(session, project_id: str, *, status: str) -> str:
    decision = Decision(
        project_id=project_id,
        title="Adopt event-driven ingestion",
        context="We must decouple ingestion from processing.",
        decision="Adopt an event bus for ingestion.",
        status=status,
    )
    session.add(decision)
    session.commit()
    return decision.id


def _approved_decision(client, tmp_path) -> str:
    """Drive the real loop to an approved decision linked to a council review."""
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        review_id = _seed_review(session, project_id)
    finally:
        session.close()
    decision_id = client.post(f"/council-reviews/{review_id}/draft-decision").json()["id"]
    approved = client.post(f"/decisions/{decision_id}/approve", json={"approver": "operator@example.com"})
    assert approved.status_code == 200, approved.text
    return decision_id


# --- render_adr_markdown (pure) --------------------------------------------


def test_render_adr_markdown_contains_decision_and_review() -> None:
    from aos_core.services.adr import render_adr_markdown

    decision = Decision(
        id="abcd1234-0000-0000-0000-000000000000",
        project_id="p1",
        title="Adopt event-driven ingestion",
        context="We must decouple ingestion from processing.",
        decision="Adopt an event bus for ingestion.",
        alternatives=[{"topic": "polling", "favorable": ["a"], "unfavorable": ["b"]}],
        tradeoffs=[{"claim": "unproven at scale"}],
        consequences=["Verify: throughput under load"],
        evidence=[{"type": "council_review", "id": "rev-xyz"}],
        confidence=0.83,
        approved_by="operator@example.com",
        approved_at=datetime(2026, 7, 6, tzinfo=timezone.utc),
        meta={"council_review_id": "rev-xyz", "acceptance_criteria": ["p95 < 100ms"]},
    )
    review = CouncilReview(id="rev-xyz", project_id="p1", question="q", verdict="Accept", confidence=0.83)

    md = render_adr_markdown(decision, review)

    assert "# ADR — Adopt event-driven ingestion" in md
    assert "## Status" in md and "Accepted" in md
    assert "2026-07-06" in md
    assert "decouple ingestion from processing" in md  # context
    assert "Adopt an event bus for ingestion." in md  # decision
    # Evidence line for the linked council review (id + verdict).
    assert "rev-xyz" in md and "Accept" in md
    assert "p95 < 100ms" in md  # acceptance criteria
    assert "operator@example.com" in md  # reviewer / approver


# --- export_decision_adr (I/O + KnowledgePage projection) -------------------


def test_export_writes_file_and_creates_page(client, tmp_path) -> None:
    settings.knowledge_root = tmp_path
    decision_id = _approved_decision(client, tmp_path)

    resp = client.post(f"/decisions/{decision_id}/adr")
    assert resp.status_code == 200, resp.text
    page = resp.json()
    assert page["page_type"] == "decision"
    assert page["validation_state"] == "approved"
    assert page["vault_path"].startswith("wiki/decisions/ADR-")
    assert page["vault_path"].endswith(f"-{decision_id[:8]}.md")
    # Links back to the decision (and its council review) as source refs.
    ref_types = {ref["type"] for ref in page["source_refs"]}
    assert "decision" in ref_types and "council_review" in ref_types

    written = tmp_path / page["vault_path"]
    assert written.is_file()
    text = written.read_text(encoding="utf-8")
    # The loop-drafted decision text + a council-review Evidence line.
    assert "Adopt the council direction" in text
    assert "## Status" in text and "Accepted" in text

    # Projected page is queryable and typed.
    pages = client.get("/knowledge/pages", params={"page_type": "decision"}).json()
    assert page["id"] in [p["id"] for p in pages]


def test_export_draft_decision_is_409(client, tmp_path) -> None:
    settings.knowledge_root = tmp_path
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        draft_id = _seed_decision(session, project_id, status="draft")
        needs_id = _seed_decision(session, project_id, status="needs_evidence")
    finally:
        session.close()

    for decision_id in (draft_id, needs_id):
        resp = client.post(f"/decisions/{decision_id}/adr")
        assert resp.status_code == 409, resp.text
        assert "approved" in resp.json()["detail"].lower()

    # No ADR file was written for a non-approved decision.
    assert not (tmp_path / "wiki" / "decisions").exists()


def test_export_missing_decision_is_404(client, tmp_path) -> None:
    settings.knowledge_root = tmp_path
    assert client.post(f"/decisions/{UNKNOWN_ID}/adr").status_code == 404


def test_export_is_idempotent(client, tmp_path) -> None:
    settings.knowledge_root = tmp_path
    decision_id = _approved_decision(client, tmp_path)

    first = client.post(f"/decisions/{decision_id}/adr")
    second = client.post(f"/decisions/{decision_id}/adr")
    assert first.status_code == 200 and second.status_code == 200, second.text
    # Same stable path, same single page.
    assert first.json()["vault_path"] == second.json()["vault_path"]
    assert first.json()["id"] == second.json()["id"]

    session = _same_file_session(tmp_path)
    try:
        pages = (
            session.query(KnowledgePage)
            .filter(KnowledgePage.vault_path == first.json()["vault_path"])
            .all()
        )
        assert len(pages) == 1
    finally:
        session.close()

    # Exactly one ADR file on disk for this decision.
    matches = list((tmp_path / "wiki" / "decisions").glob(f"ADR-*-{decision_id[:8]}.md"))
    assert len(matches) == 1


def test_export_non_writable_vault_is_409_and_decision_unchanged(client, tmp_path) -> None:
    decision_id = _approved_decision(client, tmp_path)

    # Point knowledge_root at a *file*, so mkdir under it raises OSError.
    bad_root = tmp_path / "not-a-dir"
    bad_root.write_text("x", encoding="utf-8")
    settings.knowledge_root = bad_root

    resp = client.post(f"/decisions/{decision_id}/adr")
    assert resp.status_code == 409, resp.text
    assert "local-first" in resp.json()["detail"].lower()

    # The decision's approval state is untouched — no adr_path stamped.
    session = _same_file_session(tmp_path)
    try:
        decision = session.get(Decision, decision_id)
        assert decision.status == "approved"
        assert "adr_path" not in (decision.meta or {})
    finally:
        session.close()
