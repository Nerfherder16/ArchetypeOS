"""Foundation contract models — minimal construction, extra="forbid", frozen (RFC-0017 / AOS-FOUND-CONTRACTS-001)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from aos_core.foundation import contracts

# (model class, minimal-but-valid constructor kwargs) for every contract entity.
_MINIMAL: list[tuple[type, dict]] = [
    (contracts.Locator, {}),
    (
        contracts.EvidenceSource,
        dict(
            id="src-1",
            project_id="proj-1",
            source_type="repository",
            title="a repo",
            origin="github",
            originator="acme/repo",
            minted_by="deterministic_tool",
        ),
    ),
    (
        contracts.EvidenceSourceVersion,
        dict(
            id="srcv-1",
            source_id="src-1",
            version_ref="abc123",
            content_hash="deadbeef",
            ingestion_method="scan",
            minted_by="deterministic_tool",
        ),
    ),
    (
        contracts.EvidenceFragment,
        dict(
            id="frag-1",
            source_version_id="srcv-1",
            content_hash="deadbeef",
            excerpt="some text",
            extraction_method="deterministic",
            minted_by="deterministic_tool",
        ),
    ),
    (contracts.ClaimScope, {}),
    (contracts.Derivation, dict(method="direct")),
    (
        contracts.Claim,
        dict(
            id="claim-1",
            project_id="proj-1",
            statement="A fact.",
            claim_type="fact",
            truth_layer="observed",
            domain="deployment",
            created_by="scanner",
            derivation=contracts.Derivation(method="direct"),
            minted_by="deterministic_tool",
        ),
    ),
    (
        contracts.ClaimEvidenceLink,
        dict(claim_id="claim-1", fragment_id="frag-1", relationship="supports", minted_by="deterministic_tool"),
    ),
    (
        contracts.ClaimRelationshipEdge,
        dict(from_claim_id="claim-1", to_claim_id="claim-2", relationship="supports", minted_by="agent"),
    ),
    (
        contracts.EvidenceConflict,
        dict(
            id="conflict-1",
            project_id="proj-1",
            claim_ids=["claim-1", "claim-2"],
            conflict_type="direct_contradiction",
            materiality="high",
            minted_by="agent",
        ),
    ),
    (contracts.RepositoryRef, dict(repository_id="repo-1", commit_sha="abc123")),
    (contracts.CorpusSnapshot, dict(id="corpus-1", project_id="proj-1", purpose="genome_generation")),
    (
        contracts.OpenQuestion,
        dict(
            id="q-1",
            project_id="proj-1",
            question="Must the system work offline?",
            materiality="high",
            reason="Determines runtime design.",
            answer_type="boolean",
            minted_by="agent",
        ),
    ),
    (contracts.Archetype, dict(name="Local-First Control Plane", confidence=0.9)),
    (
        contracts.GenomeSnapshot,
        dict(id="genome-1", project_id="proj-1", corpus_snapshot_id="corpus-1", state_view="current", minted_by="agent"),
    ),
    (
        contracts.GenomeTrait,
        dict(
            id="trait-1",
            genome_snapshot_id="genome-1",
            dimension="runtime_topology",
            trait_key="modular_monolith",
            value=True,
            value_type="boolean",
            minted_by="agent",
        ),
    ),
    (
        contracts.FoundationRequirement,
        dict(
            id="req-1",
            project_id="proj-1",
            requirement_type="hard_constraint",
            domain="deployment",
            statement="Must run offline.",
            priority="must",
            verification_method="architecture_inspection",
            minted_by="agent",
        ),
    ),
    (
        contracts.FoundationCandidate,
        dict(id="cand-1", selection_run_id="run-1", name="Local Durable Control Plane", minted_by="agent"),
    ),
    (
        contracts.FoundationElement,
        dict(
            id="elem-1",
            candidate_id="cand-1",
            domain="data",
            title="PostgreSQL as store",
            decision="Use PostgreSQL.",
            verification_method="prototype",
            minted_by="agent",
        ),
    ),
    (
        contracts.CandidateScore,
        dict(
            candidate_id="cand-1",
            criterion="operational_feasibility",
            raw_score=82.0,
            weight=0.8,
            confidence=0.74,
            adjusted_score=74.0,
            minted_by="agent",
        ),
    ),
    (
        contracts.ValidationTask,
        dict(
            id="val-1",
            candidate_id="cand-1",
            title="Benchmark latency",
            validation_type="benchmark",
            question="Is latency under 250ms?",
            minted_by="agent",
        ),
    ),
    (
        contracts.FoundationBaseline,
        dict(
            id="baseline-1",
            project_id="proj-1",
            candidate_id="cand-1",
            target_genome_snapshot_id="genome-1",
            approved_decision_id="decision-1",
            corpus_snapshot_id="corpus-1",
            approved_by="operator",
            minted_by="approval_process",
        ),
    ),
    (
        contracts.SelectionStageEvent,
        dict(id="event-1", selection_run_id="run-1", actor="system", new_state="draft"),
    ),
]


@pytest.mark.parametrize("model_cls,kwargs", _MINIMAL, ids=[m.__name__ for m, _ in _MINIMAL])
def test_constructs_from_minimal_valid_dict(model_cls: type, kwargs: dict) -> None:
    instance = model_cls(**kwargs)
    assert isinstance(instance, model_cls)


@pytest.mark.parametrize("model_cls,kwargs", _MINIMAL, ids=[m.__name__ for m, _ in _MINIMAL])
def test_extra_field_is_rejected(model_cls: type, kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        model_cls(**kwargs, this_field_does_not_exist="boom")


@pytest.mark.parametrize("model_cls,kwargs", _MINIMAL, ids=[m.__name__ for m, _ in _MINIMAL])
def test_model_is_frozen(model_cls: type, kwargs: dict) -> None:
    instance = model_cls(**kwargs)
    first_field = next(iter(kwargs)) if kwargs else next(iter(model_cls.model_fields))
    with pytest.raises(ValidationError):
        setattr(instance, first_field, "mutated")
