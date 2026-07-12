"""design §20 MVP fixture validates against the contracts (RFC-0017 / AOS-FOUND-CONTRACTS-001)."""
from __future__ import annotations

import json
from pathlib import Path

import aos_core.foundation as foundation_pkg
from aos_core.foundation import contracts

FIXTURE_PATH = Path(foundation_pkg.__file__).parent / "fixtures" / "mvp_scenario.json"

_KEY_TO_MODEL: dict[str, type] = {
    "evidence_sources": contracts.EvidenceSource,
    "evidence_source_versions": contracts.EvidenceSourceVersion,
    "evidence_fragments": contracts.EvidenceFragment,
    "claims": contracts.Claim,
    "claim_evidence_links": contracts.ClaimEvidenceLink,
    "evidence_conflicts": contracts.EvidenceConflict,
    "corpus_snapshots": contracts.CorpusSnapshot,
    "genome_snapshots": contracts.GenomeSnapshot,
    "genome_traits": contracts.GenomeTrait,
    "foundation_requirements": contracts.FoundationRequirement,
    "open_questions": contracts.OpenQuestion,
}


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_file_exists() -> None:
    assert FIXTURE_PATH.exists()


def test_fixture_every_list_validates_against_its_contract() -> None:
    data = _load_fixture()
    validated_any = False
    for key, model_cls in _KEY_TO_MODEL.items():
        for raw in data.get(key, []):
            model_cls(**raw)
            validated_any = True
    assert validated_any


def test_fixture_has_at_least_one_observed_claim_and_one_claimed_requirement() -> None:
    data = _load_fixture()
    claims = [contracts.Claim(**raw) for raw in data["claims"]]
    assert any(c.truth_layer.value == "observed" for c in claims)
    assert any(c.truth_layer.value == "claimed" and c.claim_type.value == "requirement" for c in claims)


def test_fixture_has_a_code_vs_intent_conflict() -> None:
    data = _load_fixture()
    conflicts = [contracts.EvidenceConflict(**raw) for raw in data["evidence_conflicts"]]
    assert any(c.conflict_type.value == "implementation_drift" for c in conflicts)


def test_fixture_has_current_and_intended_genome_snapshots_with_traits() -> None:
    data = _load_fixture()
    genomes = [contracts.GenomeSnapshot(**raw) for raw in data["genome_snapshots"]]
    state_views = {g.state_view.value for g in genomes}
    assert {"current", "intended"} <= state_views

    traits = [contracts.GenomeTrait(**raw) for raw in data["genome_traits"]]
    genome_ids_with_traits = {t.genome_snapshot_id for t in traits}
    for genome in genomes:
        assert genome.id in genome_ids_with_traits


def test_fixture_has_a_hard_constraint_requirement() -> None:
    data = _load_fixture()
    reqs = [contracts.FoundationRequirement(**raw) for raw in data["foundation_requirements"]]
    assert any(r.requirement_type.value == "hard_constraint" for r in reqs)
    assert len(reqs) >= 2
