"""Tests for AOS-EVIDENCE-BACKFILL-001 (RFC-0018 C5 reconciliation).

Hermetic: sqlite, no network/LLM. Service-level tests use the bare
``db_session`` fixture (mirrors ``test_recommendation_engine.py``'s pattern of
seeding ``Repository``/``RepositoryDNA``/... directly); the HTTP-level test
seeds through a same-sqlite-file session (mirrors ``test_evidence_api.py``'s
``_same_file_session`` pattern) and drives the route via ``client``.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.foundation.enums import TruthLayer
from aos_core.foundation.truth import MinterClass, may_mint
from aos_core.models import (
    Claim,
    Decision,
    Evaluation,
    Project,
    Recommendation,
    Repository,
    RepositoryDNA,
    ResearchPlan,
    ResearchRun,
    Risk,
)
from aos_core.services.evidence_backfill import backfill_project

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def _same_file_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _make_project(db, slug: str = "evidence-backfill") -> Project:
    project = Project(name="Evidence Backfill", slug=slug)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _seed_all(db, project_id: str) -> None:
    """One row of every backfill-eligible source type, attached to ``project_id``."""
    repo = Repository(project_id=project_id, name="svc", local_path="/tmp/svc")
    db.add(repo)
    db.commit()

    db.add(
        RepositoryDNA(
            repository_id=repo.id,
            language_mix={"python": 0.9, "shell": 0.1},
            package_managers=["pip"],
            frameworks=["fastapi"],
            runtime_services=["postgres"],
            confidence=0.8,
        )
    )

    db.add(
        Decision(
            project_id=project_id,
            title="Adopt local-first deployment",
            decision="Adopt a local-first deployment model.",
            status="approved",
            confidence=0.9,
            approved_by="operator@example.com",
        )
    )
    db.add(
        Decision(
            project_id=project_id,
            title="Draft decision",
            decision="Consider a message queue.",
            status="draft",
            confidence=0.4,
        )
    )

    db.add(
        Recommendation(
            project_id=project_id,
            title="Use pgvector",
            recommendation="Adopt pgvector for embeddings.",
            rationale="Avoids an extra vector-DB dependency.",
            confidence=0.7,
        )
    )

    db.add(
        Evaluation(
            project_id=project_id,
            evaluation_type="fitness_scan",
            score=0.82,
            findings=[{"finding": "No test directory detected"}],
        )
    )

    db.add(
        Risk(
            project_id=project_id,
            title="No CI configuration",
            description="The repository has no CI pipeline.",
            severity="high",
            likelihood="medium",
        )
    )

    plan = ResearchPlan(project_id=project_id, question="Is pgvector production-ready?")
    db.add(plan)
    db.commit()
    db.add(
        ResearchRun(
            plan_id=plan.id,
            project_id=project_id,
            findings=[{"finding": "pgvector is used in production by several orgs", "source_ref": "s1"}],
            confidence=0.6,
        )
    )
    db.commit()


# ---------------------------------------------------------------------------
# RepositoryDNA -> observed claims
# ---------------------------------------------------------------------------


def test_backfill_repository_dna_produces_observed_claims(db_session) -> None:
    project = _make_project(db_session)
    repo = Repository(project_id=project.id, name="svc", local_path="/tmp/svc")
    db_session.add(repo)
    db_session.commit()
    db_session.add(
        RepositoryDNA(
            repository_id=repo.id,
            language_mix={"python": 1.0},
            frameworks=["fastapi"],
            runtime_services=["postgres"],
            confidence=0.8,
        )
    )
    db_session.commit()

    counts = backfill_project(db_session, project.id)
    assert counts["repository_dna"]["claims_created"] == 3  # languages, frameworks, runtime_services
    assert counts["repository_dna"]["sources_created"] == 1
    assert counts["repository_dna"]["fragments_created"] == 3

    claims = db_session.query(Claim).filter(Claim.project_id == project.id).all()
    assert len(claims) == 3
    for claim in claims:
        assert claim.truth_layer == "observed"
        assert claim.minted_by == "deterministic_tool"

    from aos_core.models import ClaimEvidenceLink

    links = db_session.query(ClaimEvidenceLink).all()
    assert len(links) == 3
    for link in links:
        assert link.claim_id in {c.id for c in claims}


# ---------------------------------------------------------------------------
# Decision -> decided (approved) / decision_candidate inferred (non-approved)
# ---------------------------------------------------------------------------


def test_backfill_approved_decision_yields_decided_claim(db_session) -> None:
    project = _make_project(db_session)
    db_session.add(
        Decision(
            project_id=project.id,
            title="Adopt local-first deployment",
            decision="Adopt a local-first deployment model.",
            status="approved",
            confidence=0.9,
            approved_by="operator@example.com",
        )
    )
    db_session.commit()

    counts = backfill_project(db_session, project.id)
    assert counts["decision"]["claims_created"] == 1

    claim = db_session.query(Claim).filter(Claim.project_id == project.id).one()
    assert claim.truth_layer == "decided"
    assert claim.minted_by == "approval_process"
    assert claim.decision_id is not None


def test_backfill_non_approved_decision_yields_inferred_decision_candidate(db_session) -> None:
    project = _make_project(db_session)
    db_session.add(
        Decision(
            project_id=project.id,
            title="Draft decision",
            decision="Consider a message queue.",
            status="draft",
            confidence=0.4,
        )
    )
    db_session.commit()

    counts = backfill_project(db_session, project.id)
    assert counts["decision"]["claims_created"] == 1

    claim = db_session.query(Claim).filter(Claim.project_id == project.id).one()
    assert claim.truth_layer == "inferred"
    assert claim.minted_by == "deterministic_tool"
    assert claim.claim_type == "decision_candidate"
    assert claim.decision_id is None  # never decided directly (C1)


# ---------------------------------------------------------------------------
# Recommendation / ResearchRun / Risk -> inferred claims
# ---------------------------------------------------------------------------


def test_backfill_recommendation_yields_inferred_claim(db_session) -> None:
    project = _make_project(db_session)
    db_session.add(
        Recommendation(
            project_id=project.id,
            title="Use pgvector",
            recommendation="Adopt pgvector for embeddings.",
            rationale="Avoids an extra vector-DB dependency.",
            confidence=0.7,
        )
    )
    db_session.commit()

    counts = backfill_project(db_session, project.id)
    assert counts["recommendation"]["claims_created"] == 1
    claim = db_session.query(Claim).filter(Claim.project_id == project.id).one()
    assert claim.truth_layer == "inferred"
    assert claim.minted_by == "deterministic_tool"


def test_backfill_research_run_yields_inferred_claim(db_session) -> None:
    project = _make_project(db_session)
    plan = ResearchPlan(project_id=project.id, question="Is pgvector production-ready?")
    db_session.add(plan)
    db_session.commit()
    db_session.add(
        ResearchRun(
            plan_id=plan.id,
            project_id=project.id,
            findings=[{"finding": "pgvector is used in production", "source_ref": "s1"}],
            confidence=0.6,
        )
    )
    db_session.commit()

    counts = backfill_project(db_session, project.id)
    assert counts["research_run"]["claims_created"] == 1
    claim = db_session.query(Claim).filter(Claim.project_id == project.id).one()
    assert claim.truth_layer == "inferred"
    assert claim.minted_by == "deterministic_tool"


def test_backfill_risk_yields_inferred_claim(db_session) -> None:
    project = _make_project(db_session)
    db_session.add(
        Risk(
            project_id=project.id,
            title="No CI configuration",
            description="The repository has no CI pipeline.",
            severity="high",
            likelihood="medium",
        )
    )
    db_session.commit()

    counts = backfill_project(db_session, project.id)
    assert counts["risk"]["claims_created"] == 1
    claim = db_session.query(Claim).filter(Claim.project_id == project.id).one()
    assert claim.truth_layer == "inferred"
    assert claim.minted_by == "deterministic_tool"
    assert claim.claim_type == "risk"
    assert claim.materiality == "high"


def test_backfill_evaluation_yields_observed_score_and_inferred_findings(db_session) -> None:
    project = _make_project(db_session)
    db_session.add(
        Evaluation(
            project_id=project.id,
            evaluation_type="fitness_scan",
            score=0.82,
            findings=[{"finding": "No test directory detected"}],
        )
    )
    db_session.commit()

    counts = backfill_project(db_session, project.id)
    assert counts["evaluation"]["claims_created"] == 2

    claims = {c.truth_layer: c for c in db_session.query(Claim).filter(Claim.project_id == project.id).all()}
    assert claims["observed"].minted_by == "deterministic_tool"
    assert claims["inferred"].minted_by == "deterministic_tool"


# ---------------------------------------------------------------------------
# Idempotency: a second run creates ZERO new rows
# ---------------------------------------------------------------------------


def test_backfill_project_is_idempotent(db_session) -> None:
    project = _make_project(db_session)
    _seed_all(db_session, project.id)

    first = backfill_project(db_session, project.id)
    assert first["totals"]["claims_created"] > 0

    claim_count_after_first = db_session.query(Claim).count()

    second = backfill_project(db_session, project.id)
    assert second["totals"]["claims_created"] == 0
    assert second["totals"]["sources_created"] == 0
    assert second["totals"]["versions_created"] == 0
    assert second["totals"]["fragments_created"] == 0
    assert second["totals"]["claims_skipped"] == first["totals"]["claims_created"]

    assert db_session.query(Claim).count() == claim_count_after_first


# ---------------------------------------------------------------------------
# C3 respected across every backfilled claim
# ---------------------------------------------------------------------------


def test_backfill_never_violates_c3(db_session) -> None:
    project = _make_project(db_session)
    _seed_all(db_session, project.id)
    backfill_project(db_session, project.id)

    claims = db_session.query(Claim).filter(Claim.project_id == project.id).all()
    assert claims  # sanity: the seed actually produced claims
    for claim in claims:
        minter = MinterClass(claim.minted_by)
        assert may_mint(minter, TruthLayer(claim.truth_layer))
        # No deterministic_tool claim is ever "claimed" or "decided".
        if minter == MinterClass.DETERMINISTIC_TOOL:
            assert claim.truth_layer in ("observed", "inferred")


# ---------------------------------------------------------------------------
# HTTP route: returns counts, idempotent over HTTP
# ---------------------------------------------------------------------------


def test_evidence_backfill_route_returns_counts_and_is_idempotent(client, tmp_path) -> None:
    project_id = client.post("/projects", json={"name": "Route Backfill", "slug": "route-backfill"}).json()["id"]
    session = _same_file_session(tmp_path)
    try:
        _seed_all(session, project_id)
    finally:
        session.close()

    first = client.post(f"/projects/{project_id}/evidence-backfill")
    assert first.status_code == 200, first.text
    first_counts = first.json()
    assert first_counts["totals"]["claims_created"] > 0

    second = client.post(f"/projects/{project_id}/evidence-backfill")
    assert second.status_code == 200, second.text
    second_counts = second.json()
    assert second_counts["totals"]["claims_created"] == 0
    assert second_counts["totals"]["sources_created"] == 0
    assert second_counts["totals"]["claims_skipped"] == first_counts["totals"]["claims_created"]


def test_evidence_backfill_route_missing_project_404(client) -> None:
    resp = client.post(f"/projects/{UNKNOWN_ID}/evidence-backfill")
    assert resp.status_code == 404
