"""API tests for the Foundation Baseline HTTP surface (RFC-0022, Foundation
Intelligence Slice 5, AOS-FOUNDATION-BASELINE-API-001).

Thin-wrapper routes over ``services/foundation_baseline.py`` — these tests
exercise the HTTP layer (status codes, DTO shape, 404/409 mapping). Hermetic:
the shared ``client`` fixture (sqlite, no network/LLM). State the HTTP
surface has no route for yet (walking a run all the way to a SELECTED
candidate) is seeded directly via the engine on a second session bound to the
*same* sqlite file the ``client`` fixture uses — mirrors
``test_foundation_council_api.py``'s ``_same_file_session`` pattern and
``test_foundation_baseline_engine.py``'s ``_drive_to_selected`` recipe.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.foundation.enums import CandidateStatus, SelectionRunState
from aos_core.llm import DeterministicProvider
from aos_core.models import FoundationObjection, FoundationSelectionRun, Project, Repository, RepositoryDNA, ValidationTask
from aos_core.services.evidence import create_claim
from aos_core.services.foundation import compile_requirements, evaluate_eligibility, generate_candidates, open_selection_run, score_candidate
from aos_core.services.foundation_council import record_validation_result, resolve_objection, review_candidate, select_candidate
from aos_core.services.genome import generate_genome

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def _same_file_session(tmp_path):
    """A session on the same sqlite file the `client` fixture uses, for direct seeding."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _project_with_evidence(db, slug: str) -> Project:
    """Mirrors ``test_foundation_baseline_engine.py``'s ``_project_with_evidence``."""
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
    return project


def _open_run(db, project, *, via_service: bool = True) -> FoundationSelectionRun:
    genome = generate_genome(db, project_id=project.id, state_view="current")
    if via_service:
        return open_selection_run(db, project_id=project.id, target_genome_snapshot_id=genome.id)
    # Mirrors test_foundation_baseline_engine.py: a second run for the same
    # project (once the first is baselined) is built directly at the ORM
    # layer, since open_selection_run's one-active-run-per-project gate treats
    # a BASELINED run as still 'active'.
    run = FoundationSelectionRun(
        project_id=project.id, target_genome_snapshot_id=genome.id, corpus_snapshot_id=None,
        state=SelectionRunState.DRAFT.value, summary="", created_by="system", updated_by="system",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _drive_to_selected(db, run: FoundationSelectionRun):
    """compile -> generate -> evaluate -> score -> review -> resolve/pass -> select."""
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

    candidate = next(c for c in candidates if c.status == CandidateStatus.ELIGIBLE.value)

    review_candidate(db, candidate_id=candidate.id, provider=DeterministicProvider())
    db.refresh(candidate)
    db.refresh(run)

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
        record_validation_result(db, validation_task_id=task.id, outcome="passed", summary="Cleared with evidence.")

    db.refresh(run)
    selected = select_candidate(db, selection_run_id=run.id, candidate_id=candidate.id, approver="ops@example.com")
    db.refresh(run)
    return selected, run


# ---------------------------------------------------------------------------
# POST /foundation-runs/{run_id}/baseline — mint
# ---------------------------------------------------------------------------


def test_mint_baseline_endpoint_happy_path(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        project = _project_with_evidence(session, "baseline-api-happy")
        run = _open_run(session, project)
        _candidate, run = _drive_to_selected(session, run)
        run_id = run.id
    finally:
        session.close()

    resp = client.post(f"/foundation-runs/{run_id}/baseline", json={"approver": "ops@example.com"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["baseline_version"] == "1.0"
    assert body["baseline_hash"]
    assert body["selection_run_id"] == run_id

    verify = _same_file_session(tmp_path)
    try:
        refreshed_run = verify.get(FoundationSelectionRun, run_id)
        assert refreshed_run.state == SelectionRunState.BASELINED.value
    finally:
        verify.close()


def test_mint_baseline_endpoint_409_run_not_selected(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        project = _project_with_evidence(session, "baseline-api-not-selected")
        run = _open_run(session, project)  # still 'draft'
        run_id = run.id
    finally:
        session.close()

    resp = client.post(f"/foundation-runs/{run_id}/baseline", json={"approver": "ops@example.com"})
    assert resp.status_code == 409, resp.text


def test_mint_baseline_endpoint_404_missing_run(client):
    resp = client.post(f"/foundation-runs/{UNKNOWN_ID}/baseline", json={"approver": "ops@example.com"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/foundation-baselines
# ---------------------------------------------------------------------------


def test_list_project_baselines_endpoint(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        project = _project_with_evidence(session, "baseline-api-list")
        run = _open_run(session, project)
        _candidate, run = _drive_to_selected(session, run)
        project_id = project.id
        run_id = run.id
    finally:
        session.close()

    mint_resp = client.post(f"/foundation-runs/{run_id}/baseline", json={"approver": "ops@example.com"})
    assert mint_resp.status_code == 200, mint_resp.text
    baseline_id = mint_resp.json()["id"]

    resp = client.get(f"/projects/{project_id}/foundation-baselines")
    assert resp.status_code == 200, resp.text
    baselines = resp.json()
    assert [b["id"] for b in baselines] == [baseline_id]


def test_list_project_baselines_endpoint_missing_project_404(client):
    resp = client.get(f"/projects/{UNKNOWN_ID}/foundation-baselines")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /foundation-baselines/{baseline_id}
# ---------------------------------------------------------------------------


def test_get_foundation_baseline_endpoint_detail(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        project = _project_with_evidence(session, "baseline-api-detail")
        run = _open_run(session, project)
        _candidate, run = _drive_to_selected(session, run)
        run_id = run.id
    finally:
        session.close()

    mint_resp = client.post(f"/foundation-runs/{run_id}/baseline", json={"approver": "ops@example.com"})
    assert mint_resp.status_code == 200, mint_resp.text
    baseline_id = mint_resp.json()["id"]

    resp = client.get(f"/foundation-baselines/{baseline_id}")
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["id"] == baseline_id
    assert detail["elements"]
    assert detail["elements"][0]["baseline_id"] == baseline_id


def test_get_foundation_baseline_endpoint_missing_404(client):
    resp = client.get(f"/foundation-baselines/{UNKNOWN_ID}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /foundation-baselines/{base_id}/compare/{other_id}
# ---------------------------------------------------------------------------


def test_compare_foundation_baselines_endpoint_identity(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        project = _project_with_evidence(session, "baseline-api-compare")
        run = _open_run(session, project)
        _candidate, run = _drive_to_selected(session, run)
        run_id = run.id
    finally:
        session.close()

    mint_resp = client.post(f"/foundation-runs/{run_id}/baseline", json={"approver": "ops@example.com"})
    assert mint_resp.status_code == 200, mint_resp.text
    baseline_id = mint_resp.json()["id"]

    resp = client.get(f"/foundation-baselines/{baseline_id}/compare/{baseline_id}")
    assert resp.status_code == 200, resp.text
    diff = resp.json()
    assert diff["hash_equal"] is True
    assert diff["elements_added"] == []
    assert diff["elements_removed"] == []
    assert diff["elements_changed"] == []


def test_compare_foundation_baselines_endpoint_missing_404(client, tmp_path):
    session = _same_file_session(tmp_path)
    try:
        project = _project_with_evidence(session, "baseline-api-compare-404")
        run = _open_run(session, project)
        _candidate, run = _drive_to_selected(session, run)
        run_id = run.id
    finally:
        session.close()

    mint_resp = client.post(f"/foundation-runs/{run_id}/baseline", json={"approver": "ops@example.com"})
    assert mint_resp.status_code == 200, mint_resp.text
    baseline_id = mint_resp.json()["id"]

    resp = client.get(f"/foundation-baselines/{baseline_id}/compare/{UNKNOWN_ID}")
    assert resp.status_code == 404

    resp = client.get(f"/foundation-baselines/{UNKNOWN_ID}/compare/{baseline_id}")
    assert resp.status_code == 404
