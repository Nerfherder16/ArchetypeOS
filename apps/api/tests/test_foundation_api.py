"""API tests for the Foundation Intelligence HTTP surface (AOS-FOUNDATION-API-001,
RFC-0020 design §16).

Thin-wrapper routes over ``services/foundation.py`` — these tests exercise the
HTTP layer (status codes, DTO shape, 404/409/422 mapping) by walking the full
run: open-run -> compile-requirements -> generate-candidates ->
evaluate-eligibility -> score. Not the derivation rules themselves (that is
``test_foundation_engine.py``, at the service level, whose fixture this
mirrors: a runtime observed fact + a deployment hard-constraint claim).

Hermetic: the shared ``client`` fixture (sqlite, no network/LLM). Claims are
seeded through the Evidence Spine HTTP API where the public route allows it
(``human``-minted ``claimed``), and directly via the db where it doesn't
(``deterministic_tool``-minted ``observed`` — mirrors ``test_genome_api.py``'s
``_seed_observed_claims``/``_same_file_session`` helpers exactly, since the
public ``/claims`` route rejects ``minted_by=deterministic_tool`` outright).
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def _same_file_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _project(client, slug: str = "foundation") -> str:
    return client.post("/projects", json={"name": "Foundation", "slug": slug}).json()["id"]


def _seed_observed_runtime_claim(tmp_path, project_id: str) -> None:
    """A runtime ``observed`` fact (fires a foundation-shaping required_capability
    trait, RFC-0020's ``compile_hard_constraints_from_claims``/
    ``compile_capabilities_from_foundation_shaping_traits`` rules) — minted by
    ``deterministic_tool``, so seeded directly (public route forbids it)."""
    import aos_core.models  # noqa: F401 — register every table on Base.metadata (LES-L10)
    from aos_core.models import Claim

    session = _same_file_session(tmp_path)
    try:
        session.add(
            Claim(
                project_id=project_id,
                statement="A worker process pulls jobs from a message queue.",
                claim_type="fact",
                truth_layer="observed",
                domain="runtime",
                minted_by="deterministic_tool",
                derivation={"method": "direct", "parent_claim_ids": []},
                confidence=0.9,
                created_by="repository-scanner",
            )
        )
        session.commit()
    finally:
        session.close()


def _seed_deployment_constraint_claim(client, project_id: str) -> str:
    payload = {
        "minted_by": "human",
        "truth_layer": "claimed",
        "statement": "The deployment environment must not use a public cloud provider.",
        "claim_type": "constraint",
        "domain": "deployment",
        "created_by": "product manager",
        "derivation": {"method": "direct", "parent_claim_ids": []},
    }
    resp = client.post(f"/projects/{project_id}/claims", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _generate_genome(client, project_id: str) -> dict:
    resp = client.post(f"/projects/{project_id}/genomes/generate", json={"state_view": "current"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _setup_run_with_hard_constraint(client, tmp_path, slug: str = "foundation") -> tuple[str, dict]:
    """Mirrors ``test_foundation_engine.py``'s ``_setup_run_with_hard_constraint``
    over HTTP: a project with a runtime observed fact + a deployment
    hard-constraint claim, genome generated, run opened. Returns
    ``(project_id, run)`` with requirements not yet compiled."""
    project_id = _project(client, slug)
    _seed_observed_runtime_claim(tmp_path, project_id)
    _seed_deployment_constraint_claim(client, project_id)
    genome = _generate_genome(client, project_id)

    resp = client.post(
        f"/projects/{project_id}/foundation-runs",
        json={"target_genome_snapshot_id": genome["id"]},
    )
    assert resp.status_code == 200, resp.text
    return project_id, resp.json()


def _compile(client, run_id: str):
    return client.post(f"/foundation-runs/{run_id}/compile-requirements", json={})


def _generate_candidates(client, run_id: str):
    return client.post(f"/foundation-runs/{run_id}/generate-candidates", json={})


def _evaluate_eligibility(client, run_id: str):
    return client.post(f"/foundation-runs/{run_id}/evaluate-eligibility", json={})


def _score(client, candidate_id: str):
    return client.post(f"/candidates/{candidate_id}/score", json={})


# ---------------------------------------------------------------------------
# Open run
# ---------------------------------------------------------------------------


def test_open_foundation_run(client, tmp_path) -> None:
    project_id, run = _setup_run_with_hard_constraint(client, tmp_path)
    assert run["project_id"] == project_id
    assert run["state"] == "draft"
    assert run["version"] == 1


def test_open_foundation_run_missing_project_404(client) -> None:
    resp = client.post(
        f"/projects/{UNKNOWN_ID}/foundation-runs",
        json={"target_genome_snapshot_id": UNKNOWN_ID},
    )
    assert resp.status_code == 404


def test_open_foundation_run_missing_genome_404(client) -> None:
    project_id = _project(client)
    resp = client.post(
        f"/projects/{project_id}/foundation-runs",
        json={"target_genome_snapshot_id": UNKNOWN_ID},
    )
    assert resp.status_code == 404


def test_open_foundation_run_second_active_run_409(client, tmp_path) -> None:
    project_id, run = _setup_run_with_hard_constraint(client, tmp_path)
    resp = client.post(
        f"/projects/{project_id}/foundation-runs",
        json={"target_genome_snapshot_id": run["target_genome_snapshot_id"]},
    )
    assert resp.status_code == 409, resp.text


# ---------------------------------------------------------------------------
# Full walk: compile -> generate -> evaluate -> score
# ---------------------------------------------------------------------------


def test_full_run_walk_scores_an_eligible_candidate(client, tmp_path) -> None:
    project_id, run = _setup_run_with_hard_constraint(client, tmp_path)

    compile_resp = _compile(client, run["id"])
    assert compile_resp.status_code == 200, compile_resp.text
    requirements = compile_resp.json()
    assert requirements
    hard = [r for r in requirements if r["requirement_type"] == "hard_constraint"]
    assert len(hard) == 1
    assert hard[0]["domain"] == "deployment"
    assert hard[0]["veto_if_unsatisfied"] is True

    generate_resp = _generate_candidates(client, run["id"])
    assert generate_resp.status_code == 200, generate_resp.text
    candidates = generate_resp.json()
    assert len(candidates) >= 2

    eligibility_resp = _evaluate_eligibility(client, run["id"])
    assert eligibility_resp.status_code == 200, eligibility_resp.text
    reviewed = eligibility_resp.json()
    assert all(c["status"] == "eligible" for c in reviewed)
    assert all(c["hard_constraint_violations"] == [] for c in reviewed)

    eligible_candidate_id = reviewed[0]["id"]
    score_resp = _score(client, eligible_candidate_id)
    assert score_resp.status_code == 200, score_resp.text
    scored = score_resp.json()
    assert scored["score_summary"]["vector_shape"] == "per_criterion"
    assert scored["score_summary"]["criteria"]
    for entry in scored["score_summary"]["criteria"]:
        assert "adjusted_score" in entry
        assert "uncertainty_penalty" in entry


def test_score_rejected_candidate_409(client, tmp_path) -> None:
    project_id, run = _setup_run_with_hard_constraint(client, tmp_path)
    _compile(client, run["id"])
    _generate_candidates(client, run["id"])

    # Manually author a candidate whose deployment element affirmatively
    # violates the hard constraint (mirrors test_foundation_engine.py's
    # violator fixture).
    candidate_resp = client.post(
        f"/foundation-runs/{run['id']}/candidates",
        json={"name": "Cloud-Violating Alternative"},
    )
    assert candidate_resp.status_code == 200, candidate_resp.text
    candidate_id = candidate_resp.json()["id"]

    element_resp = client.post(
        f"/candidates/{candidate_id}/elements",
        json={
            "domain": "deployment",
            "title": "Deployment approach (violating)",
            "decision": "Deploy directly to a public cloud provider using managed Kubernetes for elasticity.",
            "verification_method": "none",
        },
    )
    assert element_resp.status_code == 200, element_resp.text

    eligibility_resp = _evaluate_eligibility(client, run["id"])
    assert eligibility_resp.status_code == 200, eligibility_resp.text
    reviewed = eligibility_resp.json()
    by_id = {c["id"]: c for c in reviewed}
    assert by_id[candidate_id]["status"] == "rejected"
    assert by_id[candidate_id]["hard_constraint_violations"]

    score_resp = _score(client, candidate_id)
    assert score_resp.status_code == 409, score_resp.text


def test_score_before_eligibility_is_409_illegal_transition_or_not_eligible(client, tmp_path) -> None:
    # A draft candidate (never run through evaluate-eligibility) is not
    # 'eligible' either -> AD-8's 409, exercised without the eligibility step.
    project_id, run = _setup_run_with_hard_constraint(client, tmp_path)
    _compile(client, run["id"])
    candidate_resp = client.post(f"/foundation-runs/{run['id']}/candidates", json={"name": "Unreviewed"})
    candidate_id = candidate_resp.json()["id"]

    resp = _score(client, candidate_id)
    assert resp.status_code == 409, resp.text


def test_compile_requirements_missing_run_404(client) -> None:
    resp = _compile(client, UNKNOWN_ID)
    assert resp.status_code == 404


def test_generate_candidates_missing_run_404(client) -> None:
    resp = _generate_candidates(client, UNKNOWN_ID)
    assert resp.status_code == 404


def test_evaluate_eligibility_missing_run_404(client) -> None:
    resp = _evaluate_eligibility(client, UNKNOWN_ID)
    assert resp.status_code == 404


def test_score_missing_candidate_404(client) -> None:
    resp = _score(client, UNKNOWN_ID)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Detail views
# ---------------------------------------------------------------------------


def test_list_foundation_runs(client, tmp_path) -> None:
    project_id, run = _setup_run_with_hard_constraint(client, tmp_path)
    resp = client.get(f"/projects/{project_id}/foundation-runs")
    assert resp.status_code == 200, resp.text
    runs = resp.json()
    assert [r["id"] for r in runs] == [run["id"]]


def test_list_foundation_runs_missing_project_404(client) -> None:
    resp = client.get(f"/projects/{UNKNOWN_ID}/foundation-runs")
    assert resp.status_code == 404


def test_get_run_detail_includes_requirements_and_candidates(client, tmp_path) -> None:
    project_id, run = _setup_run_with_hard_constraint(client, tmp_path)
    _compile(client, run["id"])
    _generate_candidates(client, run["id"])

    resp = client.get(f"/foundation-runs/{run['id']}")
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["id"] == run["id"]
    assert len(detail["requirements"]) > 0
    assert len(detail["candidates"]) > 0


def test_get_run_missing_404(client) -> None:
    resp = client.get(f"/foundation-runs/{UNKNOWN_ID}")
    assert resp.status_code == 404


def test_get_candidate_detail_includes_elements_and_score_vector(client, tmp_path) -> None:
    project_id, run = _setup_run_with_hard_constraint(client, tmp_path)
    _compile(client, run["id"])
    _generate_candidates(client, run["id"])
    reviewed = _evaluate_eligibility(client, run["id"]).json()
    candidate_id = reviewed[0]["id"]
    _score(client, candidate_id)

    resp = client.get(f"/candidates/{candidate_id}")
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["id"] == candidate_id
    assert len(detail["elements"]) > 0
    assert len(detail["scores"]) > 0
    assert {s["criterion"] for s in detail["scores"]}


def test_get_candidate_missing_404(client) -> None:
    resp = client.get(f"/candidates/{UNKNOWN_ID}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Manual authoring
# ---------------------------------------------------------------------------


def test_create_candidate_missing_run_404(client) -> None:
    resp = client.post(f"/foundation-runs/{UNKNOWN_ID}/candidates", json={"name": "X"})
    assert resp.status_code == 404


def test_add_element_missing_candidate_404(client) -> None:
    resp = client.post(
        f"/candidates/{UNKNOWN_ID}/elements",
        json={
            "domain": "runtime",
            "title": "T",
            "decision": "D",
            "verification_method": "review",
        },
    )
    assert resp.status_code == 404
