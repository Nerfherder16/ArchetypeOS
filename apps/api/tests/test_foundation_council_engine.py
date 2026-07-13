"""RFC-0021 (Foundation Intelligence Slice 4: Council & Validation,
AOS-COUNCIL-VALIDATION-MODELS-001) — ``services/foundation_council.py`` over the
Slice 1/2/3 pipeline (evidence -> genome -> requirements -> candidates ->
eligibility -> score), on the hermetic ``DeterministicProvider`` (no network/LLM
— CI runs this exact path, design §20 steps 12-15).

Hermetic: the ``db_session`` fixture (``conftest.py``) creates every table via
sqlite ``Base.metadata.create_all`` (LES-L10: imports ``aos_core.models`` before
``create_all``).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from aos_core.foundation.enums import CandidateStatus, SelectionRunState, ValidationStatus
from aos_core.llm import DeterministicProvider
from aos_core.models import (
    ApprovalRecord,
    CouncilReview,
    FoundationCandidate,
    FoundationObjection,
    Project,
    Repository,
    RepositoryDNA,
    ValidationResult,
    ValidationTask,
)
from aos_core.services.evidence import create_claim
from aos_core.services.foundation import (
    IllegalTransition,
    compile_requirements,
    evaluate_eligibility,
    generate_candidates,
    open_selection_run,
    score_candidate,
)
from aos_core.services.foundation_council import (
    record_validation_result,
    resolve_objection,
    review_candidate,
    select_candidate,
    synthesize_dossier,
)
from aos_core.services.genome import generate_genome


def _rich_reviewable_run(db, slug: str):
    """A project with a hard-constraint claim (drives a compiled requirement +
    both candidate templates), a runtime fact (drives a required_capability
    requirement), and a repository with a risk flag (drives a council concern
    for the security agent) but NO decisions/research notes (the research
    librarian's evidence selector sees nothing -> ``status='Needs Evidence'``,
    RFC-0021 Open Q1b's required-validation signal). Returns ``(project, run,
    candidates)`` with every eligible candidate already scored."""
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


# --- review_candidate --------------------------------------------------------


def test_review_candidate_attaches_typed_review_and_derives_objections_and_tasks(db_session):
    _project, run, candidates = _rich_reviewable_run(db_session, "council-review")
    candidate = candidates[0]
    assert candidate.status == CandidateStatus.ELIGIBLE.value

    review = review_candidate(db_session, candidate_id=candidate.id, provider=DeterministicProvider())

    assert isinstance(review, CouncilReview)
    assert review.candidate_id == candidate.id
    assert review.selection_run_id == run.id
    assert len(review.agent_outputs) == 4

    db_session.refresh(candidate)
    assert candidate.status == CandidateStatus.CHALLENGED.value, "review_candidate moves eligible -> challenged"

    objections = (
        db_session.query(FoundationObjection).filter(FoundationObjection.candidate_id == candidate.id).all()
    )
    assert objections, "the security risk flag concern must derive at least one objection"
    assert any(o.blocking and o.status == "open" for o in objections)
    assert all(o.review_id == review.id for o in objections)

    tasks = db_session.query(ValidationTask).filter(ValidationTask.candidate_id == candidate.id).all()
    assert tasks, "thin evidence and/or the abstained research librarian must derive a validation task"
    assert any(t.blocking and t.status == ValidationStatus.PROPOSED.value for t in tasks)
    assert all(t.selection_run_id == run.id for t in tasks)

    db_session.refresh(run)
    assert run.state in (SelectionRunState.COUNCIL_REVIEW.value, SelectionRunState.VALIDATION_REQUIRED.value)


def test_review_candidate_missing_candidate_404s(db_session):
    with pytest.raises(HTTPException) as exc:
        review_candidate(db_session, candidate_id="00000000-0000-0000-0000-000000000000", provider=DeterministicProvider())
    assert exc.value.status_code == 404


# --- the full design §20 steps 12-15 walkthrough ------------------------------


def test_full_walkthrough_objection_then_validation_then_selection(db_session):
    """design §20 steps 12-15: specialist reviews produce objections; a failed
    blocking validation marks the candidate ``challenged`` (not rejected) and
    blocks selection; re-validating clears it; a human then selects — and only
    after every gate is clear. Also proves AD-9 (the dossier recommends, never
    selects) and walks the run lifecycle
    council_review -> validation_required -> validation_complete ->
    ready_for_selection -> selected end to end.
    """
    _project, run, candidates = _rich_reviewable_run(db_session, "council-walkthrough")
    candidate = candidates[0]

    review_candidate(db_session, candidate_id=candidate.id, provider=DeterministicProvider())
    db_session.refresh(candidate)
    db_session.refresh(run)
    assert candidate.status == CandidateStatus.CHALLENGED.value
    assert run.state == SelectionRunState.VALIDATION_REQUIRED.value, (
        "a blocking validation task was derived, so the run must reach validation_required"
    )

    blocking_objections = (
        db_session.query(FoundationObjection)
        .filter(
            FoundationObjection.candidate_id == candidate.id,
            FoundationObjection.blocking.is_(True),
            FoundationObjection.status == "open",
        )
        .all()
    )
    assert blocking_objections

    blocking_tasks = (
        db_session.query(ValidationTask)
        .filter(ValidationTask.candidate_id == candidate.id, ValidationTask.blocking.is_(True))
        .all()
    )
    assert blocking_tasks

    # Step 1: an unresolved blocking objection alone blocks selection.
    with pytest.raises(HTTPException) as exc:
        select_candidate(db_session, selection_run_id=run.id, candidate_id=candidate.id, approver="ops@example.com")
    assert exc.value.status_code == 409

    for objection in blocking_objections:
        resolved = resolve_objection(
            db_session, objection_id=objection.id, status="accepted_exception",
            resolution="Reviewed and accepted as a known, tracked risk.",
        )
        assert resolved.status == "accepted_exception"

    # Step 2: objections cleared, but the blocking validation is still open -> still blocked.
    with pytest.raises(HTTPException) as exc:
        select_candidate(db_session, selection_run_id=run.id, candidate_id=candidate.id, approver="ops@example.com")
    assert exc.value.status_code == 409

    # Step 3: a FAILED blocking validation marks the candidate 'challenged', not 'rejected' (recoverable).
    first_task = blocking_tasks[0]
    failed_result = record_validation_result(
        db_session, validation_task_id=first_task.id, outcome="failed", summary="Evidence still too thin.",
    )
    assert isinstance(failed_result, ValidationResult)
    assert failed_result.outcome == "failed"
    db_session.refresh(candidate)
    assert candidate.status == CandidateStatus.CHALLENGED.value
    assert candidate.status != CandidateStatus.REJECTED.value

    with pytest.raises(HTTPException) as exc:
        select_candidate(db_session, selection_run_id=run.id, candidate_id=candidate.id, approver="ops@example.com")
    assert exc.value.status_code == 409

    # Step 4: re-validate every blocking task to 'passed' -> run reaches validation_complete.
    for task in blocking_tasks:
        record_validation_result(db_session, validation_task_id=task.id, outcome="passed", summary="Cleared with additional evidence.")
    db_session.refresh(run)
    assert run.state == SelectionRunState.VALIDATION_COMPLETE.value
    for task in blocking_tasks:
        db_session.refresh(task)
        assert task.status == ValidationStatus.PASSED.value

    # Step 5: the Final Judge dossier recommends — it never selects (AD-9).
    dossier = synthesize_dossier(db_session, selection_run_id=run.id)
    assert dossier.recommended_candidate_id == candidate.id
    assert dossier.verdict == "Recommended"
    db_session.refresh(run)
    assert run.state == SelectionRunState.READY_FOR_SELECTION.value
    assert (
        db_session.query(FoundationCandidate)
        .filter(FoundationCandidate.status == CandidateStatus.SELECTED.value)
        .count()
        == 0
    ), "synthesize_dossier must never set a candidate to selected"

    # Step 6: the human gate — now everything is clear, selection succeeds.
    selected = select_candidate(db_session, selection_run_id=run.id, candidate_id=candidate.id, approver="ops@example.com")
    assert selected.status == CandidateStatus.SELECTED.value
    db_session.refresh(run)
    assert run.state == SelectionRunState.SELECTED.value

    approvals = db_session.query(ApprovalRecord).filter(ApprovalRecord.target == candidate.id).all()
    assert approvals and approvals[-1].approval_status == "approved"
    assert approvals[-1].actor == "ops@example.com"

    db_session.refresh(dossier)
    assert dossier.approved_by == "ops@example.com"
    assert dossier.approved_at is not None


# --- select_candidate gate edge cases -----------------------------------------


def test_select_candidate_409_without_any_review(db_session):
    _project, run, candidates = _rich_reviewable_run(db_session, "council-unreviewed")
    candidate = candidates[0]
    with pytest.raises(HTTPException) as exc:
        select_candidate(db_session, selection_run_id=run.id, candidate_id=candidate.id, approver="ops@example.com")
    assert exc.value.status_code == 409


def test_select_candidate_404_missing_run_or_candidate(db_session):
    _project, run, candidates = _rich_reviewable_run(db_session, "council-404s")
    candidate = candidates[0]
    with pytest.raises(HTTPException) as exc:
        select_candidate(
            db_session, selection_run_id="00000000-0000-0000-0000-000000000000", candidate_id=candidate.id,
            approver="ops@example.com",
        )
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        select_candidate(
            db_session, selection_run_id=run.id, candidate_id="00000000-0000-0000-0000-000000000000",
            approver="ops@example.com",
        )
    assert exc.value.status_code == 404


# --- resolve_objection ---------------------------------------------------------


def test_resolve_objection_requires_open_status(db_session):
    _project, run, candidates = _rich_reviewable_run(db_session, "council-obj-status")
    candidate = candidates[0]
    review_candidate(db_session, candidate_id=candidate.id, provider=DeterministicProvider())
    objection = (
        db_session.query(FoundationObjection).filter(FoundationObjection.candidate_id == candidate.id).first()
    )
    resolve_objection(db_session, objection_id=objection.id, status="resolved", resolution="Fixed.")

    with pytest.raises(HTTPException) as exc:
        resolve_objection(db_session, objection_id=objection.id, status="accepted_exception")
    assert exc.value.status_code == 409


def test_resolve_objection_illegal_status_raises(db_session):
    _project, run, candidates = _rich_reviewable_run(db_session, "council-obj-illegal")
    candidate = candidates[0]
    review_candidate(db_session, candidate_id=candidate.id, provider=DeterministicProvider())
    objection = (
        db_session.query(FoundationObjection).filter(FoundationObjection.candidate_id == candidate.id).first()
    )
    with pytest.raises(IllegalTransition):
        resolve_objection(db_session, objection_id=objection.id, status="bogus_status")


def test_resolve_objection_converted_to_validation_creates_and_links_task(db_session):
    _project, run, candidates = _rich_reviewable_run(db_session, "council-obj-convert")
    candidate = candidates[0]
    review_candidate(db_session, candidate_id=candidate.id, provider=DeterministicProvider())
    objection = (
        db_session.query(FoundationObjection)
        .filter(FoundationObjection.candidate_id == candidate.id, FoundationObjection.blocking.is_(True))
        .first()
    )
    before_task_count = db_session.query(ValidationTask).count()

    resolved = resolve_objection(db_session, objection_id=objection.id, status="converted_to_validation")

    assert resolved.status == "converted_to_validation"
    assert resolved.resolution_validation_task_id is not None
    assert db_session.query(ValidationTask).count() == before_task_count + 1
    linked_task = db_session.get(ValidationTask, resolved.resolution_validation_task_id)
    assert linked_task is not None
    assert linked_task.candidate_id == candidate.id
    assert linked_task.blocking == objection.blocking


# --- record_validation_result ---------------------------------------------------


def test_record_validation_result_illegal_outcome_raises(db_session):
    _project, run, candidates = _rich_reviewable_run(db_session, "council-result-illegal")
    candidate = candidates[0]
    review_candidate(db_session, candidate_id=candidate.id, provider=DeterministicProvider())
    task = db_session.query(ValidationTask).filter(ValidationTask.candidate_id == candidate.id).first()
    with pytest.raises(IllegalTransition):
        record_validation_result(db_session, validation_task_id=task.id, outcome="maybe")


def test_record_validation_result_404_missing_task(db_session):
    with pytest.raises(HTTPException) as exc:
        record_validation_result(db_session, validation_task_id="00000000-0000-0000-0000-000000000000", outcome="passed")
    assert exc.value.status_code == 404


# --- C2 reuse-link round-trips --------------------------------------------------


def test_validation_result_c2_reuse_links_round_trip(db_session):
    _project, run, candidates = _rich_reviewable_run(db_session, "council-c2-result")
    candidate = candidates[0]
    review_candidate(db_session, candidate_id=candidate.id, provider=DeterministicProvider())
    task = db_session.query(ValidationTask).filter(ValidationTask.candidate_id == candidate.id).first()

    result = record_validation_result(
        db_session, validation_task_id=task.id, outcome="passed", summary="Backed by a real benchmark run.",
        benchmark_ref="bench-1234", experiment_ref="exp-5678",
    )

    db_session.refresh(result)
    assert result.benchmark_ref == "bench-1234"
    assert result.experiment_ref == "exp-5678"
    persisted = db_session.get(ValidationResult, result.id)
    assert persisted.benchmark_ref == "bench-1234"
    assert persisted.experiment_ref == "exp-5678"


# --- run lifecycle -----------------------------------------------------------


def test_run_lifecycle_illegal_transition_raises(db_session):
    from aos_core.foundation.lifecycle import LifecycleKind, can_transition
    from aos_core.services.foundation import _advance_run

    # eligibility_review -> selected is not a legal single hop.
    assert not can_transition(
        LifecycleKind.SELECTION_RUN, SelectionRunState.ELIGIBILITY_REVIEW.value, SelectionRunState.SELECTED.value
    )

    _project, run, candidates = _rich_reviewable_run(db_session, "council-run-illegal")
    candidate = candidates[0]
    review_candidate(db_session, candidate_id=candidate.id, provider=DeterministicProvider())
    db_session.refresh(run)
    assert run.state in (SelectionRunState.COUNCIL_REVIEW.value, SelectionRunState.VALIDATION_REQUIRED.value)

    # A *backward* target (behind the run's current forward-chain position) has
    # no legal forward path at all — _advance_run's walk can only go forward.
    with pytest.raises(IllegalTransition):
        _advance_run(run, SelectionRunState.DRAFT, actor="test")
