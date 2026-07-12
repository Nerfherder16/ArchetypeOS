"""RFC-0018 (Evidence Spine) — table shape, links/relationships, junction uniqueness.

Hermetic: the ``db_session`` fixture (``conftest.py``) creates every table via
sqlite ``Base.metadata.create_all`` (no alembic, no network, no LLM). These
tests exercise the ten evidence tables through ``services/evidence.py`` — the
only write path — and prove rows persist and are queryable, and that the
``claim_evidence_links`` junction enforces its unique constraint.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from aos_core.models import (
    Claim,
    ClaimEvidenceLink,
    ClaimRelationship,
    Project,
)
from aos_core.services.evidence import (
    add_fragment,
    add_source_version,
    create_claim,
    create_source,
    freeze_corpus,
    link_evidence,
    relate_claims,
)


def _project(db) -> Project:
    project = Project(name="Evidence Models", slug="evidence-models")
    db.add(project)
    db.commit()
    return project


def _source_chain(db, project):
    """A source -> version -> fragment chain, the common test scaffold."""
    source = create_source(
        db,
        project_id=project.id,
        minted_by="deterministic_tool",
        source_type="repository",
        title="control-plane repository",
        origin="github",
        originator="acme/control-plane",
    )
    version = add_source_version(
        db,
        source_id=source.id,
        minted_by="deterministic_tool",
        version_ref="a1b2c3d",
        content_hash="deadbeef" * 8,
        ingestion_method="scan",
    )
    fragment = add_fragment(
        db,
        source_version_id=version.id,
        minted_by="deterministic_tool",
        content_hash="feedface" * 8,
        excerpt="FROM python:3.12-slim",
        extraction_method="deterministic",
        extraction_confidence=0.99,
        locator={"path": "Dockerfile", "start_line": 1, "end_line": 1},
    )
    return source, version, fragment


def test_source_version_fragment_chain_persists(db_session):
    project = _project(db_session)
    source, version, fragment = _source_chain(db_session, project)

    assert source.project_id == project.id
    assert source.status == "active"
    assert source.content_hash is not None

    assert version.source_id == source.id
    assert version.content_hash == "deadbeef" * 8

    assert fragment.source_version_id == version.id
    assert fragment.locator == {
        "path": "Dockerfile", "start_line": 1, "end_line": 1,
        "page": None, "section": None, "timestamp_start": None,
        "timestamp_end": None, "json_pointer": None,
    }


def test_claim_persists_with_scope_and_derivation(db_session):
    project = _project(db_session)
    claim = create_claim(
        db_session,
        project_id=project.id,
        minted_by="deterministic_tool",
        truth_layer="observed",
        statement="A service listens on port 8000.",
        claim_type="fact",
        domain="runtime",
        created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
        scope={"repository_ids": ["repo-1"]},
    )

    reloaded = db_session.get(Claim, claim.id)
    assert reloaded.project_id == project.id
    assert reloaded.truth_layer == "observed"
    assert reloaded.scope["repository_ids"] == ["repo-1"]
    assert reloaded.derivation == {"method": "direct", "parent_claim_ids": []}
    assert reloaded.minted_by == "deterministic_tool"


def test_link_evidence_persists_and_is_queryable(db_session):
    project = _project(db_session)
    _source, _version, fragment = _source_chain(db_session, project)
    claim = create_claim(
        db_session,
        project_id=project.id,
        minted_by="deterministic_tool",
        truth_layer="observed",
        statement="A service listens on port 8000.",
        claim_type="fact",
        domain="runtime",
        created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )

    link = link_evidence(
        db_session,
        claim_id=claim.id,
        fragment_id=fragment.id,
        minted_by="deterministic_tool",
        relationship="originates",
        relevance=0.9,
        strength="direct",
    )

    rows = db_session.query(ClaimEvidenceLink).filter(ClaimEvidenceLink.claim_id == claim.id).all()
    assert len(rows) == 1
    assert rows[0].id == link.id
    assert rows[0].fragment_id == fragment.id
    assert rows[0].relationship == "originates"


def test_claim_evidence_link_unique_constraint(db_session):
    project = _project(db_session)
    _source, _version, fragment = _source_chain(db_session, project)
    claim = create_claim(
        db_session,
        project_id=project.id,
        minted_by="deterministic_tool",
        truth_layer="observed",
        statement="A service listens on port 8000.",
        claim_type="fact",
        domain="runtime",
        created_by="repository-scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )
    link_evidence(
        db_session, claim_id=claim.id, fragment_id=fragment.id,
        minted_by="deterministic_tool", relationship="originates",
    )

    with pytest.raises(IntegrityError):
        link_evidence(
            db_session, claim_id=claim.id, fragment_id=fragment.id,
            minted_by="deterministic_tool", relationship="originates",
        )
    db_session.rollback()


def test_relate_claims_persists_and_is_queryable(db_session):
    project = _project(db_session)
    claim_a = create_claim(
        db_session, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="A.", claim_type="fact", domain="runtime", created_by="scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )
    claim_b = create_claim(
        db_session, project_id=project.id, minted_by="agent", truth_layer="inferred",
        statement="B.", claim_type="finding", domain="runtime", created_by="genome-classifier",
        derivation={"method": "aggregated", "parent_claim_ids": [claim_a.id]},
    )

    edge = relate_claims(
        db_session, from_claim_id=claim_b.id, to_claim_id=claim_a.id,
        minted_by="agent", relationship="derived_from",
    )

    rows = db_session.query(ClaimRelationship).filter(ClaimRelationship.from_claim_id == claim_b.id).all()
    assert len(rows) == 1
    assert rows[0].id == edge.id
    assert rows[0].to_claim_id == claim_a.id
    assert rows[0].relationship == "derived_from"


def test_claims_project_truth_layer_composite_query(db_session):
    project = _project(db_session)
    create_claim(
        db_session, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="Observed 1.", claim_type="fact", domain="runtime", created_by="scanner",
        derivation={"method": "direct", "parent_claim_ids": []},
    )
    create_claim(
        db_session, project_id=project.id, minted_by="human", truth_layer="claimed",
        statement="Claimed 1.", claim_type="requirement", domain="deployment", created_by="pm",
        derivation={"method": "direct", "parent_claim_ids": []},
    )

    observed = (
        db_session.query(Claim)
        .filter(Claim.project_id == project.id, Claim.truth_layer == "observed")
        .all()
    )
    assert len(observed) == 1
    assert observed[0].statement == "Observed 1."


def test_freeze_corpus_creates_snapshot_and_membership_rows(db_session):
    project = _project(db_session)
    _source, version, _fragment = _source_chain(db_session, project)
    create_claim(
        db_session, project_id=project.id, minted_by="deterministic_tool", truth_layer="observed",
        statement="A service listens on port 8000.", claim_type="fact", domain="runtime",
        created_by="scanner", derivation={"method": "direct", "parent_claim_ids": []},
    )

    snapshot = freeze_corpus(
        db_session, project_id=project.id, source_version_ids=[version.id], purpose="genome_generation",
    )

    assert snapshot.project_id == project.id
    assert snapshot.source_version_ids == [version.id]
    assert snapshot.claim_set_hash is not None

    from aos_core.models import CorpusSnapshotSource

    members = (
        db_session.query(CorpusSnapshotSource)
        .filter(CorpusSnapshotSource.snapshot_id == snapshot.id)
        .all()
    )
    assert len(members) == 1
    assert members[0].source_version_id == version.id
