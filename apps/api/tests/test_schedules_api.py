"""API tests for schedule CRUD + run-now (RFC-0007 / AOS-SCHED-001)."""

from __future__ import annotations


class FakeRedis:
    """Captures lpush so run-now needs no real Redis (dead port in conftest)."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append(value)


def _make_project(client) -> str:
    resp = client.post("/projects", json={"name": "Sched Project"})
    assert resp.status_code == 200
    return resp.json()["id"]


def test_schedule_crud(client):
    project_id = _make_project(client)

    # create
    resp = client.post(
        f"/projects/{project_id}/schedules",
        json={"name": "nightly digest", "job_type": "project_digest", "interval_seconds": 86400},
    )
    assert resp.status_code == 200
    created = resp.json()
    schedule_id = created["id"]
    assert created["project_id"] == project_id
    assert created["job_type"] == "project_digest"
    assert created["interval_seconds"] == 86400
    assert created["enabled"] is True
    assert created["last_run_at"] is None
    assert created["next_run_at"] is not None

    # list
    resp = client.get(f"/projects/{project_id}/schedules")
    assert resp.status_code == 200
    listed = resp.json()
    assert len(listed) == 1
    assert listed[0]["id"] == schedule_id

    # get
    resp = client.get(f"/schedules/{schedule_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == schedule_id

    # patch: disable
    resp = client.patch(f"/schedules/{schedule_id}", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    # delete
    resp = client.delete(f"/schedules/{schedule_id}")
    assert resp.status_code == 204

    # gone
    resp = client.get(f"/schedules/{schedule_id}")
    assert resp.status_code == 404


def test_schedule_crud_missing_project(client):
    resp = client.post(
        "/projects/00000000-0000-0000-0000-000000000000/schedules",
        json={"name": "x", "job_type": "test", "interval_seconds": 60},
    )
    assert resp.status_code == 404


def test_schedule_run_now(client, monkeypatch):
    import app.main as main

    fake = FakeRedis()
    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: fake)

    project_id = _make_project(client)
    resp = client.post(
        f"/projects/{project_id}/schedules",
        json={"name": "run me", "job_type": "test", "interval_seconds": 3600},
    )
    schedule_id = resp.json()["id"]

    resp = client.post(f"/schedules/{schedule_id}/run")
    assert resp.status_code == 200
    job = resp.json()
    assert job["job_type"] == "test"
    assert job["status"] == "queued"
    job_id = job["id"]

    # the job id was pushed onto the queue
    assert fake.queue == [job_id]

    # a durable Job row exists
    resp = client.get(f"/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id

    # last_run_at was stamped on the schedule
    resp = client.get(f"/schedules/{schedule_id}")
    assert resp.json()["last_run_at"] is not None


def test_schedule_run_now_missing(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: FakeRedis())
    resp = client.post("/schedules/00000000-0000-0000-0000-000000000000/run")
    assert resp.status_code == 404
