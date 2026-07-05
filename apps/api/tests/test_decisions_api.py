from fastapi.testclient import TestClient

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def create_project(client: TestClient, slug: str = "decisions") -> dict:
    response = client.post(
        "/projects",
        json={"name": "Decisions Project", "slug": slug, "description": "Decisions API test project"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_decision_crud(client: TestClient) -> None:
    project = create_project(client)

    create = client.post(
        f"/projects/{project['id']}/decisions",
        json={"title": "Adopt SQLite for tests", "decision": "Use SQLite in the test suite"},
    )
    assert create.status_code == 200, create.text
    created = create.json()
    assert created["title"] == "Adopt SQLite for tests"
    assert created["decision"] == "Use SQLite in the test suite"

    listing = client.get(f"/projects/{project['id']}/decisions")
    assert listing.status_code == 200, listing.text
    ids = [item["id"] for item in listing.json()]
    assert created["id"] in ids

    read = client.get(f"/decisions/{created['id']}")
    assert read.status_code == 200, read.text
    assert read.json()["id"] == created["id"]
    assert read.json()["title"] == created["title"]

    missing = client.get(f"/decisions/{UNKNOWN_ID}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Decision not found"


def test_research_note_crud(client: TestClient) -> None:
    project = create_project(client)

    create = client.post(
        f"/projects/{project['id']}/research-notes",
        json={"title": "Compare queue backends", "summary": "Redis vs RabbitMQ"},
    )
    assert create.status_code == 200, create.text
    created = create.json()
    assert created["title"] == "Compare queue backends"
    assert created["summary"] == "Redis vs RabbitMQ"

    listing = client.get(f"/projects/{project['id']}/research-notes")
    assert listing.status_code == 200, listing.text
    ids = [item["id"] for item in listing.json()]
    assert created["id"] in ids

    read = client.get(f"/research-notes/{created['id']}")
    assert read.status_code == 200, read.text
    assert read.json()["id"] == created["id"]

    missing = client.get(f"/research-notes/{UNKNOWN_ID}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Research note not found"


def test_recommendation_crud(client: TestClient) -> None:
    project = create_project(client)

    create = client.post(
        f"/projects/{project['id']}/recommendations",
        json={
            "title": "Migrate to Postgres",
            "recommendation": "Move production storage to Postgres",
            "evidence": [{"type": "note", "detail": "benchmarked write throughput"}],
        },
    )
    assert create.status_code == 200, create.text
    created = create.json()
    assert created["title"] == "Migrate to Postgres"
    assert len(created["evidence"]) == 1

    listing = client.get(f"/projects/{project['id']}/recommendations")
    assert listing.status_code == 200, listing.text
    ids = [item["id"] for item in listing.json()]
    assert created["id"] in ids

    read = client.get(f"/recommendations/{created['id']}")
    assert read.status_code == 200, read.text
    assert read.json()["id"] == created["id"]

    missing = client.get(f"/recommendations/{UNKNOWN_ID}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Recommendation not found"


def test_recommendation_requires_evidence(client: TestClient) -> None:
    project = create_project(client)

    create = client.post(
        f"/projects/{project['id']}/recommendations",
        json={"title": "No evidence", "recommendation": "Do the thing", "evidence": []},
    )
    assert create.status_code == 422, create.text


def test_decision_research_link(client: TestClient) -> None:
    project = create_project(client)

    note = client.post(
        f"/projects/{project['id']}/research-notes",
        json={"title": "Linked note", "summary": "Supports the decision"},
    )
    assert note.status_code == 200, note.text
    note_id = note.json()["id"]

    create = client.post(
        f"/projects/{project['id']}/decisions",
        json={"title": "Linked decision", "decision": "Proceed", "research_note_ids": [note_id]},
    )
    assert create.status_code == 200, create.text
    evidence = create.json()["evidence"]
    assert {"type": "research_note", "id": note_id} in evidence

    unknown = client.post(
        f"/projects/{project['id']}/decisions",
        json={"title": "Bad link", "research_note_ids": [UNKNOWN_ID]},
    )
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "Research note not found"

    other_project = create_project(client, slug="decisions-other")
    other_note = client.post(
        f"/projects/{other_project['id']}/research-notes",
        json={"title": "Other project note"},
    )
    assert other_note.status_code == 200, other_note.text
    other_note_id = other_note.json()["id"]

    cross = client.post(
        f"/projects/{project['id']}/decisions",
        json={"title": "Cross-project link", "research_note_ids": [other_note_id]},
    )
    assert cross.status_code == 404
    assert cross.json()["detail"] == "Research note not found"


def test_artifacts_404s(client: TestClient) -> None:
    base = f"/projects/{UNKNOWN_ID}"

    assert client.post(f"{base}/decisions", json={"title": "x", "decision": "y"}).status_code == 404
    assert client.get(f"{base}/decisions").status_code == 404

    assert client.post(f"{base}/research-notes", json={"title": "x"}).status_code == 404
    assert client.get(f"{base}/research-notes").status_code == 404

    assert (
        client.post(
            f"{base}/recommendations",
            json={"title": "x", "recommendation": "y", "evidence": [{"type": "note"}]},
        ).status_code
        == 404
    )
    assert client.get(f"{base}/recommendations").status_code == 404
