import hashlib
from pathlib import Path

from fastapi.testclient import TestClient


def create_project(client: TestClient, slug: str) -> dict:
    response = client.post(
        "/projects",
        json={"name": "ArchetypeOS", "slug": slug, "description": "Scan history test project"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def build_repo(client: TestClient, local_path: str) -> Path:
    from app.main import settings

    repo_path = settings.repository_root / local_path
    (repo_path / "src").mkdir(parents=True)
    (repo_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
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


def scan(client: TestClient, repository_id: str) -> dict:
    response = client.post(f"/repositories/{repository_id}/scan")
    assert response.status_code == 200, response.text
    return response.json()


def test_two_scans_produce_two_versioned_artifacts(client: TestClient) -> None:
    project = create_project(client, "two-scans")
    build_repo(client, "two-scans")
    repository = register_repository(client, project["id"], "two-scans")

    scan(client, repository["id"])
    scan(client, repository["id"])

    response = client.get(f"/repositories/{repository['id']}/scans")
    assert response.status_code == 200, response.text
    scans = response.json()
    assert len(scans) == 2

    paths = {row["path"] for row in scans}
    names = {row["name"] for row in scans}
    assert len(paths) == 2
    assert len(names) == 2

    for row in scans:
        artifact_path = Path(row["path"])
        assert artifact_path.exists(), row["path"]
        digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        assert digest == row["checksum"]


def test_scan_history_listing(client: TestClient) -> None:
    project = create_project(client, "history-listing")
    build_repo(client, "history-listing")
    repository = register_repository(client, project["id"], "history-listing")

    first = scan(client, repository["id"])
    second = scan(client, repository["id"])

    response = client.get(f"/repositories/{repository['id']}/scans")
    assert response.status_code == 200, response.text
    scans = response.json()
    assert len(scans) == 2

    for row in scans:
        assert row["artifact_type"] == "repository_scan"

    assert scans[0]["created_at"] >= scans[1]["created_at"]
    ids = [row["id"] for row in scans]
    assert first["artifacts"][0]["id"] in ids
    assert second["artifacts"][0]["id"] in ids


def test_scan_report_content_retrievable(client: TestClient) -> None:
    project = create_project(client, "report-content")
    build_repo(client, "report-content")
    repository = register_repository(client, project["id"], "report-content")

    scanned = scan(client, repository["id"])
    artifact_id = scanned["artifacts"][0]["id"]

    response = client.get(f"/repositories/{repository['id']}/scans/{artifact_id}")
    assert response.status_code == 200, response.text
    report = response.json()
    assert isinstance(report, dict)
    assert "summary" in report
    assert "risk_signals" in report
    assert report["summary"] == scanned["summary"]["summary"]


def test_scan_history_404s(client: TestClient) -> None:
    unknown_repository = "00000000-0000-0000-0000-000000000000"
    unknown_artifact = "11111111-1111-1111-1111-111111111111"

    listing = client.get(f"/repositories/{unknown_repository}/scans")
    assert listing.status_code == 404, listing.text
    assert listing.json()["detail"] == "Repository not found"

    content = client.get(f"/repositories/{unknown_repository}/scans/{unknown_artifact}")
    assert content.status_code == 404, content.text
    assert content.json()["detail"] == "Repository not found"

    project = create_project(client, "history-404")
    build_repo(client, "history-404-a")
    repository_a = register_repository(client, project["id"], "history-404-a")
    scanned_a = scan(client, repository_a["id"])
    artifact_a = scanned_a["artifacts"][0]["id"]

    build_repo(client, "history-404-b")
    repository_b = register_repository(client, project["id"], "history-404-b")
    scan(client, repository_b["id"])

    missing = client.get(f"/repositories/{repository_a['id']}/scans/{unknown_artifact}")
    assert missing.status_code == 404, missing.text
    assert missing.json()["detail"] == "Scan artifact not found"

    cross = client.get(f"/repositories/{repository_b['id']}/scans/{artifact_a}")
    assert cross.status_code == 404, cross.text
    assert cross.json()["detail"] == "Scan artifact not found"
