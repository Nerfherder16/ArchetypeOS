"""API tests for the Council & Validation HTTP surface (RFC-0021, Foundation
Intelligence Slice 4, AOS-COUNCIL-VALIDATION-API-001).

Thin-wrapper routes over ``services/foundation_council.py`` — these tests
exercise the HTTP layer (status codes, DTO shape, 404/409/422 mapping).
Hermetic: the shared ``client`` fixture (sqlite, no network/LLM). State that
the HTTP surface has no route for yet (opening a run, compiling requirements,
generating candidates, scoring) is seeded directly via the engine on a second
session bound to the *same* sqlite file the ``client`` fixture uses (mirrors
``test_council_api.py``'s ``FakeRedis``/``_same_file_session`` pattern and
``test_foundation_api.py``'s helpers). The review itself is always driven
through ``review_candidate`` with the hermetic ``DeterministicProvider`` —
the review-enqueue *route* only asserts the job gets queued; it does not run
the council inline.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.foundation.enums import CandidateStatus
from aos_core.llm import DeterministicProvider
from aos_core.models import FoundationObjection, Project, Repository, RepositoryDNA, ValidationTask
from aos_core.services.evidence import create_claim
from aos_core.services.foundation import compile_requirements, evaluate_eligibility, generate_candidates, open_selection_run, score_candidate
from aos_core.services.foundation_council import record_validation_result, resolve_objection, review_candidate
from aos_core.services.genome import generate_genome

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


class FakeRedis:
    """Captures lpush so the enqueue path needs no real Redis (dead port in conftest)."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append(value)


def _same_file_session(tmp_path):
    """A session on the same sqlite file the `client` fixture uses, for direct seeding."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _rich_reviewable_run(db, slug: str):
    """Mirrors ``test_foundation_council_engine.py``'s ``_rich_reviewable_run``: a
    project with a hard-constraint claim, a runtime fact, and a repository risk
    flag, walked all the way through eligibility + scoring. Returns
    ``(project, run, candidates)`` with every eligible candidate already scored."""
    project = Project(name=slug, slug=slug)
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
    for candidate in candidates:
        db.refresh(candidate)
        if candidate.status == CandidateStatus.ELIGIBLE.value:
            score_candidate(db, candidate_id=candidate.id)
    db.commit()
    for candidate in candidates:
        db.refresh(candidate)
    db.refresh(run)
    return project, run, candidates


def _drive_full_walkthrough(db, run, candidate):
    """Reviews ``candidate``, resolves every blocking objection, and passes
    every blocking validation task — leaving the candidate clear-eligible and
    ready for ``select_candidate``/the HTTP ``/select`` route."""
    review_candidate(db, candidate_id=candidate.id, provider=DeterministicProvider())
    db.refresh(candidate)

    blocking_objections = (
        db.query(FoundationObjection)
        .filter(
            FoundationObjection.candidate_id == candidate.id,
            FoundationObjection.blocking.is_(True),
            FoundationObjection.status == "open",
        )
        .all()
    )
    for objection in blocking_objections:
        resolve_objection(
            db, objection_id=objection.id, status="accepted_exception",
            resolution="Reviewed and accepted as a known, tracked risk.",
        )

    blocking_tasks = (
        db.query(ValidationTask)
        .filter(ValidationTask.candidate_id == candidate.id, ValidationTask.blocking.is_(True))
        .all()
    )
    for task in blocking_tasks:
        record_validation_result(db, validation_task_id=task.id, outcome="passed", summary="Cleared with additional evidence.")

    db.commit()
    db.refresh(candidate)
    db.refresh(run)


# ---------------------------------------------------------------------------
# Council review enqueue
# ---------------------------------------------------------------------------


def test_council_review_endpoint_enqueues(client, tmp_path, monkeypatch):
    import app.main as main

    fake = FakeRedis()
    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: fake)

    session = _same_file_session(tmp_path)
    try:
        project, run, candidates = _rich_reviewable_run(session, "council-api-enqueue")
        candidate = candidates[0]
    finally:
        session.close()

    resp = client.post(f"/candidates/{candidate.id}/council-review", json={"actor": "ops@example.com"})
    assert resp.status_code == 200, resp.text
    job = resp.json()
    assert job["job_type"] == "foundation_council_review"
    assert job["status"] == "queued"
    assert job["project_id"] == project.id
    assert job["payload"]["candidate_id"] == candidate.id
    assert fake.queue == [job["id"]]


def test_council_review_endpoint_missing_candidate_404(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: FakeRedis())
    resp = client.post(f"/candidates/{UNKNOWN_ID}/council-review", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# select
# ---------------------------------------------------------------------------


def test_select_endpoint_409_before_clear_eligible(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, run, candidates = _rich_reviewable_run(session, "council-api-select-409")
        candidate = candidates[0]
    finally:
        session.close()

    resp = client.post(f"/foundation-runs/{run.id}/select", json={"candidate_id": candidate.id, "approver": "ops@example.com"})
    assert resp.status_code == 409, resp.text


def test_select_endpoint_200_after_full_walkthrough(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, run, candidates = _rich_reviewable_run(session, "council-api-select-200")
        candidate = candidates[0]
        _drive_full_walkthrough(session, run, candidate)
    finally:
        session.close()

    resp = client.post(f"/foundation-runs/{run.id}/select", json={"candidate_id": candidate.id, "approver": "ops@example.com"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == candidate.id
    assert body["status"] == "selected"


def test_select_endpoint_missing_run_404(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, _run, candidates = _rich_reviewable_run(session, "council-api-select-404")
        candidate = candidates[0]
    finally:
        session.close()

    resp = client.post(f"/foundation-runs/{UNKNOWN_ID}/select", json={"candidate_id": candidate.id, "approver": "ops@example.com"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# synthesize-dossier
# ---------------------------------------------------------------------------


def test_synthesize_dossier_endpoint_recommends_clear_candidate(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, run, candidates = _rich_reviewable_run(session, "council-api-dossier")
        candidate = candidates[0]
        _drive_full_walkthrough(session, run, candidate)
    finally:
        session.close()

    resp = client.post(f"/foundation-runs/{run.id}/synthesize-dossier")
    assert resp.status_code == 200, resp.text
    dossier = resp.json()
    assert dossier["recommended_candidate_id"] == candidate.id
    assert dossier["verdict"] == "Recommended"
    assert dossier["selection_run_id"] == run.id


def test_synthesize_dossier_endpoint_missing_run_404(client):
    resp = client.post(f"/foundation-runs/{UNKNOWN_ID}/synthesize-dossier")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# resolve objection
# ---------------------------------------------------------------------------


def test_resolve_objection_endpoint_happy_path(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, _run, candidates = _rich_reviewable_run(session, "council-api-resolve")
        candidate = candidates[0]
        review_candidate(session, candidate_id=candidate.id, provider=DeterministicProvider())
        objection = (
            session.query(FoundationObjection).filter(FoundationObjection.candidate_id == candidate.id).first()
        )
        objection_id = objection.id
    finally:
        session.close()

    resp = client.post(f"/foundation-objections/{objection_id}/resolve", json={"status": "resolved", "resolution": "Fixed."})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["resolution"] == "Fixed."


def test_resolve_objection_endpoint_already_resolved_409(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, _run, candidates = _rich_reviewable_run(session, "council-api-resolve-409")
        candidate = candidates[0]
        review_candidate(session, candidate_id=candidate.id, provider=DeterministicProvider())
        objection = (
            session.query(FoundationObjection).filter(FoundationObjection.candidate_id == candidate.id).first()
        )
        objection_id = objection.id
    finally:
        session.close()

    first = client.post(f"/foundation-objections/{objection_id}/resolve", json={"status": "resolved"})
    assert first.status_code == 200, first.text

    second = client.post(f"/foundation-objections/{objection_id}/resolve", json={"status": "accepted_exception"})
    assert second.status_code == 409, second.text


def test_resolve_objection_endpoint_missing_404(client):
    resp = client.post(f"/foundation-objections/{UNKNOWN_ID}/resolve", json={"status": "resolved"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# record validation result
# ---------------------------------------------------------------------------


def test_record_validation_result_endpoint_200(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, _run, candidates = _rich_reviewable_run(session, "council-api-result-200")
        candidate = candidates[0]
        review_candidate(session, candidate_id=candidate.id, provider=DeterministicProvider())
        task = session.query(ValidationTask).filter(ValidationTask.candidate_id == candidate.id).first()
        task_id = task.id
    finally:
        session.close()

    resp = client.post(
        f"/validation-tasks/{task_id}/result",
        json={"outcome": "passed", "summary": "Backed by a real benchmark run.", "benchmark_ref": "bench-1"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome"] == "passed"
    assert body["validation_task_id"] == task_id
    assert body["benchmark_ref"] == "bench-1"


def test_record_validation_result_endpoint_illegal_outcome_409(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, _run, candidates = _rich_reviewable_run(session, "council-api-result-409")
        candidate = candidates[0]
        review_candidate(session, candidate_id=candidate.id, provider=DeterministicProvider())
        task = session.query(ValidationTask).filter(ValidationTask.candidate_id == candidate.id).first()
        task_id = task.id
    finally:
        session.close()

    resp = client.post(f"/validation-tasks/{task_id}/result", json={"outcome": "maybe"})
    assert resp.status_code == 409, resp.text


def test_record_validation_result_endpoint_missing_404(client):
    resp = client.post(f"/validation-tasks/{UNKNOWN_ID}/result", json={"outcome": "passed"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET list / detail
# ---------------------------------------------------------------------------


def test_list_candidate_objections_endpoint(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, _run, candidates = _rich_reviewable_run(session, "council-api-list-objections")
        candidate = candidates[0]
        review_candidate(session, candidate_id=candidate.id, provider=DeterministicProvider())
    finally:
        session.close()

    resp = client.get(f"/candidates/{candidate.id}/objections")
    assert resp.status_code == 200, resp.text
    objections = resp.json()
    assert objections
    assert all(o["candidate_id"] == candidate.id for o in objections)


def test_list_candidate_objections_endpoint_missing_candidate_404(client):
    resp = client.get(f"/candidates/{UNKNOWN_ID}/objections")
    assert resp.status_code == 404


def test_get_objection_endpoint(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, _run, candidates = _rich_reviewable_run(session, "council-api-get-objection")
        candidate = candidates[0]
        review_candidate(session, candidate_id=candidate.id, provider=DeterministicProvider())
        objection = (
            session.query(FoundationObjection).filter(FoundationObjection.candidate_id == candidate.id).first()
        )
        objection_id = objection.id
    finally:
        session.close()

    resp = client.get(f"/foundation-objections/{objection_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == objection_id


def test_get_objection_endpoint_missing_404(client):
    resp = client.get(f"/foundation-objections/{UNKNOWN_ID}")
    assert resp.status_code == 404


def test_list_run_validation_tasks_endpoint(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, run, candidates = _rich_reviewable_run(session, "council-api-list-tasks")
        candidate = candidates[0]
        review_candidate(session, candidate_id=candidate.id, provider=DeterministicProvider())
    finally:
        session.close()

    resp = client.get(f"/foundation-runs/{run.id}/validation-tasks")
    assert resp.status_code == 200, resp.text
    tasks = resp.json()
    assert tasks
    assert all(t["selection_run_id"] == run.id for t in tasks)


def test_list_run_validation_tasks_endpoint_missing_run_404(client):
    resp = client.get(f"/foundation-runs/{UNKNOWN_ID}/validation-tasks")
    assert resp.status_code == 404


def test_get_validation_task_detail_endpoint_includes_results(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, _run, candidates = _rich_reviewable_run(session, "council-api-task-detail")
        candidate = candidates[0]
        review_candidate(session, candidate_id=candidate.id, provider=DeterministicProvider())
        task = session.query(ValidationTask).filter(ValidationTask.candidate_id == candidate.id).first()
        task_id = task.id
        record_validation_result(session, validation_task_id=task_id, outcome="passed", summary="Cleared.")
    finally:
        session.close()

    resp = client.get(f"/validation-tasks/{task_id}")
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["id"] == task_id
    assert len(detail["results"]) == 1
    assert detail["results"][0]["outcome"] == "passed"


def test_get_validation_task_detail_endpoint_missing_404(client):
    resp = client.get(f"/validation-tasks/{UNKNOWN_ID}")
    assert resp.status_code == 404


def test_get_run_dossier_endpoint(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, run, candidates = _rich_reviewable_run(session, "council-api-get-dossier")
        candidate = candidates[0]
        _drive_full_walkthrough(session, run, candidate)
        from aos_core.services.foundation_council import synthesize_dossier

        synthesize_dossier(session, selection_run_id=run.id)
    finally:
        session.close()

    resp = client.get(f"/foundation-runs/{run.id}/dossier")
    assert resp.status_code == 200, resp.text
    dossier = resp.json()
    assert dossier["selection_run_id"] == run.id
    assert dossier["recommended_candidate_id"] == candidate.id


def test_get_run_dossier_endpoint_missing_run_404(client):
    resp = client.get(f"/foundation-runs/{UNKNOWN_ID}/dossier")
    assert resp.status_code == 404


def test_get_run_dossier_endpoint_no_dossier_yet_404(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        _project, run, _candidates = _rich_reviewable_run(session, "council-api-no-dossier")
        run_id = run.id
    finally:
        session.close()

    resp = client.get(f"/foundation-runs/{run_id}/dossier")
    assert resp.status_code == 404
