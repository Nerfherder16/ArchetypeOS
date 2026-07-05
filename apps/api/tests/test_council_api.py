"""API tests for the council trigger + read endpoints (RFC-0005)."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.llm import DeterministicProvider
from aos_core.models import Repository, RepositoryDNA
from aos_core.services.council import run_council


class FakeRedis:
    """Captures lpush so the enqueue path needs no real Redis (dead port in conftest)."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append(value)


def _same_file_session(tmp_path):
    """A session on the same sqlite file the `client` fixture uses, for direct seeding."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_council_review_post_enqueues(client, monkeypatch):
    import app.main as main

    fake = FakeRedis()
    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: fake)

    project_id = client.post("/projects", json={"name": "Council"}).json()["id"]
    resp = client.post(f"/projects/{project_id}/council-reviews", json={"question": "Is it ready?"})
    assert resp.status_code == 200
    job = resp.json()
    assert job["job_type"] == "council_review"
    assert job["status"] == "queued"
    assert job["project_id"] == project_id
    assert job["payload"]["question"] == "Is it ready?"
    # A durable job row was created and its id pushed onto the queue.
    assert fake.queue == [job["id"]]
    assert client.get(f"/jobs/{job['id']}").status_code == 200


def test_council_review_post_missing_project(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.redis.Redis, "from_url", lambda *a, **k: FakeRedis())
    resp = client.post(
        "/projects/00000000-0000-0000-0000-000000000000/council-reviews",
        json={"question": "x"},
    )
    assert resp.status_code == 404


def test_council_review_get(client, tmp_path):
    project_id = client.post("/projects", json={"name": "Council Read"}).json()["id"]

    # Seed a persisted review directly through run_council (same sqlite file).
    session = _same_file_session(tmp_path)
    try:
        repo = Repository(project_id=project_id, name="svc", local_path="svc")
        session.add(repo)
        session.flush()
        session.add(
            RepositoryDNA(
                repository_id=repo.id,
                language_mix={"python": 1.0},
                frameworks=["fastapi"],
                risk_flags=["missing tests"],
            )
        )
        session.commit()
        review = run_council(session, project_id=project_id, question="Ready?", provider=DeterministicProvider())
        review_id = review.id
    finally:
        session.close()

    # list
    resp = client.get(f"/projects/{project_id}/council-reviews")
    assert resp.status_code == 200
    listed = resp.json()
    assert len(listed) == 1
    assert listed[0]["id"] == review_id

    # get by id, with nested agent outputs + verdict fields
    resp = client.get(f"/council-reviews/{review_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == review_id
    assert body["question"] == "Ready?"
    assert body["verdict"]
    assert len(body["agent_outputs"]) == 4
    assert {o["agent_name"] for o in body["agent_outputs"]} == {
        "research_librarian",
        "architecture_cartographer",
        "technology_fitness_judge",
        "security_agent",
    }


def test_council_review_get_missing(client):
    resp = client.get("/council-reviews/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_council_reviews_list_missing_project(client):
    resp = client.get("/projects/00000000-0000-0000-0000-000000000000/council-reviews")
    assert resp.status_code == 404
