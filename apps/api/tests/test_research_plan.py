"""Unit tests for the multi-phase research plan (AOS-RESEARCH-003, Finding 15).

Hermetic + deterministic (tmp sqlite, no network, no model). Covers the PR1
scope: a research plan is BUILT and PERSISTED before any source is fetched, with
its search queries, verification steps, and synthesis policy recorded.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.models import Project, ResearchPlan
from aos_core.services.llm_router import Sensitivity
from aos_core.services.research_plan import build_plan_spec, create_research_plan

import pytest


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'plan.db'}",
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


def _project(db) -> Project:
    project = Project(name="Recall", slug="recall")
    db.add(project)
    db.commit()
    return project


def test_build_plan_spec_is_deterministic_and_populated():
    spec_a = build_plan_spec("best vector database for local memory", Sensitivity.PUBLIC)
    spec_b = build_plan_spec("best vector database for local memory", Sensitivity.PUBLIC)
    # Deterministic: same question → identical plan (no wall-clock, no randomness).
    assert spec_a == spec_b
    # Every plan facet is populated before any fetch happens.
    assert spec_a["search_queries"], "a plan must record search queries before fetching"
    assert spec_a["required_source_types"]
    assert spec_a["verification_steps"]
    assert isinstance(spec_a["synthesis_policy"], dict)
    # The synthesis policy commits to citing sources and recording open questions.
    assert spec_a["synthesis_policy"]["cite_sources"] is True
    assert spec_a["synthesis_policy"]["record_open_questions"] is True
    # The original question seeds the first search query.
    assert any("vector database" in q for q in spec_a["search_queries"])


def test_create_research_plan_persists_the_plan_before_fetch(db):
    project = _project(db)
    plan = create_research_plan(
        db, project_id=project.id, question="how should we shard qdrant", sensitivity=Sensitivity.PUBLIC
    )
    # Persisted with status 'planned' — recorded before any source is fetched.
    assert plan.id
    assert plan.plan_status == "planned"
    assert plan.question == "how should we shard qdrant"
    assert plan.sensitivity == "public"
    assert plan.search_queries
    assert plan.verification_steps
    assert plan.synthesis_policy["cite_sources"] is True

    # Round-trips from the DB.
    reloaded = db.query(ResearchPlan).filter(ResearchPlan.id == plan.id).one()
    assert reloaded.question == "how should we shard qdrant"
    assert reloaded.search_queries == plan.search_queries


def test_create_research_plan_carries_sensitivity(db):
    project = _project(db)
    plan = create_research_plan(
        db, project_id=project.id, question="internal auth token rotation", sensitivity=Sensitivity.PRIVATE
    )
    assert plan.sensitivity == "private"
