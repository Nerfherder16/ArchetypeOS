"""AOS-RESEARCH-COUNCIL-001: a deep research run reaches the Agent Council.

Closes AOS-REVIEW-003 seam #5 — `execute_research_run` writes a `ResearchRun`
but the council's evidence selector (`_select_research`) reads `ResearchNote`,
so multi-phase research never became council evidence. `execute_research_run`
now also get-or-creates one `ResearchNote` keyed on `job_id` (when a job_id is
supplied), so the council picks it up like any other research note.

Hermetic + deterministic (tmp sqlite, no network) — mirrors the fixture/seed
pattern of `test_research_run.py`.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.models import Project, ResearchNote
from aos_core.services.council import _select_research
from aos_core.services.llm_router import Sensitivity
from aos_core.services.research_plan import create_research_plan
from aos_core.services.research_run import execute_research_run

import pytest


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'seam.db'}",
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


def test_execute_research_run_emits_research_note_for_job(db):
    project = _seed(db)
    plan = create_research_plan(
        db, project_id=project.id, question="vector database sharding", sensitivity=Sensitivity.PUBLIC
    )
    run = execute_research_run(db, plan, job_id="j1")

    notes = db.query(ResearchNote).filter(ResearchNote.job_id == "j1").all()
    assert len(notes) == 1
    note = notes[0]
    assert note.project_id == project.id
    assert note.question == plan.question
    assert note.summary
    assert note.findings == run.findings
    assert note.sources == run.sources
    assert note.confidence == run.confidence
    assert note.freshness


def test_existing_note_for_job_id_is_not_duplicated(db):
    # `ResearchRun` itself already enforces "one run per originating job"
    # (`uq_research_runs_job_id`, AOS-JOBS-RELIABILITY-001 Slice 3), and the worker
    # handler (`apps/worker/app/handlers/research_run.py`) checks for an existing
    # `ResearchRun` before calling `execute_research_run` at all — so the function
    # is never actually invoked twice for the same job_id in production, and a
    # literal second call would raise on the ResearchRun insert alone, independent
    # of the ResearchNote get-or-create under test here. What DOES need covering is
    # the get-or-create guard itself: pre-seed a ResearchNote already keyed on
    # job_id "j1" (as if a prior note-writing step already ran for this job) and
    # confirm `execute_research_run` does not insert a second one (which would
    # otherwise violate `uq_research_notes_job_id`).
    project = _seed(db)
    plan = create_research_plan(
        db, project_id=project.id, question="vector database sharding", sensitivity=Sensitivity.PUBLIC
    )
    db.add(
        ResearchNote(
            project_id=project.id,
            title="Research: pre-existing",
            question="vector database sharding",
            summary="a note already recorded for this job",
            sources=[],
            findings=[],
            confidence=0.1,
            job_id="j1",
        )
    )
    db.commit()

    execute_research_run(db, plan, job_id="j1")

    notes = db.query(ResearchNote).filter(ResearchNote.job_id == "j1").all()
    assert len(notes) == 1
    assert notes[0].summary == "a note already recorded for this job"


def test_job_id_none_creates_no_research_note(db):
    project = _seed(db)
    plan = create_research_plan(
        db, project_id=project.id, question="vector database sharding", sensitivity=Sensitivity.PUBLIC
    )
    before = db.query(ResearchNote).filter(ResearchNote.project_id == project.id).count()
    execute_research_run(db, plan)
    after = db.query(ResearchNote).filter(ResearchNote.project_id == project.id).count()

    assert after == before


def test_council_select_research_returns_the_run_note(db):
    project = _seed(db)
    plan = create_research_plan(
        db, project_id=project.id, question="vector database sharding", sensitivity=Sensitivity.PUBLIC
    )
    execute_research_run(db, plan, job_id="j2")

    note = db.query(ResearchNote).filter(ResearchNote.job_id == "j2").one()
    items = _select_research(db, project.id)
    refs = {item["ref"] for item in items}
    assert f"research_note:{note.id}" in refs
