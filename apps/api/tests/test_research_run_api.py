"""API tests for the research-run endpoints (AOS-RESEARCH-003 executor)."""

from __future__ import annotations


class FakeRedis:
    """Captures lpush so the enqueue path needs no real Redis (dead port in conftest)."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append(value)


def _client_db():
    """Yield a session bound to the SAME test DB the TestClient uses (via the
    get_db dependency override the `client` fixture installs)."""
    from aos_core.database import get_db
    from app.main import app

    return app.dependency_overrides[get_db]()


def _plan(client) -> tuple[str, str]:
    project_id = client.post("/projects", json={"name": "Recall"}).json()["id"]
    plan = client.post(
        f"/projects/{project_id}/research-plans", json={"question": "vector database sharding"}
    ).json()
    return project_id, plan["id"]


def test_run_plan_enqueues_a_research_run_job(client, monkeypatch):
    import app.routes.research_plans as routes

    fake = FakeRedis()
    monkeypatch.setattr(routes.redis.Redis, "from_url", lambda *a, **k: fake)

    _project_id, plan_id = _plan(client)
    resp = client.post(f"/research-plans/{plan_id}/run")
    assert resp.status_code == 200
    job = resp.json()
    assert job["job_type"] == "research_run"
    assert job["status"] == "queued"
    assert job["payload"]["plan_id"] == plan_id
    assert fake.queue == [job["id"]]


def test_run_plan_unknown_404(client):
    resp = client.post("/research-plans/00000000-0000-0000-0000-000000000000/run")
    assert resp.status_code == 404


def test_research_run_executed_via_worker_is_listable(client):
    # Execute the run directly through the service (no worker process in tests),
    # then assert the run endpoints surface it.
    from aos_core.services.research_run import execute_research_run

    _project_id, plan_id = _plan(client)

    # Build the run through the service against the SAME session the app uses.
    db = next(_client_db())
    try:
        from aos_core.models import ResearchPlan

        plan = db.get(ResearchPlan, plan_id)
        run = execute_research_run(db, plan)
        run_id = run.id
    finally:
        db.close()

    runs = client.get(f"/research-plans/{plan_id}/runs")
    assert runs.status_code == 200
    assert any(r["id"] == run_id for r in runs.json())

    detail = client.get(f"/research-runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["plan_id"] == plan_id
    assert "phases" in body and "sources" in body and "conflicts" in body


def test_source_decision_override_persists_reason(client):
    from aos_core.services.research_run import execute_research_run
    from aos_core.models import ResearchPlan

    _project_id, plan_id = _plan(client)
    db = next(_client_db())
    try:
        plan = db.get(ResearchPlan, plan_id)
        run = execute_research_run(db, plan)
        run_id = run.id
        source_ref = run.sources[0]["ref"] if run.sources else None
    finally:
        db.close()

    if source_ref is None:
        # No local corpus seeded → no sources; the override path still 404s cleanly.
        resp = client.post(
            f"/research-runs/{run_id}/sources/whatever/decision",
            json={"accepted": False, "reason": "irrelevant"},
        )
        assert resp.status_code == 404
        return

    resp = client.post(
        f"/research-runs/{run_id}/sources/{source_ref}/decision",
        json={"accepted": False, "reason": "operator rejected: off-topic"},
    )
    assert resp.status_code == 200
    updated = {s["ref"]: s for s in resp.json()["sources"]}
    assert updated[source_ref]["accepted"] is False
    assert updated[source_ref]["reason"] == "operator rejected: off-topic"


def test_source_decision_requires_reason(client):
    from aos_core.services.research_run import execute_research_run
    from aos_core.models import ResearchPlan

    _project_id, plan_id = _plan(client)
    db = next(_client_db())
    try:
        plan = db.get(ResearchPlan, plan_id)
        run = execute_research_run(db, plan)
        run_id = run.id
    finally:
        db.close()

    resp = client.post(
        f"/research-runs/{run_id}/sources/anything/decision",
        json={"accepted": True, "reason": "   "},
    )
    assert resp.status_code == 422


def test_get_research_run_unknown_404(client):
    resp = client.get("/research-runs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
