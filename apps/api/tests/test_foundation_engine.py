"""RFC-0020 (Foundation Intelligence Slice 3, AOS-FOUNDATION-MODELS-001) —
``services/foundation.py`` over a genome + claims fixture.

Hermetic: the ``db_session`` fixture (``conftest.py``) creates every table via
sqlite ``Base.metadata.create_all``. Claims are created through
``services/evidence.py`` and the genome through ``services/genome.py``,
mirroring ``test_genome_generate.py``'s fixture style (LES-L10: import
``aos_core.models`` before ``create_all``, handled by the fixture itself).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from aos_core.foundation.enums import CandidateStatus, FoundationDomain, RequirementType, SelectionRunState
from aos_core.models import (
    Evaluation,
    FoundationElement,
    FoundationRequirement,
    FoundationScore,
    Project,
    Recommendation,
)
from aos_core.services.evidence import create_claim
from aos_core.services.foundation import (
    IllegalTransition,
    _advance_run,
    _set_candidate_status,
    add_element,
    compile_requirements,
    create_candidate,
    evaluate_eligibility,
    generate_candidates,
    open_selection_run,
    score_candidate,
)
from aos_core.services.genome import generate_genome


def _project(db, slug: str) -> Project:
    project = Project(name=slug, slug=slug)
    db.add(project)
    db.commit()
    return project


def _observed(db, project, *, statement: str, domain: str, confidence: float = 0.9) -> str:
    claim = create_claim(
        db, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement=statement, claim_type="fact", domain=domain, created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []}, confidence=confidence,
    )
    return claim.id


def _claimed(db, project, *, statement: str, domain: str, claim_type: str, confidence: float = 0.9) -> str:
    claim = create_claim(
        db, project_id=project.id, minted_by="human", truth_layer="claimed",
        statement=statement, claim_type=claim_type, domain=domain, created_by="product manager",
        derivation={"method": "direct", "parent_claim_ids": []}, confidence=confidence,
    )
    return claim.id


def _setup_run_with_hard_constraint(db, slug: str):
    """A project with a runtime observed fact (fires a foundation-shaping
    required_capability trait) + a deployment 'constraint' claim (fires a
    hard_constraint). Returns ``(project, run, constraint_claim_id)`` with
    requirements already compiled (``run.state == requirements_compiled``)."""
    project = _project(db, slug)
    _observed(db, project, statement="A worker process pulls jobs from a message queue.", domain="runtime")
    constraint_id = _claimed(
        db, project, statement="The deployment environment must not use a public cloud provider.",
        domain="deployment", claim_type="constraint",
    )
    genome = generate_genome(db, project_id=project.id, state_view="current")
    run = open_selection_run(db, project_id=project.id, target_genome_snapshot_id=genome.id)
    compile_requirements(db, selection_run_id=run.id)
    return project, run, constraint_id


# --- requirement compilation --------------------------------------------------


def test_compile_requirements_hard_constraint_has_source_claim_and_verification_method(db_session):
    project, run, constraint_id = _setup_run_with_hard_constraint(db_session, "found-compile")
    assert run.state == SelectionRunState.REQUIREMENTS_COMPILED.value

    requirements = db_session.query(FoundationRequirement).filter(
        FoundationRequirement.selection_run_id == run.id
    ).all()

    hard = [r for r in requirements if r.requirement_type == RequirementType.HARD_CONSTRAINT.value]
    assert len(hard) == 1
    assert hard[0].domain == FoundationDomain.DEPLOYMENT.value
    assert hard[0].veto_if_unsatisfied is True
    assert constraint_id in hard[0].claim_ids
    assert hard[0].verification_method

    capabilities = [r for r in requirements if r.requirement_type == RequirementType.REQUIRED_CAPABILITY.value]
    assert any(r.domain == FoundationDomain.RUNTIME.value for r in capabilities)


def test_compile_requirements_preference_claim_becomes_preference_requirement(db_session):
    project = _project(db_session, "found-preference")
    _observed(db_session, project, statement="A worker process pulls jobs from a message queue.", domain="runtime")
    preference_id = _claimed(
        db_session, project, statement="We would prefer to use PostgreSQL for storage.",
        domain="data", claim_type="preference",
    )
    genome = generate_genome(db_session, project_id=project.id, state_view="current")
    run = open_selection_run(db_session, project_id=project.id, target_genome_snapshot_id=genome.id)
    requirements = compile_requirements(db_session, selection_run_id=run.id)

    preferences = [r for r in requirements if r.requirement_type == RequirementType.PREFERENCE.value]
    assert len(preferences) == 1
    assert preference_id in preferences[0].claim_ids
    assert preferences[0].veto_if_unsatisfied is False


# --- candidate generation ------------------------------------------------------


def test_generate_candidates_yields_distinct_candidates_addressing_hard_constraint(db_session):
    project, run, _constraint_id = _setup_run_with_hard_constraint(db_session, "found-candidates")

    candidates = generate_candidates(db_session, selection_run_id=run.id)
    db_session.refresh(run)
    assert run.state == SelectionRunState.CANDIDATES_GENERATED.value
    assert len(candidates) >= 2
    names = {c.name for c in candidates}
    assert len(names) == len(candidates)  # genuinely distinct, not cosmetic dupes

    hard_constraint = (
        db_session.query(FoundationRequirement)
        .filter(
            FoundationRequirement.selection_run_id == run.id,
            FoundationRequirement.requirement_type == RequirementType.HARD_CONSTRAINT.value,
        )
        .one()
    )

    for candidate in candidates:
        elements = db_session.query(FoundationElement).filter(FoundationElement.candidate_id == candidate.id).all()
        assert elements, f"candidate {candidate.name} has no elements"
        assert any(hard_constraint.id in (el.requirement_ids or []) for el in elements), (
            f"candidate {candidate.name} does not address the hard constraint"
        )


# --- AD-8: eligibility before scoring ------------------------------------------


def test_evaluate_eligibility_rejects_violator_before_scoring_and_score_refuses_it(db_session):
    project, run, _constraint_id = _setup_run_with_hard_constraint(db_session, "found-eligibility")
    candidates = generate_candidates(db_session, selection_run_id=run.id)

    violator = create_candidate(db_session, selection_run_id=run.id, name="Cloud-Violating Alternative")
    add_element(
        db_session,
        candidate_id=violator.id,
        domain=FoundationDomain.DEPLOYMENT,
        title="Deployment approach (violating)",
        decision="Deploy directly to a public cloud provider using managed Kubernetes for elasticity.",
        verification_method="none",
    )

    hard_constraint = (
        db_session.query(FoundationRequirement)
        .filter(
            FoundationRequirement.selection_run_id == run.id,
            FoundationRequirement.requirement_type == RequirementType.HARD_CONSTRAINT.value,
        )
        .one()
    )

    reviewed = evaluate_eligibility(db_session, selection_run_id=run.id)
    db_session.refresh(run)
    assert run.state == SelectionRunState.ELIGIBILITY_REVIEW.value

    by_id = {c.id: c for c in reviewed}
    assert by_id[violator.id].status == CandidateStatus.REJECTED.value
    assert hard_constraint.id in by_id[violator.id].hard_constraint_violations

    for candidate in candidates:
        assert by_id[candidate.id].status == CandidateStatus.ELIGIBLE.value
        assert by_id[candidate.id].hard_constraint_violations == []

    # AD-8 — score_candidate refuses the rejected candidate; NO score rows written.
    with pytest.raises(HTTPException) as exc_info:
        score_candidate(db_session, candidate_id=violator.id)
    assert exc_info.value.status_code == 409
    assert db_session.query(FoundationScore).filter(FoundationScore.candidate_id == violator.id).count() == 0

    # An eligible candidate scores fine, producing a per-criterion vector.
    scored = score_candidate(db_session, candidate_id=candidates[0].id)
    assert scored.score_summary["vector_shape"] == "per_criterion"
    assert scored.score_summary["criteria"]
    for entry in scored.score_summary["criteria"]:
        assert "adjusted_score" in entry
        assert "uncertainty_penalty" in entry


# --- score vectors + LES-023 coverage-honest uncertainty -----------------------


def test_score_candidate_uncertainty_penalty_grows_with_evidence_thinness(db_session):
    project = _project(db_session, "found-scoring")
    fact_claim_ids = [
        _observed(db_session, project, statement=f"Observed fact {i} about the runtime.", domain="runtime")
        for i in range(3)
    ]
    genome = generate_genome(db_session, project_id=project.id, state_view="current")
    run = open_selection_run(db_session, project_id=project.id, target_genome_snapshot_id=genome.id)
    compile_requirements(db_session, selection_run_id=run.id)

    dense = create_candidate(db_session, selection_run_id=run.id, name="Dense")
    add_element(
        db_session, candidate_id=dense.id, domain=FoundationDomain.RUNTIME, title="Runtime (dense)",
        decision="Adopt a well-evidenced runtime approach.", verification_method="review",
        claim_ids=fact_claim_ids,
    )

    sparse = create_candidate(db_session, selection_run_id=run.id, name="Sparse")
    add_element(
        db_session, candidate_id=sparse.id, domain=FoundationDomain.RUNTIME, title="Runtime (sparse)",
        decision="Adopt an unevidenced runtime approach.", verification_method="review",
        claim_ids=[],
    )

    evaluate_eligibility(db_session, selection_run_id=run.id)

    dense_scored = score_candidate(db_session, candidate_id=dense.id)
    sparse_scored = score_candidate(db_session, candidate_id=sparse.id)

    dense_penalties = {e["criterion"]: e["uncertainty_penalty"] for e in dense_scored.score_summary["criteria"]}
    sparse_penalties = {e["criterion"]: e["uncertainty_penalty"] for e in sparse_scored.score_summary["criteria"]}
    assert dense_penalties  # non-empty vector
    for criterion, dense_penalty in dense_penalties.items():
        assert sparse_penalties[criterion] > dense_penalty
    dense_confidences = {e["criterion"]: e["confidence"] for e in dense_scored.score_summary["criteria"]}
    sparse_confidences = {e["criterion"]: e["confidence"] for e in sparse_scored.score_summary["criteria"]}
    for criterion, dense_confidence in dense_confidences.items():
        assert sparse_confidences[criterion] < dense_confidence


# --- selection-run lifecycle + illegal transitions -----------------------------


def test_selection_run_lifecycle_advances_through_the_milestones(db_session):
    project, run, _constraint_id = _setup_run_with_hard_constraint(db_session, "found-lifecycle")
    assert run.state == SelectionRunState.REQUIREMENTS_COMPILED.value

    generate_candidates(db_session, selection_run_id=run.id)
    db_session.refresh(run)
    assert run.state == SelectionRunState.CANDIDATES_GENERATED.value

    evaluate_eligibility(db_session, selection_run_id=run.id)
    db_session.refresh(run)
    assert run.state == SelectionRunState.ELIGIBILITY_REVIEW.value


def test_open_selection_run_rejects_a_second_active_run_per_project(db_session):
    project, run, _ = _setup_run_with_hard_constraint(db_session, "found-second-run")
    with pytest.raises(HTTPException) as exc_info:
        open_selection_run(db_session, project_id=project.id, target_genome_snapshot_id=run.target_genome_snapshot_id)
    assert exc_info.value.status_code == 409


def test_candidate_status_illegal_transition_raises(db_session):
    project, run, _ = _setup_run_with_hard_constraint(db_session, "found-candidate-illegal")
    candidate = create_candidate(db_session, selection_run_id=run.id, name="Terminal")
    candidate.status = CandidateStatus.SELECTED.value  # a terminal candidate status (no outgoing edges)

    with pytest.raises(IllegalTransition):
        _set_candidate_status(candidate, CandidateStatus.ELIGIBLE, actor="test")


def test_advance_run_raises_when_target_is_permanently_unreachable(db_session):
    """Once a run enters the design §13 cycle (genome_review..monitoring), the
    pre-cycle states (draft..reconciled) never reappear on any forward edge —
    ``_advance_run`` must detect this and raise rather than loop forever."""
    project, run, _ = _setup_run_with_hard_constraint(db_session, "found-unreachable")
    assert run.state == SelectionRunState.REQUIREMENTS_COMPILED.value  # already inside the cycle

    with pytest.raises(IllegalTransition):
        _advance_run(run, SelectionRunState.INTAKE_COMPLETE, actor="test")


# --- C2 reuse-links round-trip --------------------------------------------------


def test_c2_links_round_trip_recommendation_ref_and_evaluation_ref(db_session):
    project, run, _constraint_id = _setup_run_with_hard_constraint(db_session, "found-c2")

    recommendation = Recommendation(project_id=project.id, title="Use managed PostgreSQL")
    db_session.add(recommendation)
    db_session.commit()

    candidate = create_candidate(
        db_session, selection_run_id=run.id, name="C2-linked", recommendation_ref=recommendation.id,
    )
    db_session.refresh(candidate)
    assert candidate.recommendation_ref == recommendation.id

    evaluate_eligibility(db_session, selection_run_id=run.id)
    score_candidate(db_session, candidate_id=candidate.id)

    evaluation = Evaluation(project_id=project.id, evaluation_type="foundation_score_backing")
    db_session.add(evaluation)
    db_session.commit()

    score_row = (
        db_session.query(FoundationScore).filter(FoundationScore.candidate_id == candidate.id).first()
    )
    assert score_row is not None
    score_row.evaluation_ref = evaluation.id
    db_session.commit()
    db_session.refresh(score_row)
    assert score_row.evaluation_ref == evaluation.id
