"""Worker test for the ``foundation_council_review`` handler (RFC-0021,
Foundation Intelligence Slice 4, AOS-COUNCIL-VALIDATION-API-001).

Exercises the handler END TO END through ``worker.run_job`` (claim → dispatch →
complete), the path the API's ``POST /candidates/{id}/council-review`` enqueues:
the handler resolves the (deterministic) council provider, runs
``review_candidate`` over a reviewable candidate, stamps the review's ``job_id``,
and completes the job with ``{review_id, verdict}``. Also asserts redelivery
idempotency (a second ``run_job`` for the same job returns the same review, not a
duplicate) — the handler's ``CouncilReview.job_id`` guard, mirroring
``council_review.py``'s P0-3 fix.

Hermetic: the ``worker_db`` fixture (``test_worker.py``) creates every table via
sqlite ``create_all`` and points ``worker.SessionLocal`` at the test DB; the
council runs on the ``DeterministicProvider`` (no network), so the ledger sink is
inert (``InstrumentedProvider`` skips the deterministic tier).
"""

from __future__ import annotations

import os
from collections.abc import Generator

os.environ.setdefault("DATABASE_URL", "sqlite:///./archetypeos_worker_dev.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:9999/0")

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.worker as worker  # noqa: E402
from aos_core.config import get_settings  # noqa: E402
from aos_core.database import Base  # noqa: E402
from aos_core.foundation.enums import CandidateStatus  # noqa: E402
from aos_core.models import (  # noqa: E402
    CouncilReview,
    FoundationCandidate,
    FoundationObjection,
    FoundationSelectionRun,
    Job,
    Project,
    Repository,
    RepositoryDNA,
    ValidationTask,
)
from aos_core.services.evidence import create_claim  # noqa: E402
from aos_core.services.foundation import (  # noqa: E402
    compile_requirements,
    evaluate_eligibility,
    generate_candidates,
    open_selection_run,
    score_candidate,
)
from aos_core.services.genome import generate_genome  # noqa: E402


@pytest.fixture()
def worker_db(tmp_path, monkeypatch) -> Generator[sessionmaker, None, None]:
    """Hermetic worker DB, self-contained (mirrors ``test_worker.py``'s fixture):
    a fresh sqlite engine with every table, with ``worker.SessionLocal``
    monkeypatched to it so ``run_job`` runs against the test DB."""
    monkeypatch.setenv("REPOSITORY_ROOT", str(tmp_path / "repositories"))
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    get_settings.cache_clear()

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(worker, "SessionLocal", testing_session_local)
    try:
        yield testing_session_local
    finally:
        engine.dispose()


def _reviewable_candidate(db):
    """A scored, eligible candidate on an open run with a hard-constraint claim,
    a runtime fact, and a risk-flagged repo (mirrors the engine test's
    ``_rich_reviewable_run``) — enough for ``review_candidate`` to run the
    council and derive objections/tasks. Returns the eligible candidate."""
    project = Project(name="fcr-worker", slug="fcr-worker")
    db.add(project)
    db.commit()

    create_claim(
        db, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="A worker process pulls jobs from a message queue.", claim_type="fact", domain="runtime",
        created_by="repository-scanner", derivation={"method": "direct", "parent_claim_ids": []}, confidence=0.9,
    )
    create_claim(
        db, project_id=project.id, minted_by="human", truth_layer="claimed",
        statement="The deployment environment must not use a public cloud provider.", claim_type="constraint",
        domain="deployment", created_by="product manager", derivation={"method": "direct", "parent_claim_ids": []},
        confidence=0.9,
    )

    repo = Repository(project_id=project.id, name="svc", local_path="svc")
    db.add(repo)
    db.flush()
    db.add(
        RepositoryDNA(
            repository_id=repo.id,
            language_mix={"python": 1.0},
            frameworks=["fastapi"],
            package_managers=["pip"],
            runtime_services=["postgres"],
            risk_flags=["missing tests for the auth module"],
            maturity="beta",
        )
    )
    db.commit()

    genome = generate_genome(db, project_id=project.id, state_view="current")
    run = open_selection_run(db, project_id=project.id, target_genome_snapshot_id=genome.id)
    compile_requirements(db, selection_run_id=run.id)
    candidates = generate_candidates(db, selection_run_id=run.id)
    evaluate_eligibility(db, selection_run_id=run.id)
    eligible = None
    for candidate in candidates:
        db.refresh(candidate)
        if candidate.status == CandidateStatus.ELIGIBLE.value:
            score_candidate(db, candidate_id=candidate.id)
            eligible = candidate
    db.commit()
    assert eligible is not None, "fixture must yield at least one eligible candidate"
    db.refresh(eligible)
    return eligible


def test_foundation_council_review_dispatch(worker_db):
    with worker_db() as db:
        candidate = _reviewable_candidate(db)
        candidate_id = candidate.id
        # project_id must be the candidate's run's project (what the API route
        # looks up before enqueuing).
        run = db.get(FoundationSelectionRun, candidate.selection_run_id)
        job = Job(
            job_type="foundation_council_review",
            status="queued",
            project_id=run.project_id,
            payload={"candidate_id": candidate_id},
        )
        db.add(job)
        db.commit()
        job_id = job.id

    worker.run_job(job_id)

    with worker_db() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed"
        review_id = job.result["review_id"]
        assert review_id
        assert job.result["verdict"]

        review = db.get(CouncilReview, review_id)
        assert review is not None
        assert review.job_id == job_id
        assert review.candidate_id == candidate_id
        assert len(review.agent_outputs) == 4

        # review_candidate advances the reviewed candidate off 'eligible'.
        candidate = db.get(FoundationCandidate, candidate_id)
        assert candidate.status == CandidateStatus.CHALLENGED.value

        # The risk-flagged repo + no decisions/research drive at least one
        # objection and one validation task (design §11 / AD-10).
        objections = db.query(FoundationObjection).filter(FoundationObjection.candidate_id == candidate_id).count()
        tasks = db.query(ValidationTask).filter(ValidationTask.candidate_id == candidate_id).count()
        assert objections >= 1
        assert tasks >= 1


def test_foundation_council_review_idempotent_on_redelivery(worker_db):
    with worker_db() as db:
        candidate = _reviewable_candidate(db)
        candidate_id = candidate.id
        run = db.get(FoundationSelectionRun, candidate.selection_run_id)
        job = Job(
            job_type="foundation_council_review",
            status="queued",
            project_id=run.project_id,
            payload={"candidate_id": candidate_id},
        )
        db.add(job)
        db.commit()
        job_id = job.id

    worker.run_job(job_id)
    with worker_db() as db:
        first_review_id = db.get(Job, job_id).result["review_id"]
        reviews_before = db.query(CouncilReview).filter(CouncilReview.candidate_id == candidate_id).count()

    # Re-dispatch the SAME job: the handler's job_id guard returns the existing
    # review rather than running the council again.
    with worker_db() as db:
        job = db.get(Job, job_id)
        job.status = "queued"
        job.claimed_by = None
        job.claim_token = None
        db.commit()
    worker.run_job(job_id)

    with worker_db() as db:
        second_review_id = db.get(Job, job_id).result["review_id"]
        reviews_after = db.query(CouncilReview).filter(CouncilReview.candidate_id == candidate_id).count()
        assert second_review_id == first_review_id
        assert reviews_after == reviews_before, "redelivery must not create a duplicate review"
