"""API tests for the multi-phase research-plan endpoints (AOS-RESEARCH-003)."""

from __future__ import annotations


def test_create_and_read_research_plan(client):
    project_id = client.post("/projects", json={"name": "Recall"}).json()["id"]

    resp = client.post(
        f"/projects/{project_id}/research-plans",
        json={"question": "best vector database for local memory", "sensitivity": "public"},
    )
    assert resp.status_code == 201
    plan = resp.json()
    assert plan["project_id"] == project_id
    assert plan["question"] == "best vector database for local memory"
    assert plan["plan_status"] == "planned"
    # The plan records its search queries + verification + policy BEFORE any fetch.
    assert plan["search_queries"]
    assert plan["verification_steps"]
    assert plan["synthesis_policy"]["cite_sources"] is True
    assert plan["synthesis_policy"]["record_open_questions"] is True

    # Detail round-trips.
    detail = client.get(f"/research-plans/{plan['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == plan["id"]

    # List returns it under the project.
    listing = client.get(f"/projects/{project_id}/research-plans")
    assert listing.status_code == 200
    ids = [row["id"] for row in listing.json()]
    assert plan["id"] in ids


def test_create_research_plan_unknown_project_404(client):
    resp = client.post(
        "/projects/00000000-0000-0000-0000-000000000000/research-plans",
        json={"question": "anything"},
    )
    assert resp.status_code == 404


def test_create_research_plan_rejects_empty_question(client):
    project_id = client.post("/projects", json={"name": "Recall"}).json()["id"]
    resp = client.post(f"/projects/{project_id}/research-plans", json={"question": "   "})
    assert resp.status_code == 422


def test_create_research_plan_rejects_unknown_sensitivity(client):
    project_id = client.post("/projects", json={"name": "Recall"}).json()["id"]
    resp = client.post(
        f"/projects/{project_id}/research-plans",
        json={"question": "q", "sensitivity": "top-secret"},
    )
    assert resp.status_code == 422


def test_get_research_plan_unknown_404(client):
    resp = client.get("/research-plans/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
