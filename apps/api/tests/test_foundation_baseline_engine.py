"""RFC-0022 (Foundation Intelligence Slice 5: Foundation Baseline,
AOS-FOUNDATION-BASELINE-MODELS-001) — ``services/foundation_baseline.py`` over
the Slice 1-4 pipeline (evidence -> genome -> requirements -> candidates ->
eligibility -> score -> council review -> selection), on the hermetic
``DeterministicProvider`` (no network/LLM).

Hermetic: the ``db_session`` fixture (``conftest.py``) creates every table via
sqlite ``Base.metadata.create_all`` (LES-L10: imports ``aos_core.models``
before ``create_all``).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from aos_core.foundation.enums import BaselineStatus, CandidateStatus, SelectionRunState
from aos_core.foundation.serialization import set_hash
from aos_core.llm import DeterministicProvider
from aos_core.models import (
    ApprovalRecord,
    Decision,
    FoundationBaseline,
    FoundationBaselineElement,
    FoundationElement,
    FoundationObjection,
    FoundationSelectionRun,
    ImmutableContentError,
    Project,
    Repository,
    RepositoryDNA,
    ValidationTask,
)
from aos_core.services.decisions import DECISION_APPROVED
from aos_core.services.evidence import create_claim
from aos_core.services.foundation import (
    compile_requirements,
    evaluate_eligibility,
    generate_candidates,
    open_selection_run,
    score_candidate,
)
from aos_core.services.foundation_baseline import (
    _baseline_hash,
    _element_content_hash,
    compare_baselines,
    mint_baseline,
    supersede_baseline,
)
from aos_core.services.foundation_council import (
    record_validation_result,
    resolve_objection,
    review_candidate,
    select_candidate,
)
from aos_core.services.genome import generate_genome

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Fixture builders — mirrors test_foundation_council_engine.py's
# _rich_reviewable_run recipe, extended to walk a candidate all the way to
# CandidateStatus.SELECTED / SelectionRunState.SELECTED (Slice 4's own human
# gate), which is this slice's starting point.
# ---------------------------------------------------------------------------


def _project_with_evidence(db, slug: str) -> Project:
    """A project with a hard-constraint claim, a runtime fact, and a repository
    risk flag — drives compiled requirements, both candidate templates, and a
    council concern (RFC-0021's fixture recipe)."""
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
    # RFC-0022 versioning test fallback: open_selection_run's one-active-run-
    # per-project gate treats a BASELINED run as still "active" (only
    # blocked/cancelled/superseded are terminal there), so a project cannot
    # open a second run through the service once its first is baselined. A
    # second run for the SAME project is therefore built directly at the ORM
    # layer here, exactly as the RFC anticipates ("mint two baselines via a
    # lower-level path" if the one-active-run constraint blocks the service
    # path) — every downstream engine call (compile/generate/evaluate/score/
    # review/select) only takes a run_id and has no project-uniqueness check
    # of its own.
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
# mint_baseline — happy path
# ---------------------------------------------------------------------------


def test_mint_baseline_happy_path(db_session):
    project = _project_with_evidence(db_session, "baseline-happy")
    run = _open_run(db_session, project)
    candidate, run = _drive_to_selected(db_session, run)
    assert candidate.status == CandidateStatus.SELECTED.value
    assert run.state == SelectionRunState.SELECTED.value

    elements = db_session.query(FoundationElement).filter(FoundationElement.candidate_id == candidate.id).all()
    assert elements, "the selected candidate must have at least one element to freeze"

    baseline = mint_baseline(db_session, selection_run_id=run.id, approver="ops@example.com")

    assert isinstance(baseline, FoundationBaseline)
    assert baseline.status == BaselineStatus.ACTIVE.value
    assert baseline.baseline_version == "1.0"
    assert baseline.candidate_id == candidate.id
    assert baseline.selection_run_id == run.id
    assert baseline.target_genome_snapshot_id == run.target_genome_snapshot_id
    assert baseline.supersedes_baseline_id is None

    db_session.refresh(run)
    assert run.state == SelectionRunState.BASELINED.value

    decision = db_session.get(Decision, baseline.approved_decision_id)
    assert decision is not None
    assert decision.status == DECISION_APPROVED
    assert decision.approved_by == "ops@example.com"
    assert baseline.approved_decision_id == decision.id

    approvals = db_session.query(ApprovalRecord).filter(ApprovalRecord.target == baseline.id).all()
    assert approvals and approvals[-1].approval_status == "approved"
    assert approvals[-1].actor == "ops@example.com"

    baseline_elements = (
        db_session.query(FoundationBaselineElement)
        .filter(FoundationBaselineElement.baseline_id == baseline.id)
        .all()
    )
    assert len(baseline_elements) == len(elements)
    assert {e.source_element_id for e in baseline_elements} == {e.id for e in elements}

    assert baseline.element_set_hash
    assert baseline.baseline_hash

    # Reproducibility: recompute both hashes from the frozen constituents via
    # the same helpers the engine uses — must match exactly (C4).
    recomputed_element_hashes = [_element_content_hash(el) for el in elements]
    recomputed_element_set_hash = set_hash(recomputed_element_hashes)
    assert recomputed_element_set_hash == baseline.element_set_hash

    recomputed_baseline_hash = _baseline_hash(
        target_genome_snapshot_id=baseline.target_genome_snapshot_id,
        corpus_snapshot_id=baseline.corpus_snapshot_id,
        approved_decision_id=baseline.approved_decision_id,
        candidate_id=baseline.candidate_id,
        element_set_hash=baseline.element_set_hash,
        baseline_version=baseline.baseline_version,
        review_triggers=baseline.review_triggers,
    )
    assert recomputed_baseline_hash == baseline.baseline_hash


# ---------------------------------------------------------------------------
# C4 — immutability
# ---------------------------------------------------------------------------


def test_c4_baseline_content_mutation_is_refused(db_session):
    project = _project_with_evidence(db_session, "baseline-c4-baseline")
    run = _open_run(db_session, project)
    _candidate, run = _drive_to_selected(db_session, run)
    baseline = mint_baseline(db_session, selection_run_id=run.id, approver="ops@example.com")

    baseline.baseline_hash = "tampered"
    with pytest.raises(ImmutableContentError):
        db_session.commit()
    db_session.rollback()

    reloaded = db_session.get(FoundationBaseline, baseline.id)
    assert reloaded.baseline_hash != "tampered"


def test_c4_baseline_element_content_mutation_is_refused(db_session):
    project = _project_with_evidence(db_session, "baseline-c4-element")
    run = _open_run(db_session, project)
    _candidate, run = _drive_to_selected(db_session, run)
    baseline = mint_baseline(db_session, selection_run_id=run.id, approver="ops@example.com")

    element = (
        db_session.query(FoundationBaselineElement)
        .filter(FoundationBaselineElement.baseline_id == baseline.id)
        .first()
    )
    original_hash = element.content_hash
    element.content_hash = "tampered"
    with pytest.raises(ImmutableContentError):
        db_session.commit()
    db_session.rollback()

    reloaded = db_session.get(FoundationBaselineElement, element.id)
    assert reloaded.content_hash == original_hash


def test_c4_status_transition_still_works(db_session):
    """The one mutable field (C4/AD-12): a status transition must NOT raise."""
    project = _project_with_evidence(db_session, "baseline-c4-status")
    run = _open_run(db_session, project)
    _candidate, run = _drive_to_selected(db_session, run)
    baseline = mint_baseline(db_session, selection_run_id=run.id, approver="ops@example.com")

    superseded = supersede_baseline(db_session, baseline_id=baseline.id, actor="ops@example.com")
    assert superseded.status == BaselineStatus.SUPERSEDED.value

    reloaded = db_session.get(FoundationBaseline, baseline.id)
    assert reloaded.status == BaselineStatus.SUPERSEDED.value


# ---------------------------------------------------------------------------
# mint_baseline — gate
# ---------------------------------------------------------------------------


def test_mint_baseline_404_missing_run(db_session):
    with pytest.raises(HTTPException) as exc:
        mint_baseline(db_session, selection_run_id=UNKNOWN_ID, approver="ops@example.com")
    assert exc.value.status_code == 404


def test_mint_baseline_409_run_not_selected(db_session):
    project = _project_with_evidence(db_session, "baseline-gate-run-state")
    run = _open_run(db_session, project)  # still 'draft'
    with pytest.raises(HTTPException) as exc:
        mint_baseline(db_session, selection_run_id=run.id, approver="ops@example.com")
    assert exc.value.status_code == 409


def test_mint_baseline_409_no_selected_candidate(db_session):
    project = _project_with_evidence(db_session, "baseline-gate-no-candidate")
    run = _open_run(db_session, project)
    # Force the run into 'selected' directly (no candidate ever reaches
    # CandidateStatus.SELECTED) to isolate this 409 from the run-state 409.
    run.state = SelectionRunState.SELECTED.value
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        mint_baseline(db_session, selection_run_id=run.id, approver="ops@example.com")
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# mint_baseline — versioning
# ---------------------------------------------------------------------------


def test_mint_baseline_versioning_supersedes_prior(db_session):
    project = _project_with_evidence(db_session, "baseline-versioning")

    run1 = _open_run(db_session, project)
    _candidate1, run1 = _drive_to_selected(db_session, run1)
    baseline1 = mint_baseline(db_session, selection_run_id=run1.id, approver="ops@example.com")
    assert baseline1.baseline_version == "1.0"
    assert baseline1.status == BaselineStatus.ACTIVE.value

    run2 = _open_run(db_session, project, via_service=False)
    _candidate2, run2 = _drive_to_selected(db_session, run2)
    baseline2 = mint_baseline(db_session, selection_run_id=run2.id, approver="ops@example.com")

    assert baseline2.baseline_version == "2.0"
    assert baseline2.supersedes_baseline_id == baseline1.id
    assert baseline2.status == BaselineStatus.ACTIVE.value

    db_session.refresh(baseline1)
    assert baseline1.status == BaselineStatus.SUPERSEDED.value

    diff = compare_baselines(db_session, base_id=baseline1.id, other_id=baseline2.id)
    assert diff["hash_equal"] is False


# ---------------------------------------------------------------------------
# compare_baselines
# ---------------------------------------------------------------------------


def test_compare_baselines_identity_is_empty_diff(db_session):
    project = _project_with_evidence(db_session, "baseline-compare-identity")
    run = _open_run(db_session, project)
    _candidate, run = _drive_to_selected(db_session, run)
    baseline = mint_baseline(db_session, selection_run_id=run.id, approver="ops@example.com")

    diff = compare_baselines(db_session, base_id=baseline.id, other_id=baseline.id)

    assert diff["base_id"] == baseline.id
    assert diff["other_id"] == baseline.id
    assert diff["hash_equal"] is True
    assert diff["elements_added"] == []
    assert diff["elements_removed"] == []
    assert diff["elements_changed"] == []
    assert diff["genome_changed"] is False
    assert diff["review_triggers_added"] == []
    assert diff["review_triggers_removed"] == []


def test_compare_baselines_404_missing_baseline(db_session):
    project = _project_with_evidence(db_session, "baseline-compare-404")
    run = _open_run(db_session, project)
    _candidate, run = _drive_to_selected(db_session, run)
    baseline = mint_baseline(db_session, selection_run_id=run.id, approver="ops@example.com")

    with pytest.raises(HTTPException) as exc:
        compare_baselines(db_session, base_id=UNKNOWN_ID, other_id=baseline.id)
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        compare_baselines(db_session, base_id=baseline.id, other_id=UNKNOWN_ID)
    assert exc.value.status_code == 404


def test_compare_baselines_added_removed_changed_and_genome_delta(db_session):
    """A hand-built second baseline (sharing one element whose content changed,
    dropping one, adding one, and pointing at a different genome snapshot)
    exercises the full diff shape independent of the mint pipeline."""
    project = _project_with_evidence(db_session, "baseline-compare-diff")
    run = _open_run(db_session, project)
    _candidate, run = _drive_to_selected(db_session, run)
    baseline = mint_baseline(
        db_session, selection_run_id=run.id, approver="ops@example.com", review_triggers=["manual_review"]
    )

    base_elements = (
        db_session.query(FoundationBaselineElement)
        .filter(FoundationBaselineElement.baseline_id == baseline.id)
        .all()
    )
    assert base_elements
    shared = base_elements[0]

    other_genome_id = "00000000-0000-0000-0000-0000000000aa"
    new_element_source_id = "00000000-0000-0000-0000-0000000000bb"

    other_baseline = FoundationBaseline(
        status=BaselineStatus.ACTIVE.value,
        project_id=baseline.project_id,
        candidate_id=baseline.candidate_id,
        selection_run_id=baseline.selection_run_id,
        target_genome_snapshot_id=other_genome_id,
        corpus_snapshot_id=baseline.corpus_snapshot_id,
        approved_decision_id=baseline.approved_decision_id,
        baseline_version="9.0",
        element_set_hash="other-element-set-hash",
        baseline_hash="other-baseline-hash",
        review_triggers=["drift_detected"],
        minted_by="approval_process",
        approved_by="ops@example.com",
        created_by="ops@example.com",
        updated_by="ops@example.com",
    )
    db_session.add(other_baseline)
    db_session.flush()
    db_session.add_all(
        [
            FoundationBaselineElement(
                baseline_id=other_baseline.id,
                source_element_id=shared.source_element_id,
                domain=shared.domain,
                title="Changed title",
                decision="Changed decision",
                verification_method="n/a",
                content_hash="changed-content-hash",
                created_by="ops@example.com",
                updated_by="ops@example.com",
            ),
            FoundationBaselineElement(
                baseline_id=other_baseline.id,
                source_element_id=new_element_source_id,
                domain="deployment",
                title="A brand-new element",
                decision="New decision",
                verification_method="n/a",
                content_hash="new-content-hash",
                created_by="ops@example.com",
                updated_by="ops@example.com",
            ),
        ]
    )
    db_session.commit()

    diff = compare_baselines(db_session, base_id=baseline.id, other_id=other_baseline.id)

    assert diff["hash_equal"] is False
    assert diff["genome_changed"] is True
    assert diff["genome"] == {"base": baseline.target_genome_snapshot_id, "other": other_genome_id}

    added_ids = {e["source_element_id"] for e in diff["elements_added"]}
    assert added_ids == {new_element_source_id}

    removed_ids = {e["source_element_id"] for e in diff["elements_removed"]}
    assert removed_ids == {e.source_element_id for e in base_elements if e.source_element_id != shared.source_element_id}

    changed = diff["elements_changed"]
    assert len(changed) == 1
    assert changed[0]["source_element_id"] == shared.source_element_id
    assert changed[0]["base_content_hash"] == shared.content_hash
    assert changed[0]["other_content_hash"] == "changed-content-hash"

    assert diff["review_triggers_added"] == ["drift_detected"]
    assert diff["review_triggers_removed"] == ["manual_review"]
