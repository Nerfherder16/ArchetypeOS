from pathlib import Path

from fastapi.testclient import TestClient

from app.main import settings

SCAN_MARKER = "fake-env-marker-do-not-leak"


def create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        json={"name": "ArchetypeOS", "slug": "archetypeos", "description": "DNA endpoint test project"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def build_repo(local_path: str) -> Path:
    repo_path = settings.repository_root / local_path
    (repo_path / "src").mkdir(parents=True)
    (repo_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (repo_path / ".env").write_text(f"API_KEY={SCAN_MARKER}\n", encoding="utf-8")
    (repo_path / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    workflows = repo_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: ci\non: push\n", encoding="utf-8")
    return repo_path


def register_repository(client: TestClient, project_id: str, local_path: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/repositories",
        json={"name": "Scan Target", "local_path": local_path, "default_branch": "main"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_dna_endpoint_returns_stored_scan_results(client: TestClient) -> None:
    project = create_project(client)
    build_repo("dna-target")
    repository = register_repository(client, project["id"], "dna-target")

    scan_response = client.post(f"/repositories/{repository['id']}/scan")
    assert scan_response.status_code == 200, scan_response.text

    response = client.get(f"/repositories/{repository['id']}/dna")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["repository_id"] == repository["id"]
    assert body["language_mix"]
    assert "Python" in body["language_mix"]
    assert body["risk_flags"]
    assert body["scan_summary"]
    assert "summary" in body["scan_summary"]
    assert body["scan_summary"]["summary"]["has_ci"] is True
    assert body["confidence"] == 0.65
    # AOS-CONTRACT-001: the richer evidence the backend computes is no longer
    # dropped at the API seam — these keys are present in the contract.
    for field in ("purpose", "maturity", "frameworks", "runtime_services", "evidence"):
        assert field in body, f"RepositoryDnaRead must expose {field}"
    assert isinstance(body["frameworks"], list)
    assert isinstance(body["runtime_services"], list)


def test_dna_endpoint_404_for_never_scanned_repository(client: TestClient) -> None:
    project = create_project(client)
    build_repo("never-scanned-target")
    repository = register_repository(client, project["id"], "never-scanned-target")

    response = client.get(f"/repositories/{repository['id']}/dna")
    assert response.status_code == 404
    assert response.json()["detail"] == "Repository has not been scanned"


def test_dna_endpoint_404_for_unknown_repository(client: TestClient) -> None:
    response = client.get("/repositories/00000000-0000-0000-0000-000000000000/dna")
    assert response.status_code == 404
    assert response.json()["detail"] == "Repository not found"
