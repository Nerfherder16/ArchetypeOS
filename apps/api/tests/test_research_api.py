"""API tests for the research trigger endpoint (RFC-0011 slice-1)."""

from __future__ import annotations


class FakeRedis:
    """Captures lpush so the enqueue path needs no real Redis (dead port in conftest)."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append(value)


def test_research_post_enqueues(client, monkeypatch):
    import app.main as main

    fake = FakeRedis()
    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: fake)

    project_id = client.post("/projects", json={"name": "Research"}).json()["id"]
    resp = client.post(
        f"/projects/{project_id}/research",
        json={"question": "Should we adopt asyncpg?", "sensitivity": "public"},
    )
    assert resp.status_code == 200
    job = resp.json()
    assert job["job_type"] == "research"
    assert job["status"] == "queued"
    assert job["project_id"] == project_id
    assert job["payload"]["question"] == "Should we adopt asyncpg?"
    assert job["payload"]["sensitivity"] == "public"
    assert fake.queue == [job["id"]]
    assert client.get(f"/jobs/{job['id']}").status_code == 200


def test_research_post_defaults_sensitivity(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: FakeRedis())
    project_id = client.post("/projects", json={"name": "Research2"}).json()["id"]
    resp = client.post(f"/projects/{project_id}/research", json={"question": "Q?"})
    assert resp.status_code == 200
    assert resp.json()["payload"]["sensitivity"] == "public"


def test_research_post_missing_project(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: FakeRedis())
    resp = client.post(
        "/projects/00000000-0000-0000-0000-000000000000/research",
        json={"question": "x"},
    )
    assert resp.status_code == 404
