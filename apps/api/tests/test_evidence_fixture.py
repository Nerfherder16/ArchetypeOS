"""RFC-0018 §20 fixture — the MVP acceptance scenario loads through services/evidence.py.

``foundation/fixtures/mvp_scenario.json`` is the design's §20 MVP acceptance
seed. This test replays its evidence-domain sections (sources, source
versions, fragments, claims, claim_evidence_links, evidence_conflicts,
corpus_snapshots — the Slice 1 scope; genome_snapshots/genome_traits/
foundation_requirements are later slices and are intentionally NOT loaded
here) through ``services/evidence.py`` — the only write path — and asserts the
expected rows exist: every source, one claim per truth layer bucket, and the
one open conflict.

Hermetic: sqlite ``create_all`` via the shared ``db_session`` fixture; the
fixture JSON is read from disk but no network/LLM is used.
"""

from __future__ import annotations

import json
from pathlib import Path

from aos_core.models import Claim, EvidenceConflict, EvidenceFragment, EvidenceSource, EvidenceSourceVersion, Project
from aos_core.services.evidence import (
    add_fragment,
    add_source_version,
    create_claim,
    create_source,
    link_evidence,
    open_conflict,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "packages" / "aos_core" / "aos_core" / "foundation" / "fixtures" / "mvp_scenario.json"
)


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def test_mvp_scenario_fixture_loads_through_evidence_service(db_session):
    fixture = _load_fixture()

    project = Project(name="MVP Scenario", slug="mvp-scenario")
    db_session.add(project)
    db_session.commit()

    source_ids: dict[str, str] = {}
    for src in fixture["evidence_sources"]:
        row = create_source(
            db_session,
            project_id=project.id,
            minted_by=src["minted_by"],
            source_type=src["source_type"],
            title=src["title"],
            origin=src["origin"],
            originator=src["originator"],
            canonical_uri=src.get("canonical_uri"),
            sensitivity=src.get("sensitivity", "internal"),
            authority_domains=src.get("authority_domains", []),
            status=src.get("status", "active"),
        )
        source_ids[src["id"]] = row.id

    version_ids: dict[str, str] = {}
    for ver in fixture["evidence_source_versions"]:
        row = add_source_version(
            db_session,
            source_id=source_ids[ver["source_id"]],
            minted_by=ver["minted_by"],
            version_ref=ver["version_ref"],
            content_hash=ver["content_hash"],
            ingestion_method=ver["ingestion_method"],
            parser_version=ver.get("parser_version"),
        )
        version_ids[ver["id"]] = row.id

    fragment_ids: dict[str, str] = {}
    for frag in fixture["evidence_fragments"]:
        row = add_fragment(
            db_session,
            source_version_id=version_ids[frag["source_version_id"]],
            minted_by=frag["minted_by"],
            content_hash=frag["content_hash"],
            excerpt=frag["excerpt"],
            extraction_method=frag["extraction_method"],
            extraction_confidence=frag.get("extraction_confidence", 0.0),
            locator=frag.get("locator", {}),
        )
        fragment_ids[frag["id"]] = row.id

    claim_ids: dict[str, str] = {}
    for claim in fixture["claims"]:
        row = create_claim(
            db_session,
            project_id=project.id,
            minted_by=claim["minted_by"],
            truth_layer=claim["truth_layer"],
            statement=claim["statement"],
            claim_type=claim["claim_type"],
            domain=claim["domain"],
            created_by=claim["created_by"],
            derivation=claim["derivation"],
            scope=claim.get("scope", {}),
            polarity=claim.get("polarity", "affirming"),
            confidence=claim.get("confidence", 1.0),
            materiality=claim.get("materiality", "medium"),
        )
        claim_ids[claim["id"]] = row.id

    for link in fixture["claim_evidence_links"]:
        link_evidence(
            db_session,
            claim_id=claim_ids[link["claim_id"]],
            fragment_id=fragment_ids[link["fragment_id"]],
            minted_by=link["minted_by"],
            relationship=link["relationship"],
            relevance=link.get("relevance", 1.0),
            strength=link.get("strength", "moderate"),
        )

    for conflict in fixture["evidence_conflicts"]:
        open_conflict(
            db_session,
            project_id=project.id,
            claim_ids=[claim_ids[cid] for cid in conflict["claim_ids"]],
            minted_by=conflict["minted_by"],
            conflict_type=conflict["conflict_type"],
            materiality=conflict["materiality"],
            blocking_stages=conflict.get("blocking_stages", []),
        )

    # --- assertions: the expected rows exist ---------------------------------

    assert db_session.query(EvidenceSource).filter(EvidenceSource.project_id == project.id).count() == len(
        fixture["evidence_sources"]
    )
    assert db_session.query(EvidenceSourceVersion).count() == len(fixture["evidence_source_versions"])
    assert db_session.query(EvidenceFragment).count() == len(fixture["evidence_fragments"])

    claims = db_session.query(Claim).filter(Claim.project_id == project.id).all()
    assert len(claims) == len(fixture["claims"])
    by_layer: dict[str, int] = {}
    for c in claims:
        by_layer[c.truth_layer] = by_layer.get(c.truth_layer, 0) + 1
    expected_by_layer: dict[str, int] = {}
    for claim in fixture["claims"]:
        expected_by_layer[claim["truth_layer"]] = expected_by_layer.get(claim["truth_layer"], 0) + 1
    assert by_layer == expected_by_layer
    assert by_layer["observed"] == 2
    assert by_layer["claimed"] == 2
    assert by_layer["inferred"] == 1

    conflicts = db_session.query(EvidenceConflict).filter(EvidenceConflict.project_id == project.id).all()
    assert len(conflicts) == 1
    assert conflicts[0].status == "open"
    assert set(conflicts[0].claim_ids) == {
        claim_ids["claim-observed-cloud-egress"], claim_ids["claim-requirement-offline"]
    }
