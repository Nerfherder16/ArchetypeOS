"""Unit tests for the research-run executor (AOS-RESEARCH-003, criteria 2-5).

Hermetic + deterministic (tmp sqlite, no network). Seeds the local corpus with
prior research notes so the run has sources to rank, then asserts the run records
its phases, accepts/rejects sources WITH REASON, cites accepted sources in
findings, keeps conflicts visible, and spawns follow-up plans from open questions.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.models import Project, ResearchNote, ResearchPlan, ResearchRun
from aos_core.services.llm_router import Sensitivity
from aos_core.services.research_plan import create_research_plan
from aos_core.services.research_run import execute_research_run

import pytest


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'run.db'}",
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


def _seed(db):
    project = Project(name="Recall", slug="recall")
    db.add(project)
    db.commit()
    # Prior research notes that address the question → become rankable sources.
    for i, title in enumerate(
        ["Qdrant sharding guide", "Vector database comparison", "Unrelated billing note"]
    ):
        db.add(
            ResearchNote(
                project_id=project.id,
                title=title,
                question="q",
                summary=f"note {i} about vector database sharding" if i < 2 else "invoices",
                sources=[],
                findings=[],
                confidence=0.5,
            )
        )
    db.commit()
    return project


def test_execute_research_run_records_phases_in_order(db):
    project = _seed(db)
    plan = create_research_plan(
        db, project_id=project.id, question="vector database sharding", sensitivity=Sensitivity.PUBLIC
    )
    run = execute_research_run(db, plan)

    assert run.plan_id == plan.id
    assert run.run_status == "completed"
    phase_names = [p["phase"] for p in run.phases]
    assert phase_names == ["plan", "search", "fetch", "verify", "synthesize"]


def test_execute_research_run_accepts_and_rejects_sources_with_reason(db):
    project = _seed(db)
    plan = create_research_plan(
        db, project_id=project.id, question="vector database sharding", sensitivity=Sensitivity.PUBLIC
    )
    run = execute_research_run(db, plan)

    # Every recorded source carries an accept/reject decision and a reason.
    assert run.sources, "the run must record the sources it considered"
    for source in run.sources:
        assert "accepted" in source
        assert "ref" in source
        if not source["accepted"]:
            assert source["reason"], "a rejected source must carry a reason"
    accepted = [s for s in run.sources if s["accepted"]]
    assert accepted, "at least one relevant source should be accepted"


def test_execute_research_run_findings_cite_accepted_sources(db):
    project = _seed(db)
    plan = create_research_plan(
        db, project_id=project.id, question="vector database sharding", sensitivity=Sensitivity.PUBLIC
    )
    run = execute_research_run(db, plan)

    accepted_refs = {s["ref"] for s in run.sources if s["accepted"]}
    assert run.findings
    for finding in run.findings:
        assert finding["source_ref"] in accepted_refs, "findings must cite an accepted source"


def test_execute_research_run_keeps_conflicts_visible(db):
    project = _seed(db)
    plan = create_research_plan(
        db, project_id=project.id, question="vector database sharding", sensitivity=Sensitivity.PUBLIC
    )
    run = execute_research_run(db, plan)
    # The conflicts field exists and is a list (visible, not flattened away), even
    # if the deterministic floor finds none for this corpus.
    assert isinstance(run.conflicts, list)


def test_open_questions_become_follow_up_plans(db):
    project = _seed(db)
    # A question with no matching corpus → thin coverage → open questions.
    plan = create_research_plan(
        db, project_id=project.id, question="kubernetes operator upgrade strategy", sensitivity=Sensitivity.PUBLIC
    )
    run = execute_research_run(db, plan)

    assert run.open_questions, "a thinly-covered question should produce open questions"
    # Each open question is turned into a follow-up plan (criterion 5).
    follow_ups = (
        db.query(ResearchPlan)
        .filter(ResearchPlan.project_id == project.id, ResearchPlan.plan_status == "follow_up")
        .all()
    )
    assert len(follow_ups) == len(run.open_questions)
    follow_up_questions = {p.question for p in follow_ups}
    assert follow_up_questions == set(run.open_questions)


def test_execute_research_run_persists_and_reloads(db):
    project = _seed(db)
    plan = create_research_plan(
        db, project_id=project.id, question="vector database sharding", sensitivity=Sensitivity.PUBLIC
    )
    run = execute_research_run(db, plan)
    reloaded = db.query(ResearchRun).filter(ResearchRun.id == run.id).one()
    assert reloaded.plan_id == plan.id
    assert isinstance(reloaded.confidence, float)
