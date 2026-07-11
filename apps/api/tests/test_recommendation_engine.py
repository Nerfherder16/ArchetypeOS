"""Tests for the Technology Fitness + Recommendation generator (AOS-RECO-ENGINE-001).

Fully hermetic: no provider/LLM/network call anywhere in this module. Every
assertion exercises a deterministic rule pass over rows already committed to a
sqlite session (``score_fitness`` / ``generate_recommendations``,
``services/recommendation.py``). Service-level tests exercise the module
directly on a bare in-memory session (mirrors ``test_build_plan.py``); the
route test seeds via a same-file sqlite session and drives
``routes/decisions.py``'s new ``POST .../recommendations/generate`` endpoint.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.models import Project, Recommendation, Repository, RepositoryDNA, ResearchNote
from aos_core.services.recommendation import (
    DEFAULT_RISK_SCORE,
    DEFAULT_RISK_SEVERITY,
    FRAMEWORK_PRESENCE_SCORE,
    generate_recommendations,
    score_fitness,
)

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Service-level tests (bare in-memory session, no HTTP layer)
# ---------------------------------------------------------------------------


def _project_with_dna(
    db,
    *,
    risk_flags: list[str] | None = None,
    frameworks: list[str] | None = None,
    runtime_services: list[str] | None = None,
) -> tuple[str, RepositoryDNA]:
    project = Project(name="Reco Engine", slug="reco-engine")
    db.add(project)
    db.commit()
    repo = Repository(project_id=project.id, name="svc", local_path="/tmp/svc")
    db.add(repo)
    db.commit()
    dna = RepositoryDNA(
        repository_id=repo.id,
        frameworks=frameworks or [],
        risk_flags=risk_flags or [],
        runtime_services=runtime_services or [],
        confidence=0.8,
    )
    db.add(dna)
    db.commit()
    return project.id, dna


def test_score_fitness_signals(db_session) -> None:
    _, dna = _project_with_dna(
        db_session,
        risk_flags=["Code files present but no test files or test directories detected"],
        frameworks=["fastapi"],
        runtime_services=["postgres"],
    )

    signals = score_fitness(dna)

    by_signal = {s["signal"]: s for s in signals}
    assert set(by_signal) == {"risk_flag", "framework_present", "runtime_service_present"}
    for signal in signals:
        assert {"subject", "signal", "score", "severity", "evidence"} <= set(signal.keys())
        assert isinstance(signal["evidence"], list) and signal["evidence"]
        assert 0.0 <= signal["score"] <= 1.0

    risk_signal = by_signal["risk_flag"]
    assert risk_signal["subject"] == "Code files present but no test files or test directories detected"
    assert risk_signal["severity"] == "high"
    assert risk_signal["score"] == 0.25

    framework_signal = by_signal["framework_present"]
    assert framework_signal["subject"] == "fastapi"
    assert framework_signal["score"] == FRAMEWORK_PRESENCE_SCORE
    assert framework_signal["severity"] == "info"


def test_score_fitness_unknown_flag_gets_documented_default(db_session) -> None:
    _, dna = _project_with_dna(db_session, risk_flags=["something the scanner has never said before"])

    signals = score_fitness(dna)

    assert len(signals) == 1
    assert signals[0]["score"] == DEFAULT_RISK_SCORE
    assert signals[0]["severity"] == DEFAULT_RISK_SEVERITY


def test_score_fitness_deterministic(db_session) -> None:
    _, dna = _project_with_dna(db_session, risk_flags=["no CI configuration"], frameworks=["react"])

    assert score_fitness(dna) == score_fitness(dna)


def test_generate_from_dna_risk_flags(db_session) -> None:
    project_id, dna = _project_with_dna(
        db_session,
        risk_flags=["No CI configuration detected", "Docker files present but no .env.example template found"],
    )

    created = generate_recommendations(db_session, project_id=project_id)

    assert len(created) == 2
    for reco in created:
        assert reco.project_id == project_id
        # Recommendation has no approved_by column (unlike Decision/Plan) — draft/
        # advisory status is carried entirely by AuditMixin.status, left at its
        # default ("active") rather than any approval workflow.
        assert reco.status == "active"
        assert 0.0 <= reco.confidence <= 1.0
        assert reco.evidence == [{"type": "repository_dna", "id": dna.id}]
        assert reco.risk
        assert reco.meta.get("reco_signature")
        assert reco.meta.get("kind") == "risk_remediation"

    stored = db_session.query(Recommendation).filter(Recommendation.project_id == project_id).all()
    assert len(stored) == 2


def test_generate_idempotent(db_session) -> None:
    project_id, _ = _project_with_dna(db_session, risk_flags=["No CI configuration detected"])

    first = generate_recommendations(db_session, project_id=project_id)
    second = generate_recommendations(db_session, project_id=project_id)

    assert len(first) == 1
    assert second == []  # nothing new to create — already generated
    stored = db_session.query(Recommendation).filter(Recommendation.project_id == project_id).all()
    assert len(stored) == 1
    assert stored[0].meta.get("reco_signature") == first[0].meta.get("reco_signature")


def test_generate_from_research_finding(db_session) -> None:
    project = Project(name="Research Reco", slug="research-reco")
    db_session.add(project)
    db_session.commit()
    note = ResearchNote(
        project_id=project.id,
        title="Frontend framework survey",
        findings=[
            {"claim": "Adopt React for the frontend rewrite.", "source_ref": "src-1"},
            {"claim": "Vue and React both have mature ecosystems.", "source_ref": "src-2"},
        ],
        confidence=0.7,
    )
    db_session.add(note)
    db_session.commit()

    created = generate_recommendations(db_session, project_id=project.id)

    assert len(created) == 1
    reco = created[0]
    assert reco.evidence == [{"type": "research_note", "id": note.id}]
    assert "Adopt React" in reco.recommendation
    assert 0.0 <= reco.confidence <= 1.0
    assert reco.meta.get("kind") == "research_adoption"


def test_generate_empty_project(db_session) -> None:
    project = Project(name="Empty", slug="empty-reco")
    db_session.add(project)
    db_session.commit()

    created = generate_recommendations(db_session, project_id=project.id)

    assert created == []


# ---------------------------------------------------------------------------
# API-level tests (routes/decisions.py), mirroring test_build_plan.py
# ---------------------------------------------------------------------------


def _same_file_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _seed_dna_with_risk_flag(session, project_id: str) -> None:
    repo = Repository(project_id=project_id, name="svc", local_path="/tmp/svc")
    session.add(repo)
    session.commit()
    session.add(
        RepositoryDNA(
            repository_id=repo.id,
            risk_flags=["No CI configuration detected"],
            confidence=0.8,
        )
    )
    session.commit()


def test_generate_recommendations_route(client, tmp_path) -> None:
    project_id = client.post("/projects", json={"name": "Route Reco", "slug": "route-reco"}).json()["id"]
    session = _same_file_session(tmp_path)
    try:
        _seed_dna_with_risk_flag(session, project_id)
    finally:
        session.close()

    resp = client.post(f"/projects/{project_id}/recommendations/generate")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["project_id"] == project_id
    assert body[0]["evidence"]

    # idempotent through the route too
    second = client.post(f"/projects/{project_id}/recommendations/generate")
    assert second.status_code == 200
    assert second.json() == []

    listing = client.get(f"/projects/{project_id}/recommendations")
    assert len(listing.json()) == 1


def test_generate_recommendations_route_missing_project_404(client) -> None:
    resp = client.post(f"/projects/{UNKNOWN_ID}/recommendations/generate")
    assert resp.status_code == 404
