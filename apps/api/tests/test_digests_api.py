from pathlib import Path

from fastapi.testclient import TestClient

from app.main import settings

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def create_project(client: TestClient, slug: str = "digests") -> dict:
    response = client.post(
        "/projects",
        json={"name": "Digests Project", "slug": slug, "description": "Digests API test project"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def build_repo(local_path: str, with_tests: bool = True) -> Path:
    repo_path = settings.repository_root / local_path
    (repo_path / "src").mkdir(parents=True)
    (repo_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    if with_tests:
        (repo_path / "tests").mkdir(parents=True)
        (repo_path / "tests" / "test_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    return repo_path


def register_repository(client: TestClient, project_id: str, local_path: str, name: str = "Scan Target") -> dict:
    response = client.post(
        f"/projects/{project_id}/repositories",
        json={"name": name, "local_path": local_path, "default_branch": "main"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def scan(client: TestClient, repository_id: str) -> None:
    response = client.post(f"/repositories/{repository_id}/scan")
    assert response.status_code == 200, response.text


def test_digest_run_and_saved(client: TestClient) -> None:
    project = create_project(client)
    build_repo("digest-run")
    repository = register_repository(client, project["id"], "digest-run")
    scan(client, repository["id"])

    run = client.post(f"/projects/{project['id']}/digests")
    assert run.status_code == 200, run.text
    digest = run.json()
    assert isinstance(digest["summary"], str) and digest["summary"]
    assert digest["project_id"] == project["id"]

    listing = client.get(f"/projects/{project['id']}/digests")
    assert listing.status_code == 200, listing.text
    assert len(listing.json()) == 1
    assert listing.json()[0]["id"] == digest["id"]

    read = client.get(f"/digests/{digest['id']}")
    assert read.status_code == 200, read.text
    assert read.json()["id"] == digest["id"]
    assert read.json()["summary"] == digest["summary"]


def test_digest_changes_aggregation(client: TestClient) -> None:
    project = create_project(client)
    build_repo("digest-changes")
    repository = register_repository(client, project["id"], "digest-changes")
    scan(client, repository["id"])

    note = client.post(
        f"/projects/{project['id']}/research-notes",
        json={"title": "A research note", "summary": "Some findings"},
    )
    assert note.status_code == 200, note.text

    decision = client.post(
        f"/projects/{project['id']}/decisions",
        json={"title": "A decision", "decision": "Proceed"},
    )
    assert decision.status_code == 200, decision.text

    run = client.post(f"/projects/{project['id']}/digests")
    assert run.status_code == 200, run.text
    change_types = {entry["type"] for entry in run.json()["changes"]}
    assert "repository_scan" in change_types
    assert "decision" in change_types
    assert "research_note" in change_types


def test_digest_draft_recommendations(client: TestClient) -> None:
    project = create_project(client)
    build_repo("digest-no-tests", with_tests=False)
    scanned_repo = register_repository(client, project["id"], "digest-no-tests", name="No Tests Repo")
    scan(client, scanned_repo["id"])

    build_repo("digest-unscanned")
    register_repository(client, project["id"], "digest-unscanned", name="Unscanned Repo")

    decision = client.post(
        f"/projects/{project['id']}/decisions",
        json={"title": "Unlinked decision", "decision": "Proceed"},
    )
    assert decision.status_code == 200, decision.text

    run = client.post(f"/projects/{project['id']}/digests")
    assert run.status_code == 200, run.text
    recommendations = run.json()["recommendations"]
    titles = [entry["title"] for entry in recommendations]

    assert any(title.startswith("Add tests to") for title in titles)
    assert any(title.startswith("Run a scan for") for title in titles)
    assert any(title.startswith("Link research to decision") for title in titles)
    assert recommendations
    assert all(entry["status"] == "draft" for entry in recommendations)


def test_digest_repeated_tasks(client: TestClient) -> None:
    project = create_project(client)
    build_repo("digest-repeat")
    repository = register_repository(client, project["id"], "digest-repeat")
    scan(client, repository["id"])
    scan(client, repository["id"])

    run = client.post(f"/projects/{project['id']}/digests")
    assert run.status_code == 200, run.text
    repeated = run.json()["repeated_tasks"]
    entry = next(item for item in repeated if item["repository_id"] == repository["id"])
    assert entry["task"] == "repository_scan"
    assert entry["count"] == 2


def test_digest_empty_project(client: TestClient) -> None:
    project = create_project(client)

    run = client.post(f"/projects/{project['id']}/digests")
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["changes"] == []
    assert body["repeated_tasks"] == []
    assert isinstance(body["summary"], str) and body["summary"]
    assert "0 repositories" in body["summary"]


def test_digest_404s(client: TestClient) -> None:
    assert client.post(f"/projects/{UNKNOWN_ID}/digests").status_code == 404
    assert client.get(f"/projects/{UNKNOWN_ID}/digests").status_code == 404

    missing = client.get(f"/digests/{UNKNOWN_ID}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Digest not found"
