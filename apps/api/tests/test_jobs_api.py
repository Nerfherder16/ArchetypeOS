"""API tests for the project jobs-list endpoint (RFC-0007 / AOS-SCHED-002)."""

from __future__ import annotations


class FakeRedis:
    """Captures lpush so POST /jobs needs no real Redis (dead port in conftest)."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append(value)


def _make_project(client) -> str:
    resp = client.post("/projects", json={"name": "Jobs Project"})
    assert resp.status_code == 200
    return resp.json()["id"]


def test_list_project_jobs(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: FakeRedis())

    project_id = _make_project(client)

    first = client.post("/jobs", json={"project_id": project_id, "job_type": "project_digest"})
    assert first.status_code == 200
    second = client.post("/jobs", json={"project_id": project_id, "job_type": "repository_scan"})
    assert second.status_code == 200

    resp = client.get(f"/projects/{project_id}/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 2

    # Newest queued first.
    assert jobs[0]["id"] == second.json()["id"]
    assert jobs[0]["job_type"] == "repository_scan"
    assert jobs[1]["id"] == first.json()["id"]
    assert jobs[1]["job_type"] == "project_digest"
    assert all(job["status"] == "queued" for job in jobs)
    assert all(job["project_id"] == project_id for job in jobs)


def test_list_project_jobs_missing_project(client):
    resp = client.get("/projects/00000000-0000-0000-0000-000000000000/jobs")
    assert resp.status_code == 404
