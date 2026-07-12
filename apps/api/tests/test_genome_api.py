"""API tests for the System Genome HTTP surface (AOS-GENOME-API-001, RFC-0019 §16).

Thin-wrapper routes over ``services/genome.py`` — these tests exercise the
HTTP layer (status codes, DTO shape, 422/404/409 mapping), not the derivation
rules themselves (that is ``test_genome_rules.py``/``test_genome.py``, at the
service level).

Hermetic: the shared ``client`` fixture (sqlite, no network/LLM). Claims are
seeded through the Evidence Spine HTTP API (``/projects/{id}/claims``), mirroring
how ``test_evidence_api.py`` seeds its fixtures.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def _same_file_session(tmp_path):
    """A session on the same sqlite file the `client` fixture uses, for direct seeding.

    Mirrors ``test_evidence_api.py``'s ``_same_file_session`` helper: only
    ``deterministic_tool`` may mint ``observed`` claims (C3, ``foundation.
    truth.may_mint``), and the public ``/claims`` route rejects
    ``minted_by=deterministic_tool`` outright (it's reserved for internal
    scanners/backfill) — so seeding an ``observed`` claim set for a
    ``state_view=current`` genome requires writing the row directly, exactly
    like ``test_project_decided_claim_*`` seeds a ``Decision`` directly.
    """
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _project(client, slug: str = "genome") -> str:
    return client.post("/projects", json={"name": "Genome", "slug": slug}).json()["id"]


def _create_claim(client, project_id: str, **overrides) -> dict:
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
    assert resp.status_code == 200, resp.text
    return resp.json()


def _seed_observed_claims(tmp_path, project_id: str) -> None:
    """Seed ``observed`` claims (fire the seed rules for a ``state_view=current``
    genome) directly via the db, bypassing the guarded public ``/claims`` route."""
    import aos_core.models  # noqa: F401 — register every table on Base.metadata (LES-L10)
    from aos_core.models import Claim

    session = _same_file_session(tmp_path)
    try:
        session.add_all(
            [
                Claim(
                    project_id=project_id,
                    statement="The system runs distributed background workers via a message broker.",
                    claim_type="fact",
                    truth_layer="observed",
                    domain="runtime",
                    minted_by="deterministic_tool",
                    derivation={"method": "scan", "parent_claim_ids": []},
                    confidence=0.9,
                    created_by="scanner",
                ),
                Claim(
                    project_id=project_id,
                    statement="The deployment must be local-first with no public cloud dependency.",
                    claim_type="fact",
                    truth_layer="observed",
                    domain="deployment",
                    minted_by="deterministic_tool",
                    derivation={"method": "scan", "parent_claim_ids": []},
                    confidence=0.9,
                    created_by="scanner",
                ),
                Claim(
                    project_id=project_id,
                    statement="An autonomous agent drives the build pipeline.",
                    claim_type="fact",
                    truth_layer="observed",
                    domain="architecture",
                    minted_by="deterministic_tool",
                    derivation={"method": "scan", "parent_claim_ids": []},
                    confidence=0.9,
                    created_by="scanner",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()


def _seed_claims(client, project_id: str) -> None:
    # Fires: runtime_topology/distributed_workers (domain=runtime, "worker"
    # keyword), deployment_ownership/local_first ("local-first" keyword, any
    # domain), ai_autonomy/agentic ("agent" keyword, any domain) — enough to
    # roll up all three seed archetypes (services/genome.py:_derive_archetypes).
    _create_claim(
        client, project_id, statement="The system runs distributed background workers via a message broker.",
        domain="runtime", claim_type="fact",
    )
    _create_claim(
        client, project_id, statement="The deployment must be local-first with no public cloud dependency.",
        domain="deployment", claim_type="requirement",
    )
    _create_claim(
        client, project_id, statement="An autonomous agent drives the build pipeline.",
        domain="architecture", claim_type="fact",
    )


def _generate(client, project_id: str, state_view: str = "current", **overrides) -> dict:
    payload = {"state_view": state_view}
    payload.update(overrides)
    resp = client.post(f"/projects/{project_id}/genomes/generate", json=payload)
    return resp


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------


def test_generate_current_and_intended_genomes(client) -> None:
    project_id = _project(client)
    _seed_claims(client, project_id)

    current_resp = _generate(client, project_id, state_view="current")
    assert current_resp.status_code == 200, current_resp.text
    current = current_resp.json()
    assert current["project_id"] == project_id
    assert current["state_view"] == "current"
    assert current["status"] == "draft"
    assert current["version"] == 1

    intended_resp = _generate(client, project_id, state_view="intended")
    assert intended_resp.status_code == 200, intended_resp.text
    intended = intended_resp.json()
    assert intended["state_view"] == "intended"


def test_generate_missing_project_404(client) -> None:
    resp = _generate(client, UNKNOWN_ID)
    assert resp.status_code == 404


def test_generate_unsupported_state_view_422(client) -> None:
    project_id = _project(client)
    resp = _generate(client, project_id, state_view="target")
    assert resp.status_code == 422, resp.text
    assert "target" in resp.json()["detail"]

    resp_candidate = _generate(client, project_id, state_view="candidate")
    assert resp_candidate.status_code == 422, resp_candidate.text


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_genomes_filtered_by_state_view(client) -> None:
    project_id = _project(client)
    _seed_claims(client, project_id)
    current = _generate(client, project_id, state_view="current").json()
    intended = _generate(client, project_id, state_view="intended").json()

    all_genomes = client.get(f"/projects/{project_id}/genomes")
    assert all_genomes.status_code == 200
    assert {g["id"] for g in all_genomes.json()} == {current["id"], intended["id"]}

    only_current = client.get(f"/projects/{project_id}/genomes", params={"state_view": "current"})
    assert only_current.status_code == 200
    assert [g["id"] for g in only_current.json()] == [current["id"]]


def test_list_genomes_missing_project_404(client) -> None:
    resp = client.get(f"/projects/{UNKNOWN_ID}/genomes")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Detail (traits + archetypes)
# ---------------------------------------------------------------------------


def test_genome_detail_includes_traits_and_archetypes(client, tmp_path) -> None:
    project_id = _project(client)
    _seed_observed_claims(tmp_path, project_id)
    genome = _generate(client, project_id, state_view="current").json()

    detail_resp = client.get(f"/genomes/{genome['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    assert detail["id"] == genome["id"]
    assert len(detail["traits"]) > 0
    # Every foundation-shaping dimension gets a trait row (evidence-backed or
    # an explicit "unknown") — at least one of the seeded rules should fire
    # with supporting claim ids attached.
    fired = [t for t in detail["traits"] if t["classification"] != "unknown"]
    assert fired
    assert any(t["supporting_claim_ids"] for t in fired)
    assert len(detail["archetypes"]) > 0


def test_get_genome_missing_404(client) -> None:
    resp = client.get(f"/genomes/{UNKNOWN_ID}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Review / approve
# ---------------------------------------------------------------------------


def test_review_then_approve_genome(client) -> None:
    project_id = _project(client)
    _seed_claims(client, project_id)
    genome = _generate(client, project_id, state_view="current").json()

    review_resp = client.post(f"/genomes/{genome['id']}/review", json={"reviewer": "operator@example.com"})
    assert review_resp.status_code == 200, review_resp.text
    reviewed = review_resp.json()
    assert reviewed["status"] == "reviewed"

    approve_resp = client.post(
        f"/genomes/{genome['id']}/approve", json={"approver": "operator@example.com", "rationale": "Looks good."}
    )
    assert approve_resp.status_code == 200, approve_resp.text
    approved = approve_resp.json()
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "operator@example.com"


def test_approve_before_review_409(client) -> None:
    project_id = _project(client)
    _seed_claims(client, project_id)
    genome = _generate(client, project_id, state_view="current").json()

    resp = client.post(f"/genomes/{genome['id']}/approve", json={"approver": "operator@example.com"})
    assert resp.status_code == 409, resp.text


def test_review_missing_genome_404(client) -> None:
    resp = client.post(f"/genomes/{UNKNOWN_ID}/review", json={"reviewer": "operator@example.com"})
    assert resp.status_code == 404


def test_approve_missing_genome_404(client) -> None:
    resp = client.post(f"/genomes/{UNKNOWN_ID}/approve", json={"approver": "operator@example.com"})
    assert resp.status_code == 404


def test_review_already_reviewed_409(client) -> None:
    project_id = _project(client)
    _seed_claims(client, project_id)
    genome = _generate(client, project_id, state_view="current").json()
    client.post(f"/genomes/{genome['id']}/review", json={"reviewer": "operator@example.com"})

    resp = client.post(f"/genomes/{genome['id']}/review", json={"reviewer": "operator@example.com"})
    assert resp.status_code == 409, resp.text


# ---------------------------------------------------------------------------
# Open questions
# ---------------------------------------------------------------------------


def test_list_genome_questions(client) -> None:
    project_id = _project(client)
    _seed_claims(client, project_id)
    genome = _generate(client, project_id, state_view="current").json()

    resp = client.get(f"/genomes/{genome['id']}/questions")
    assert resp.status_code == 200, resp.text
    questions = resp.json()
    # Every foundation-shaping dimension without a confident firing rule
    # produces an OpenQuestion (design §7) — several of the 6 seed dimensions
    # have no evidence in this claim set.
    assert len(questions) > 0
    assert all(q["genome_snapshot_id"] == genome["id"] for q in questions)


def test_list_genome_questions_missing_genome_404(client) -> None:
    resp = client.get(f"/genomes/{UNKNOWN_ID}/questions")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------


def test_compare_genomes_returns_delta(client) -> None:
    project_id = _project(client)
    _seed_claims(client, project_id)
    current = _generate(client, project_id, state_view="current").json()
    intended = _generate(client, project_id, state_view="intended").json()

    resp = client.post(f"/genomes/{current['id']}/compare/{intended['id']}")
    assert resp.status_code == 200, resp.text
    delta = resp.json()
    assert delta["from_snapshot_id"] == current["id"]
    assert delta["to_snapshot_id"] == intended["id"]
    assert "changes" in delta
    assert "coverage_delta" in delta["changes"]


def test_compare_genomes_missing_snapshot_404(client) -> None:
    project_id = _project(client)
    _seed_claims(client, project_id)
    genome = _generate(client, project_id, state_view="current").json()

    resp = client.post(f"/genomes/{genome['id']}/compare/{UNKNOWN_ID}")
    assert resp.status_code == 404
