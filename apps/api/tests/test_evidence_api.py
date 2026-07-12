"""API tests for the Evidence Spine HTTP surface (AOS-EVIDENCE-API-001, RFC-0018).

Thin-wrapper routes over ``services/evidence.py`` — these tests exercise the
HTTP layer (status codes, DTO shape, 422/404/409 mapping), not the guard logic
itself (that is ``test_evidence_guards.py``, at the service level).

Hermetic: the shared ``client`` fixture (sqlite, no network/LLM). A non-approved
-> approved Decision is seeded through the same sqlite file the `client`
fixture uses, mirroring ``test_build_plan.py``'s API-level pattern.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.models import Decision

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def _same_file_session(tmp_path):
    """A session on the same sqlite file the `client` fixture uses, for direct seeding."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _project(client, slug: str = "evidence") -> str:
    return client.post("/projects", json={"name": "Evidence", "slug": slug}).json()["id"]


def _create_source(client, project_id: str, **overrides) -> dict:
    payload = {
        "minted_by": "deterministic_tool",
        "source_type": "repository",
        "title": "control-plane repository",
        "origin": "github",
        "originator": "acme/control-plane",
    }
    payload.update(overrides)
    resp = client.post(f"/projects/{project_id}/sources", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_version(client, source_id: str, **overrides) -> dict:
    payload = {
        "minted_by": "deterministic_tool",
        "version_ref": "v1",
        "content_hash": "a" * 64,
        "ingestion_method": "scan",
    }
    payload.update(overrides)
    resp = client.post(f"/sources/{source_id}/versions", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_fragment(client, version_id: str, **overrides) -> dict:
    payload = {
        "minted_by": "deterministic_tool",
        "content_hash": "b" * 64,
        "excerpt": "The Dockerfile exposes port 8000.",
        "extraction_method": "deterministic",
    }
    payload.update(overrides)
    resp = client.post(f"/source-versions/{version_id}/fragments", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_claim(client, project_id: str, **overrides) -> dict:
    # Default minted_by="human"/truth_layer="claimed": this is the API's normal
    # claim-creation combo (only agent/human may mint through the public route
    # at all — see test_create_claim_rejects_deterministic_tool_minted_by_via_
    # public_route — and human may only mint "claimed", per C3).
    payload = {
        "minted_by": "human",
        "truth_layer": "claimed",
        "statement": "A service listens on port 8000.",
        "claim_type": "fact",
        "domain": "runtime",
        "created_by": "pm",
        "derivation": {"method": "direct", "parent_claim_ids": []},
    }
    payload.update(overrides)
    resp = client.post(f"/projects/{project_id}/claims", json=payload)
    return resp


# ---------------------------------------------------------------------------
# Happy path: source -> version -> fragment -> claim -> link
# ---------------------------------------------------------------------------


def test_source_version_fragment_claim_link_happy_path(client) -> None:
    project_id = _project(client)

    source = _create_source(client, project_id)
    assert source["project_id"] == project_id
    assert source["content_hash"]

    listed_sources = client.get(f"/projects/{project_id}/sources")
    assert listed_sources.status_code == 200
    assert [s["id"] for s in listed_sources.json()] == [source["id"]]

    version = _create_version(client, source["id"])
    assert version["source_id"] == source["id"]

    listed_versions = client.get(f"/sources/{source['id']}/versions")
    assert listed_versions.status_code == 200
    assert [v["id"] for v in listed_versions.json()] == [version["id"]]

    fragment = _create_fragment(client, version["id"])
    assert fragment["source_version_id"] == version["id"]

    claim_resp = _create_claim(client, project_id)
    assert claim_resp.status_code == 200, claim_resp.text
    claim = claim_resp.json()
    assert claim["project_id"] == project_id
    assert claim["truth_layer"] == "claimed"
    assert claim["content_hash"]

    link_resp = client.post(
        f"/claims/{claim['id']}/evidence",
        json={
            "fragment_id": fragment["id"],
            "minted_by": "deterministic_tool",
            "relationship": "supports",
        },
    )
    assert link_resp.status_code == 200, link_resp.text
    link = link_resp.json()
    assert link["claim_id"] == claim["id"]
    assert link["fragment_id"] == fragment["id"]
    assert link["relationship"] == "supports"


def test_create_source_missing_project_404(client) -> None:
    resp = client.post(
        f"/projects/{UNKNOWN_ID}/sources",
        json={
            "minted_by": "deterministic_tool", "source_type": "repository", "title": "x",
            "origin": "github", "originator": "acme/x",
        },
    )
    assert resp.status_code == 404


def test_create_version_missing_source_404(client) -> None:
    resp = client.post(
        f"/sources/{UNKNOWN_ID}/versions",
        json={
            "minted_by": "deterministic_tool", "version_ref": "v1", "content_hash": "a" * 64,
            "ingestion_method": "scan",
        },
    )
    assert resp.status_code == 404


def test_create_fragment_missing_version_404(client) -> None:
    resp = client.post(
        f"/source-versions/{UNKNOWN_ID}/fragments",
        json={
            "minted_by": "deterministic_tool", "content_hash": "b" * 64,
            "excerpt": "x", "extraction_method": "deterministic",
        },
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Claims: list filtered by truth_layer, detail with links + relationships
# ---------------------------------------------------------------------------


def test_list_claims_filtered_by_truth_layer(client) -> None:
    project_id = _project(client)

    claimed = _create_claim(
        client, project_id, minted_by="human", truth_layer="claimed",
        statement="Must not require public cloud connectivity.", claim_type="requirement",
        created_by="pm",
    ).json()
    inferred = _create_claim(
        client, project_id, minted_by="agent", truth_layer="inferred",
        statement="Inferred: a lockfile plus a Dockerfile implies this service exists.",
        claim_type="finding", created_by="genome-classifier",
    ).json()

    all_claims = client.get(f"/projects/{project_id}/claims")
    assert all_claims.status_code == 200
    assert {c["id"] for c in all_claims.json()} == {claimed["id"], inferred["id"]}

    only_claimed = client.get(f"/projects/{project_id}/claims", params={"truth_layer": "claimed"})
    assert only_claimed.status_code == 200
    assert [c["id"] for c in only_claimed.json()] == [claimed["id"]]


def test_claim_detail_includes_evidence_links_and_relationships(client) -> None:
    project_id = _project(client)
    source = _create_source(client, project_id)
    version = _create_version(client, source["id"])
    fragment = _create_fragment(client, version["id"])

    claim_a = _create_claim(client, project_id, statement="Claim A.").json()
    claim_b = _create_claim(
        client, project_id, minted_by="human", truth_layer="claimed",
        statement="Claim B.", claim_type="requirement", created_by="pm",
    ).json()

    client.post(
        f"/claims/{claim_a['id']}/evidence",
        json={"fragment_id": fragment["id"], "minted_by": "deterministic_tool", "relationship": "supports"},
    )
    rel_resp = client.post(
        f"/claims/{claim_a['id']}/relationships",
        json={"to_claim_id": claim_b["id"], "minted_by": "agent", "relationship": "supports"},
    )
    assert rel_resp.status_code == 200, rel_resp.text

    detail = client.get(f"/claims/{claim_a['id']}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["id"] == claim_a["id"]
    assert len(body["evidence_links"]) == 1
    assert body["evidence_links"][0]["fragment_id"] == fragment["id"]
    assert len(body["relationships"]) == 1
    assert body["relationships"][0]["to_claim_id"] == claim_b["id"]

    # And the relationship is also visible from the other side (from OR to).
    detail_b = client.get(f"/claims/{claim_b['id']}")
    assert detail_b.status_code == 200
    assert len(detail_b.json()["relationships"]) == 1


def test_get_claim_missing_404(client) -> None:
    resp = client.get(f"/claims/{UNKNOWN_ID}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# C3 over HTTP: minted_by=agent + truth_layer=observed -> 422
# ---------------------------------------------------------------------------


def test_create_claim_c3_agent_cannot_mint_observed_422(client) -> None:
    project_id = _project(client)
    resp = _create_claim(
        client, project_id, minted_by="agent", truth_layer="observed",
        statement="An agent tries to assert an observed fact.", created_by="some-agent",
    )
    assert resp.status_code == 422, resp.text
    assert "C3" in resp.json()["detail"]


def test_create_claim_rejects_deterministic_tool_minted_by_via_public_route(client) -> None:
    # minted_by=deterministic_tool is reserved for internal scanners/backfill
    # calling services/evidence.py directly, never the public HTTP route.
    project_id = _project(client)
    resp = _create_claim(client, project_id, minted_by="deterministic_tool", truth_layer="observed")
    assert resp.status_code == 422, resp.text
    assert "deterministic_tool" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# C1 over HTTP: project-claim on non-approved -> 409, on approved -> claim
# ---------------------------------------------------------------------------


def test_project_decided_claim_non_approved_decision_409(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        decision = Decision(project_id=project_id, title="Draft decision", status="draft")
        session.add(decision)
        session.commit()
        decision_id = decision.id
    finally:
        session.close()

    resp = client.post(f"/decisions/{decision_id}/project-claim")
    assert resp.status_code == 409, resp.text


def test_project_decided_claim_approved_decision_returns_decided_claim(client, tmp_path) -> None:
    project_id = _project(client)
    session = _same_file_session(tmp_path)
    try:
        decision = Decision(
            project_id=project_id, title="Adopt local-first deployment", status="approved",
            decision="Adopt a local-first deployment model.", confidence=0.9,
            approved_by="operator@example.com",
        )
        session.add(decision)
        session.commit()
        decision_id = decision.id
    finally:
        session.close()

    resp = client.post(f"/decisions/{decision_id}/project-claim")
    assert resp.status_code == 200, resp.text
    claim = resp.json()
    assert claim["truth_layer"] == "decided"
    assert claim["minted_by"] == "approval_process"
    assert claim["decision_id"] == decision_id


def test_project_decided_claim_missing_decision_404(client) -> None:
    resp = client.post(f"/decisions/{UNKNOWN_ID}/project-claim")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Conflicts: open then resolve via PATCH
# ---------------------------------------------------------------------------


def test_open_and_resolve_conflict(client) -> None:
    project_id = _project(client)
    claim_a = _create_claim(client, project_id, statement="Observed: no cloud egress.").json()
    claim_b = _create_claim(
        client, project_id, minted_by="human", truth_layer="claimed",
        statement="Required: must not require public cloud connectivity.", claim_type="requirement",
        created_by="pm",
    ).json()

    open_resp = client.post(
        f"/projects/{project_id}/conflicts",
        json={
            "claim_ids": [claim_a["id"], claim_b["id"]],
            "minted_by": "agent",
            "conflict_type": "implementation_drift",
            "materiality": "high",
            "blocking_stages": ["foundation_selection"],
        },
    )
    assert open_resp.status_code == 200, open_resp.text
    conflict = open_resp.json()
    assert conflict["status"] == "open"

    listed = client.get(f"/projects/{project_id}/conflicts")
    assert listed.status_code == 200
    assert [c["id"] for c in listed.json()] == [conflict["id"]]

    resolve_resp = client.patch(
        f"/conflicts/{conflict['id']}",
        json={"status": "resolved", "resolution": "Adopted the offline requirement."},
    )
    assert resolve_resp.status_code == 200, resolve_resp.text
    resolved = resolve_resp.json()
    assert resolved["status"] == "resolved"
    assert resolved["resolution"] == "Adopted the offline requirement."


def test_resolve_conflict_invalid_status_422(client) -> None:
    project_id = _project(client)
    claim_a = _create_claim(client, project_id, statement="Claim A.").json()

    open_resp = client.post(
        f"/projects/{project_id}/conflicts",
        json={
            "claim_ids": [claim_a["id"]], "minted_by": "agent",
            "conflict_type": "ambiguity", "materiality": "low",
        },
    )
    conflict_id = open_resp.json()["id"]

    resp = client.patch(
        f"/conflicts/{conflict_id}", json={"status": "open", "resolution": "no-op"}
    )
    assert resp.status_code == 422, resp.text


def test_resolve_conflict_missing_404(client) -> None:
    resp = client.patch(
        f"/conflicts/{UNKNOWN_ID}", json={"status": "resolved", "resolution": "n/a"}
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Corpus snapshots
# ---------------------------------------------------------------------------


def test_freeze_and_get_corpus_snapshot(client) -> None:
    project_id = _project(client)
    source = _create_source(client, project_id)
    version = _create_version(client, source["id"])
    _create_claim(client, project_id)

    freeze_resp = client.post(
        f"/projects/{project_id}/corpus-snapshots",
        json={"source_version_ids": [version["id"]], "purpose": "genome_generation"},
    )
    assert freeze_resp.status_code == 200, freeze_resp.text
    snapshot = freeze_resp.json()
    assert snapshot["project_id"] == project_id
    assert snapshot["claim_set_hash"]

    listed = client.get(f"/projects/{project_id}/corpus-snapshots")
    assert listed.status_code == 200
    assert [s["id"] for s in listed.json()] == [snapshot["id"]]


def test_corpus_snapshot_missing_project_404(client) -> None:
    resp = client.post(
        f"/projects/{UNKNOWN_ID}/corpus-snapshots",
        json={"source_version_ids": [], "purpose": "genome_generation"},
    )
    assert resp.status_code == 404
