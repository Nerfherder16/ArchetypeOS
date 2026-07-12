"""RFC-0018 (Evidence Spine) — the C1/C3/C4 guards, proven as regression tests.

- **C3**: ``create_claim`` calls ``foundation.truth.may_mint``; an ``agent`` can
  never persist an ``observed`` claim (only ``deterministic_tool`` can), but an
  ``agent`` CAN persist ``claimed``/``inferred``.
- **C1**: ``create_claim`` refuses ``truth_layer="decided"`` outright;
  ``project_decided_claim`` is the only minter, and only from an **approved**
  ``Decision`` (else 409).
- **C4**: ``content_hash`` is set at insert and equals
  ``foundation.serialization.content_hash`` of the matching contract; a
  content-field UPDATE is refused (``ImmutableContentError``); ``freeze_corpus``'s
  ``claim_set_hash`` is permutation-invariant across ``source_version_ids`` order.

Hermetic: sqlite ``create_all`` via the shared ``db_session`` fixture, no
alembic, no network, no LLM.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from aos_core.foundation import contracts
from aos_core.foundation.enums import ClaimType, Materiality, Polarity, TruthLayer
from aos_core.foundation.serialization import content_hash as compute_content_hash
from aos_core.foundation.truth import MinterClass
from aos_core.models import Claim, Decision, EvidenceConflict, EvidenceSource, ImmutableContentError, Project
from aos_core.services.evidence import create_claim, create_source, freeze_corpus, open_conflict, project_decided_claim

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def _project(db) -> Project:
    project = Project(name="Evidence Guards", slug="evidence-guards")
    db.add(project)
    db.commit()
    return project


# ---------------------------------------------------------------------------
# C3 — deterministic-only-observed truth-layer minter guard
# ---------------------------------------------------------------------------


def test_c3_agent_cannot_mint_observed_claim(db_session):
    project = _project(db_session)
    with pytest.raises(ValueError, match="C3 violation"):
        create_claim(
            db_session, project_id=project.id, minted_by="agent", truth_layer="observed",
            statement="An agent tries to assert an observed fact.", claim_type="fact",
            domain="runtime", created_by="some-agent",
            derivation={"method": "direct", "parent_claim_ids": []},
        )


def test_c3_deterministic_tool_can_mint_observed_claim(db_session):
    project = _project(db_session)
    claim = create_claim(
        db_session, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="The Dockerfile exposes port 8000.", claim_type="fact",
        domain="runtime", created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )
    assert claim.truth_layer == "observed"
    assert claim.minted_by == "deterministic_tool"


@pytest.mark.parametrize("truth_layer", ["claimed", "inferred"])
def test_c3_agent_can_mint_claimed_or_inferred_claim(db_session, truth_layer):
    project = _project(db_session)
    claim = create_claim(
        db_session, project_id=project.id, minted_by="agent", truth_layer=truth_layer,
        statement="An agent's finding.", claim_type="finding",
        domain="runtime", created_by="genome-classifier",
        derivation={"method": "aggregated", "parent_claim_ids": []},
    )
    assert claim.truth_layer == truth_layer
    assert claim.minted_by == "agent"


def test_c3_human_cannot_mint_inferred_claim(db_session):
    project = _project(db_session)
    with pytest.raises(ValueError, match="C3 violation"):
        create_claim(
            db_session, project_id=project.id, minted_by="human", truth_layer="inferred",
            statement="A human tries to assert an inference.", claim_type="finding",
            domain="runtime", created_by="someone",
            derivation={"method": "direct", "parent_claim_ids": []},
        )


# ---------------------------------------------------------------------------
# C1 — decided claims are projected only from an approved Decision
# ---------------------------------------------------------------------------


def test_c1_create_claim_refuses_decided_truth_layer(db_session):
    project = _project(db_session)
    with pytest.raises(ValueError, match="C1 violation"):
        create_claim(
            db_session, project_id=project.id, minted_by="approval_process", truth_layer="decided",
            statement="Smuggling a decided claim.", claim_type="fact",
            domain="runtime", created_by="someone",
            derivation={"method": "approved", "parent_claim_ids": []},
        )


def test_c1_project_decided_claim_from_approved_decision(db_session):
    project = _project(db_session)
    decision = Decision(
        project_id=project.id, title="Adopt local-first deployment", status="approved",
        decision="Adopt a local-first deployment model.", confidence=0.9, approved_by="operator@example.com",
    )
    db_session.add(decision)
    db_session.commit()

    claim = project_decided_claim(db_session, decision_id=decision.id)

    assert claim.truth_layer == "decided"
    assert claim.minted_by == "approval_process"
    assert claim.decision_id == decision.id
    assert claim.derivation == {"method": "approved", "parent_claim_ids": []}


def test_c1_project_decided_claim_from_non_approved_decision_raises(db_session):
    project = _project(db_session)
    decision = Decision(project_id=project.id, title="Draft decision", status="draft")
    db_session.add(decision)
    db_session.commit()

    with pytest.raises(HTTPException) as excinfo:
        project_decided_claim(db_session, decision_id=decision.id)
    assert excinfo.value.status_code == 409
    assert "approved" in excinfo.value.detail


def test_c1_project_decided_claim_missing_decision_404s(db_session):
    with pytest.raises(HTTPException) as excinfo:
        project_decided_claim(db_session, decision_id=UNKNOWN_ID)
    assert excinfo.value.status_code == 404


# ---------------------------------------------------------------------------
# C4 — content_hash / immutability
# ---------------------------------------------------------------------------


def test_c4_source_content_hash_equals_foundation_content_hash(db_session):
    project = _project(db_session)
    source = create_source(
        db_session, project_id=project.id, minted_by="deterministic_tool",
        source_type="repository", title="control-plane repository", origin="github",
        originator="acme/control-plane",
    )

    expected_contract = contracts.EvidenceSource(
        id=source.id,
        project_id=source.project_id,
        source_type=source.source_type,
        title=source.title,
        origin=source.origin,
        originator=source.originator,
        canonical_uri=source.canonical_uri,
        sensitivity=source.sensitivity,
        authority_domains=source.authority_domains,
        access_policy_id=source.access_policy_id,
        status=source.status,
        created_at=None,
        minted_by=source.minted_by,
    )
    assert source.content_hash == compute_content_hash(expected_contract)


def test_c4_claim_content_hash_equals_foundation_content_hash(db_session):
    project = _project(db_session)
    claim = create_claim(
        db_session, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="A service listens on port 8000.", claim_type="fact",
        domain="runtime", created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )

    expected_contract = contracts.Claim(
        id=claim.id,
        project_id=claim.project_id,
        statement=claim.statement,
        claim_type=ClaimType(claim.claim_type),
        truth_layer=TruthLayer(claim.truth_layer),
        domain=claim.domain,
        scope=contracts.ClaimScope(**claim.scope),
        polarity=Polarity(claim.polarity),
        confidence=claim.confidence,
        materiality=Materiality(claim.materiality),
        status=claim.status,
        valid_from=claim.valid_from,
        valid_until=claim.valid_until,
        created_by=claim.created_by,
        derivation=contracts.Derivation(**claim.derivation),
        minted_by=MinterClass(claim.minted_by),
        decision_ref=None,
    )
    assert claim.content_hash == compute_content_hash(expected_contract)


def test_c4_claim_content_mutation_is_refused(db_session):
    project = _project(db_session)
    claim = create_claim(
        db_session, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="Original statement.", claim_type="fact",
        domain="runtime", created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )

    claim.statement = "Mutated statement — a content field."
    with pytest.raises(ImmutableContentError):
        db_session.commit()
    db_session.rollback()

    reloaded = db_session.get(Claim, claim.id)
    assert reloaded.statement == "Original statement."


def test_c4_source_content_mutation_is_refused(db_session):
    project = _project(db_session)
    source = create_source(
        db_session, project_id=project.id, minted_by="deterministic_tool",
        source_type="repository", title="control-plane repository", origin="github",
        originator="acme/control-plane",
    )

    source.title = "A different title — a content field."
    with pytest.raises(ImmutableContentError):
        db_session.commit()
    db_session.rollback()

    reloaded = db_session.get(EvidenceSource, source.id)
    assert reloaded.title == "control-plane repository"


def test_c4_status_transition_is_not_a_content_mutation(db_session):
    """Status/annotation changes go through explicit transitions, not the content guard."""
    project = _project(db_session)
    claim = create_claim(
        db_session, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="A service listens on port 8000.", claim_type="fact",
        domain="runtime", created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )
    original_hash = claim.content_hash

    claim.status = "disputed"
    db_session.commit()  # must NOT raise — status is excluded from the content guard

    reloaded = db_session.get(Claim, claim.id)
    assert reloaded.status == "disputed"
    assert reloaded.content_hash == original_hash


def test_c4_freeze_corpus_claim_set_hash_is_permutation_invariant(db_session):
    project = _project(db_session)
    source = create_source(
        db_session, project_id=project.id, minted_by="deterministic_tool",
        source_type="repository", title="repo", origin="github", originator="acme/control-plane",
    )
    version_a = create_source(  # a second, distinct source to get two version ids to permute
        db_session, project_id=project.id, minted_by="deterministic_tool",
        source_type="document", title="doc", origin="upload", originator="pm",
    )
    v1 = _add_version(db_session, source.id, "v1")
    v2 = _add_version(db_session, version_a.id, "v2")

    create_claim(
        db_session, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="Claim one.", claim_type="fact", domain="runtime", created_by="scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )
    create_claim(
        db_session, project_id=project.id, minted_by="human", truth_layer="claimed",
        statement="Claim two.", claim_type="requirement", domain="deployment", created_by="pm",
        derivation={"method": "direct", "parent_claim_ids": []},
    )

    snap_forward = freeze_corpus(
        db_session, project_id=project.id, source_version_ids=[v1.id, v2.id], purpose="genome_generation",
    )
    snap_reverse = freeze_corpus(
        db_session, project_id=project.id, source_version_ids=[v2.id, v1.id], purpose="genome_generation",
    )

    assert snap_forward.claim_set_hash is not None
    assert snap_forward.claim_set_hash == snap_reverse.claim_set_hash


# ---------------------------------------------------------------------------
# Conflict lifecycle — stays visible until explicitly resolved
# ---------------------------------------------------------------------------


def test_conflict_stays_open_until_explicitly_resolved(db_session):
    project = _project(db_session)
    claim_a = create_claim(
        db_session, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="Observed: no cloud egress.", claim_type="fact", domain="deployment",
        created_by="scanner", derivation={"method": "direct", "parent_claim_ids": []},
    )
    claim_b = create_claim(
        db_session, project_id=project.id, minted_by="human", truth_layer="claimed",
        statement="Required: must not require public cloud connectivity.", claim_type="requirement",
        domain="deployment", created_by="pm", derivation={"method": "direct", "parent_claim_ids": []},
    )

    conflict = open_conflict(
        db_session, project_id=project.id, claim_ids=[claim_a.id, claim_b.id],
        minted_by="agent", conflict_type="implementation_drift", materiality="high",
        blocking_stages=["foundation_selection"],
    )
    assert conflict.status == "open"
    assert conflict.resolution_decision_id is None

    # It stays open across an unrelated read/query...
    reloaded = db_session.get(EvidenceConflict, conflict.id)
    assert reloaded.status == "open"

    # ...until an explicit resolution transition (not a content-guarded field
    # on this table — RFC-0018 leaves conflicts un-hashed/un-guarded).
    decision = Decision(project_id=project.id, title="Resolve conflict", status="approved", approved_by="op")
    db_session.add(decision)
    db_session.commit()

    reloaded.status = "resolved"
    reloaded.resolution = "Adopted the offline requirement; reworked the Dockerfile."
    reloaded.resolution_decision_id = decision.id
    db_session.commit()

    final = db_session.get(EvidenceConflict, conflict.id)
    assert final.status == "resolved"
    assert final.resolution_decision_id == decision.id


def _add_version(db, source_id, ref):
    from aos_core.services.evidence import add_source_version

    return add_source_version(
        db, source_id=source_id, minted_by="deterministic_tool", version_ref=ref,
        content_hash=f"{ref}-hash".ljust(64, "0"), ingestion_method="scan",
    )
