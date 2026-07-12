"""RFC-0019 (System Genome MVP, AOS-GENOME-MODELS-001) — ``generate_genome`` over
hand-built claim sets.

Hermetic: the ``db_session`` fixture (``conftest.py``) creates every table via
sqlite ``Base.metadata.create_all`` (no alembic, no network, no LLM). Claims
are created through ``services/evidence.py`` — the only write path — mirroring
design §20's code-vs-intent scenario: an ``observed`` claim (what the
repository scan found) and a ``claimed`` claim (what stakeholders said they
wanted) can disagree on the same dimension, and the current/intended split
must surface that as different traits, never silently merge them.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from aos_core.foundation.enums import GenomeDimension, GenomeStatus, TraitClassification
from aos_core.models import GenomeSnapshot, GenomeTrait, GenomeTraitClaim, OpenQuestion, Project
from aos_core.services.evidence import create_claim
from aos_core.services.genome import (
    _claims_for_state_view,
    approve_genome,
    compare_genomes,
    generate_genome,
    review_genome,
)


def _project(db, slug: str) -> Project:
    project = Project(name=slug, slug=slug)
    db.add(project)
    db.commit()
    return project


def _observed(db, project, *, statement: str, domain: str, confidence: float = 0.9, claim_type: str = "fact") -> str:
    claim = create_claim(
        db, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement=statement, claim_type=claim_type, domain=domain, created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []}, confidence=confidence,
    )
    return claim.id


def _claimed(db, project, *, statement: str, domain: str, confidence: float = 0.9, claim_type: str = "requirement") -> str:
    claim = create_claim(
        db, project_id=project.id, minted_by="human", truth_layer="claimed",
        statement=statement, claim_type=claim_type, domain=domain, created_by="product manager",
        derivation={"method": "direct", "parent_claim_ids": []}, confidence=confidence,
    )
    return claim.id


def _inferred(db, project, *, statement: str, domain: str, parent_claim_ids: list[str], confidence: float = 0.7) -> str:
    claim = create_claim(
        db, project_id=project.id, minted_by="agent", truth_layer="inferred",
        statement=statement, claim_type="finding", domain=domain, created_by="genome-classifier",
        derivation={"method": "aggregated", "parent_claim_ids": parent_claim_ids}, confidence=confidence,
    )
    return claim.id


# --- the current/intended claim-set split -----------------------------------


def test_claims_for_state_view_splits_by_truth_layer_and_inference_parentage(db_session):
    project = _project(db_session, "genome-split")
    observed_id = _observed(db_session, project, statement="A service listens on port 8000.", domain="runtime")
    claimed_id = _claimed(
        db_session, project, statement="The deployment must not require public cloud connectivity.", domain="deployment"
    )
    # Purely machine-inferred over an observed fact -> counts as CURRENT.
    fact_inferred_id = _inferred(
        db_session, project, statement="The system appears latency-sensitive.", domain="workload",
        parent_claim_ids=[observed_id],
    )
    # Inferred from a claimed (stated-intent) claim -> counts as INTENDED.
    intent_inferred_id = _inferred(
        db_session, project, statement="The system likely requires offline tolerance.", domain="deployment",
        parent_claim_ids=[claimed_id],
    )

    current = _claims_for_state_view(db_session, project_id=project.id, state_view="current")
    intended = _claims_for_state_view(db_session, project_id=project.id, state_view="intended")

    current_ids = {c.id for c in current}
    intended_ids = {c.id for c in intended}

    assert current_ids == {observed_id, fact_inferred_id}
    assert intended_ids == {claimed_id, intent_inferred_id}


def test_claims_for_state_view_rejects_target_and_candidate(db_session):
    project = _project(db_session, "genome-split-unsupported")
    with pytest.raises(ValueError):
        _claims_for_state_view(db_session, project_id=project.id, state_view="target")
    with pytest.raises(ValueError):
        _claims_for_state_view(db_session, project_id=project.id, state_view="candidate")


# --- current vs intended drift (design §20 step 6->8) -----------------------


def _drift_project_claims(db, project):
    """Observed: distributed runtime + a managed-cloud deployment fact.
    Claimed: an explicit local-first requirement + a data-retention constraint.
    The deployment_ownership dimension must DIFFER between current and intended."""
    _observed(db, project, statement="A worker process pulls jobs from a message queue.", domain="runtime")
    _observed(
        db, project,
        statement="The control-plane repository's Dockerfile declares a managed cloud SDK dependency.",
        domain="deployment",
    )
    _claimed(
        db, project, statement="The deployment environment must not require public cloud connectivity.",
        domain="deployment",
    )
    _claimed(db, project, statement="The system may not retain category X data beyond 30 days.", domain="data")


def test_generate_genome_current_and_intended_differ_on_at_least_one_dimension(db_session):
    project = _project(db_session, "genome-drift")
    _drift_project_claims(db_session, project)

    current = generate_genome(db_session, project_id=project.id, state_view="current")
    intended = generate_genome(db_session, project_id=project.id, state_view="intended")

    current_traits = db_session.query(GenomeTrait).filter(GenomeTrait.genome_snapshot_id == current.id).all()
    intended_traits = db_session.query(GenomeTrait).filter(GenomeTrait.genome_snapshot_id == intended.id).all()

    current_deployment = {t.trait_key for t in current_traits if t.dimension == GenomeDimension.DEPLOYMENT_OWNERSHIP.value}
    intended_deployment = {t.trait_key for t in intended_traits if t.dimension == GenomeDimension.DEPLOYMENT_OWNERSHIP.value}

    # Current (observed code fact): a managed-cloud dependency. Intended
    # (stated requirement): local-first. Same dimension, different trait — the
    # code-vs-intent contradiction the design's MVP scenario calls for.
    assert current_deployment == {"managed_cloud"}
    assert intended_deployment == {"local_first"}
    assert current_deployment != intended_deployment

    # runtime_topology only fired from the observed worker/queue claim, so it
    # is evidenced in `current` but `unknown` in `intended`.
    current_runtime = [t for t in current_traits if t.dimension == GenomeDimension.RUNTIME_TOPOLOGY.value]
    intended_runtime = [t for t in intended_traits if t.dimension == GenomeDimension.RUNTIME_TOPOLOGY.value]
    assert any(t.trait_key == "distributed_workers" for t in current_runtime)
    assert all(t.classification == TraitClassification.UNKNOWN.value for t in intended_runtime)

    # Every persisted trait links back to at least one supporting claim unless unknown.
    for trait in current_traits + intended_traits:
        links = db_session.query(GenomeTraitClaim).filter(GenomeTraitClaim.trait_id == trait.id).all()
        if trait.classification == TraitClassification.UNKNOWN.value:
            assert links == []
        else:
            assert any(link.polarity == "supporting" for link in links)


def test_unevidenced_foundation_shaping_dimensions_are_explicit_unknown_not_omitted(db_session):
    project = _project(db_session, "genome-sparse")
    _observed(db_session, project, statement="A worker process pulls jobs from a message queue.", domain="runtime")

    snapshot = generate_genome(db_session, project_id=project.id, state_view="current")
    traits = db_session.query(GenomeTrait).filter(GenomeTrait.genome_snapshot_id == snapshot.id).all()
    dims_present = {t.dimension for t in traits}

    from aos_core.services.genome_rules import FOUNDATION_SHAPING_DIMENSIONS

    assert {d.value for d in FOUNDATION_SHAPING_DIMENSIONS} <= dims_present

    unknown_traits = [t for t in traits if t.classification == TraitClassification.UNKNOWN.value]
    unknown_dims = {t.dimension for t in unknown_traits}
    assert GenomeDimension.DEPLOYMENT_OWNERSHIP.value in unknown_dims
    assert GenomeDimension.DATA_PROFILE.value in unknown_dims
    for trait in unknown_traits:
        assert trait.confidence == 0.0
        assert trait.value is None


def test_open_questions_generated_only_for_unevidenced_foundation_shaping_dimensions(db_session):
    project = _project(db_session, "genome-questions")
    _observed(db_session, project, statement="A worker process pulls jobs from a message queue.", domain="runtime")
    _observed(
        db_session, project, statement="The deployment runs air-gapped with no public cloud connectivity.",
        domain="deployment",
    )
    _observed(db_session, project, statement="The system retains personal data for compliance purposes.", domain="data")
    _observed(
        db_session, project, statement="An autonomous agent executes build plans without human review.", domain="ai",
    )

    snapshot = generate_genome(db_session, project_id=project.id, state_view="current")
    questions = db_session.query(OpenQuestion).filter(OpenQuestion.genome_snapshot_id == snapshot.id).all()

    affected = {tuple(q.affected_dimensions) for q in questions}
    assert affected == {
        (GenomeDimension.ASSURANCE_CRITICALITY.value,),
        (GenomeDimension.SECURITY_PRIVACY.value,),
    }
    assert snapshot.open_question_count == len(questions) == 2

    # None of the four evidenced dimensions got a question.
    evidenced = {
        GenomeDimension.RUNTIME_TOPOLOGY.value,
        GenomeDimension.DEPLOYMENT_OWNERSHIP.value,
        GenomeDimension.DATA_PROFILE.value,
        GenomeDimension.AI_AUTONOMY.value,
    }
    for question in questions:
        assert not (set(question.affected_dimensions) & evidenced)


# --- coverage-calibrated confidence (LES-023) --------------------------------


def test_coverage_calibration_sparse_scores_lower_than_dense_with_identical_per_trait_confidence(db_session):
    sparse = _project(db_session, "genome-coverage-sparse")
    _observed(
        db_session, sparse, statement="A worker process pulls jobs from a message queue.", domain="runtime",
        confidence=0.9,
    )

    dense = _project(db_session, "genome-coverage-dense")
    _observed(
        db_session, dense, statement="A worker process pulls jobs from a message queue.", domain="runtime",
        confidence=0.9,
    )
    _observed(
        db_session, dense, statement="The deployment runs air-gapped with no public cloud connectivity.",
        domain="deployment", confidence=0.9,
    )
    _observed(db_session, dense, statement="The system retains personal data for compliance purposes.", domain="data", confidence=0.9)
    _observed(
        db_session, dense, statement="An autonomous agent executes build plans without human review.", domain="ai",
        confidence=0.9,
    )

    sparse_snapshot = generate_genome(db_session, project_id=sparse.id, state_view="current")
    dense_snapshot = generate_genome(db_session, project_id=dense.id, state_view="current")

    sparse_traits = db_session.query(GenomeTrait).filter(GenomeTrait.genome_snapshot_id == sparse_snapshot.id).all()
    dense_traits = db_session.query(GenomeTrait).filter(GenomeTrait.genome_snapshot_id == dense_snapshot.id).all()
    sparse_evidenced = [t.confidence for t in sparse_traits if t.classification != TraitClassification.UNKNOWN.value]
    dense_evidenced = [t.confidence for t in dense_traits if t.classification != TraitClassification.UNKNOWN.value]

    # Per-trait confidence is identical across both projects...
    assert sparse_evidenced == pytest.approx([0.9])
    assert dense_evidenced == pytest.approx([0.9, 0.9, 0.9, 0.9])

    # ...but coverage differs (1/6 vs 4/6), so the coverage-calibrated
    # aggregate must NOT be equal — sparse must read strictly lower (LES-023:
    # a naive mean-of-confidences would score both identically at 0.9).
    assert sparse_snapshot.coverage < dense_snapshot.coverage
    assert sparse_snapshot.aggregate_confidence < dense_snapshot.aggregate_confidence
    assert sparse_snapshot.aggregate_confidence == pytest.approx(0.9 * (1 / 6))
    assert dense_snapshot.aggregate_confidence == pytest.approx(0.9 * (4 / 6))


# --- supersession invariant ---------------------------------------------------


def test_generate_genome_supersedes_prior_snapshot_for_same_project_and_state_view(db_session):
    project = _project(db_session, "genome-supersede")
    _observed(db_session, project, statement="A worker process pulls jobs from a message queue.", domain="runtime")

    first = generate_genome(db_session, project_id=project.id, state_view="current")
    assert first.version == 1
    assert first.status == GenomeStatus.DRAFT.value

    second = generate_genome(db_session, project_id=project.id, state_view="current")
    assert second.version == 2

    db_session.refresh(first)
    assert first.status == GenomeStatus.SUPERSEDED.value

    non_superseded = (
        db_session.query(GenomeSnapshot)
        .filter(
            GenomeSnapshot.project_id == project.id,
            GenomeSnapshot.state_view == "current",
            GenomeSnapshot.status != GenomeStatus.SUPERSEDED.value,
        )
        .all()
    )
    assert len(non_superseded) == 1
    assert non_superseded[0].id == second.id


# --- review / approve -----------------------------------------------------


def test_review_and_approve_genome_transitions(db_session):
    project = _project(db_session, "genome-approve")
    _observed(db_session, project, statement="A worker process pulls jobs from a message queue.", domain="runtime")
    snapshot = generate_genome(db_session, project_id=project.id, state_view="current")

    with pytest.raises(HTTPException):
        approve_genome(db_session, genome_id=snapshot.id, approver="operator")

    reviewed = review_genome(db_session, genome_id=snapshot.id, reviewer="operator")
    assert reviewed.status == GenomeStatus.REVIEWED.value

    with pytest.raises(HTTPException):
        review_genome(db_session, genome_id=snapshot.id, reviewer="operator")

    approved = approve_genome(db_session, genome_id=snapshot.id, approver="operator", rationale="looks right")
    assert approved.status == GenomeStatus.APPROVED.value
    assert approved.approved_by == "operator"
    assert approved.approved_at is not None


# --- compare_genomes ----------------------------------------------------------


def test_compare_genomes_returns_a_delta(db_session):
    project = _project(db_session, "genome-compare")
    _drift_project_claims(db_session, project)

    current = generate_genome(db_session, project_id=project.id, state_view="current")
    intended = generate_genome(db_session, project_id=project.id, state_view="intended")

    delta = compare_genomes(db_session, from_id=current.id, to_id=intended.id)

    assert delta.from_snapshot_id == current.id
    assert delta.to_snapshot_id == intended.id
    total_changes = (
        len(delta.changes["added_traits"]) + len(delta.changes["removed_traits"]) + len(delta.changes["changed_traits"])
    )
    assert total_changes > 0
    assert isinstance(delta.changes["coverage_delta"], float)
    assert isinstance(delta.changes["confidence_delta"], float)

    # deployment_ownership's trait_key changed identity (managed_cloud -> local_first).
    added_keys = {(c["dimension"], c["trait_key"]) for c in delta.changes["added_traits"]}
    removed_keys = {(c["dimension"], c["trait_key"]) for c in delta.changes["removed_traits"]}
    assert (GenomeDimension.DEPLOYMENT_OWNERSHIP.value, "local_first") in added_keys
    assert (GenomeDimension.DEPLOYMENT_OWNERSHIP.value, "managed_cloud") in removed_keys
