"""RFC-0019 (System Genome MVP) — each seed :class:`TraitRule` fires on a
matching claim and abstains otherwise.

Hermetic: no DB needed for most of these (rules are pure functions over an
in-memory ``Claim`` list); a couple of tests use ``db_session`` to build claims
through ``services/evidence.py`` (the only write path) so IDs/derivation are
realistic. No LLM, no network (AOS-GENOME-MODELS-001, RFC-0019 non-goal).
"""

from __future__ import annotations

from aos_core.foundation.enums import GenomeDimension, TraitClassification
from aos_core.models import Claim, Project
from aos_core.services.evidence import create_claim
from aos_core.services.genome_rules import FOUNDATION_SHAPING_DIMENSIONS, GENOME_RULES


def _claim(*, statement: str, domain: str = "runtime", confidence: float = 0.9, claim_id: str = "c1") -> Claim:
    """A bare, unpersisted Claim row — enough for a TraitRule's pure predicate."""
    return Claim(
        id=claim_id,
        project_id="proj-1",
        statement=statement,
        claim_type="fact",
        truth_layer="observed",
        domain=domain,
        confidence=confidence,
    )


def _rule(dimension: GenomeDimension, trait_key: str):
    for rule in GENOME_RULES:
        if rule.dimension == dimension and rule.trait_key == trait_key:
            return rule
    raise AssertionError(f"no seed rule for {dimension}/{trait_key}")


def test_foundation_shaping_dimensions_cover_the_six_seed_dimensions():
    assert FOUNDATION_SHAPING_DIMENSIONS == {
        GenomeDimension.RUNTIME_TOPOLOGY,
        GenomeDimension.DEPLOYMENT_OWNERSHIP,
        GenomeDimension.DATA_PROFILE,
        GenomeDimension.AI_AUTONOMY,
        GenomeDimension.ASSURANCE_CRITICALITY,
        GenomeDimension.SECURITY_PRIVACY,
    }
    assert 6 <= len(GENOME_RULES) <= 10


def test_runtime_distributed_fires_on_queue_worker_claim():
    rule = _rule(GenomeDimension.RUNTIME_TOPOLOGY, "distributed_workers")
    claim = _claim(statement="A background worker consumes jobs from a message queue.")
    result = rule.derive([claim])
    assert result is not None
    assert result.value is True
    assert result.classification in (TraitClassification.PRIMARY, TraitClassification.CONDITIONAL)
    assert result.supporting_claim_ids == [claim.id]


def test_runtime_distributed_abstains_without_distributed_signal():
    rule = _rule(GenomeDimension.RUNTIME_TOPOLOGY, "distributed_workers")
    claim = _claim(statement="A single service listens on port 8000.")
    assert rule.derive([claim]) is None


def test_runtime_monolithic_fires_when_no_distributed_signal_present():
    rule = _rule(GenomeDimension.RUNTIME_TOPOLOGY, "monolithic")
    claim = _claim(statement="A single service listens on port 8000.")
    result = rule.derive([claim])
    assert result is not None
    assert result.value is True
    assert result.supporting_claim_ids == [claim.id]


def test_runtime_monolithic_abstains_when_distributed_signal_present():
    rule = _rule(GenomeDimension.RUNTIME_TOPOLOGY, "monolithic")
    claim = _claim(statement="A background worker consumes jobs from a message queue.")
    assert rule.derive([claim]) is None


def test_runtime_monolithic_abstains_with_no_runtime_claims_at_all():
    rule = _rule(GenomeDimension.RUNTIME_TOPOLOGY, "monolithic")
    claim = _claim(statement="The system may not retain category X data beyond 30 days.", domain="data")
    assert rule.derive([claim]) is None


def test_deployment_local_first_fires_on_no_public_cloud_claim():
    rule = _rule(GenomeDimension.DEPLOYMENT_OWNERSHIP, "local_first")
    claim = _claim(statement="The deployment environment must not require public cloud connectivity.", domain="deployment")
    result = rule.derive([claim])
    assert result is not None
    assert result.value is True
    assert result.supporting_claim_ids == [claim.id]


def test_deployment_local_first_abstains_without_local_keywords():
    rule = _rule(GenomeDimension.DEPLOYMENT_OWNERSHIP, "local_first")
    claim = _claim(statement="The system is deployed to a managed cloud provider.", domain="deployment")
    assert rule.derive([claim]) is None


def test_deployment_managed_cloud_fires_on_cloud_claim():
    rule = _rule(GenomeDimension.DEPLOYMENT_OWNERSHIP, "managed_cloud")
    claim = _claim(statement="The system is deployed to a managed cloud provider.", domain="deployment")
    result = rule.derive([claim])
    assert result is not None
    assert result.value is True
    assert result.supporting_claim_ids == [claim.id]


def test_deployment_managed_cloud_abstains_on_no_public_cloud_claim():
    """A 'no public cloud' claim contains the substring 'cloud' but must NOT
    also fire managed_cloud — the two rules are mutually exclusive."""
    rule = _rule(GenomeDimension.DEPLOYMENT_OWNERSHIP, "managed_cloud")
    claim = _claim(statement="The deployment environment must not require public cloud connectivity.", domain="deployment")
    assert rule.derive([claim]) is None


def test_data_profile_regulated_fires_on_retention_claim():
    rule = _rule(GenomeDimension.DATA_PROFILE, "regulated_data")
    claim = _claim(statement="The system may not retain category X data beyond 30 days.", domain="data")
    result = rule.derive([claim])
    assert result is not None
    assert result.value is True
    assert result.supporting_claim_ids == [claim.id]


def test_data_profile_regulated_abstains_without_keywords():
    rule = _rule(GenomeDimension.DATA_PROFILE, "regulated_data")
    claim = _claim(statement="The system stores time-series metrics.", domain="data")
    assert rule.derive([claim]) is None


def test_ai_autonomy_agentic_fires_on_agent_claim():
    rule = _rule(GenomeDimension.AI_AUTONOMY, "agentic")
    claim = _claim(statement="An autonomous agent drafts council reviews for human approval.", domain="ai")
    result = rule.derive([claim])
    assert result is not None
    assert result.value is True
    assert result.supporting_claim_ids == [claim.id]


def test_ai_autonomy_agentic_abstains_without_keywords():
    rule = _rule(GenomeDimension.AI_AUTONOMY, "agentic")
    claim = _claim(statement="A cron job runs a nightly backup.", domain="ops")
    assert rule.derive([claim]) is None


def test_assurance_criticality_fires_on_business_critical_claim():
    rule = _rule(GenomeDimension.ASSURANCE_CRITICALITY, "business_critical")
    claim = _claim(statement="This service is business critical and requires high availability.", domain="assurance")
    result = rule.derive([claim])
    assert result is not None
    assert result.value is True
    assert result.supporting_claim_ids == [claim.id]


def test_assurance_criticality_abstains_without_keywords():
    rule = _rule(GenomeDimension.ASSURANCE_CRITICALITY, "business_critical")
    claim = _claim(statement="This is an internal prototype used by one team.", domain="assurance")
    assert rule.derive([claim]) is None


def test_security_privacy_restricted_fires_on_confidential_claim():
    rule = _rule(GenomeDimension.SECURITY_PRIVACY, "restricted")
    claim = _claim(statement="Tenant data is confidential and must remain tenant isolated.", domain="security")
    result = rule.derive([claim])
    assert result is not None
    assert result.value is True
    assert result.supporting_claim_ids == [claim.id]


def test_security_privacy_restricted_abstains_without_keywords():
    rule = _rule(GenomeDimension.SECURITY_PRIVACY, "restricted")
    claim = _claim(statement="This repository's README is publicly readable.", domain="security")
    assert rule.derive([claim]) is None


def test_rule_fires_over_claims_persisted_through_evidence_service(db_session):
    """Sanity check the rules operate correctly on real, persisted Claim rows
    (not just bare in-memory instances) — created via the only write path."""
    project = Project(name="Genome Rules", slug="genome-rules")
    db_session.add(project)
    db_session.commit()

    claim = create_claim(
        db_session,
        project_id=project.id,
        minted_by="deterministic_tool",
        truth_layer="observed",
        statement="A worker process pulls jobs from a Redis queue.",
        claim_type="fact",
        domain="runtime",
        created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )

    rule = _rule(GenomeDimension.RUNTIME_TOPOLOGY, "distributed_workers")
    result = rule.derive([claim])
    assert result is not None
    assert result.supporting_claim_ids == [claim.id]
