import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import settings

SCAN_MARKER = "fake-env-marker-do-not-leak"


def create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        json={"name": "ArchetypeOS", "slug": "archetypeos", "description": "Scan endpoint test project"},
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


def test_scan_endpoint_produces_report_dna_and_artifact(client: TestClient) -> None:
    project = create_project(client)
    build_repo("scan-target")
    repository = register_repository(client, project["id"], "scan-target")

    response = client.post(f"/repositories/{repository['id']}/scan")
    assert response.status_code == 200, response.text
    body = response.json()

    report = body["summary"]
    risk_codes = {signal["code"] for signal in report["risk_signals"]}
    assert "ENV_FILE_PRESENT" in risk_codes
    ci_paths = {item["path"] for item in report["ci_files"]}
    assert ".github/workflows/ci.yml" in ci_paths
    assert report["summary"]["has_ci"] is True

    serialized = json.dumps(body)
    assert SCAN_MARKER not in serialized

    assert len(body["artifacts"]) == 1
    artifact = body["artifacts"][0]
    artifact_path = Path(artifact["path"])
    assert artifact_path.exists()
    assert settings.artifact_root.resolve() in artifact_path.resolve().parents
    parsed = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    assert digest == artifact["checksum"]

    list_response = client.get(f"/projects/{project['id']}/repositories")
    assert list_response.status_code == 200, list_response.text
    repositories = list_response.json()
    assert repositories[0]["last_scanned_at"] is not None


def test_scan_endpoint_is_read_only_against_scanned_repo(client: TestClient) -> None:
    project = create_project(client)
    repo_path = build_repo("read-only-target")
    repository = register_repository(client, project["id"], "read-only-target")

    before = {path.relative_to(repo_path).as_posix() for path in repo_path.rglob("*")}

    response = client.post(f"/repositories/{repository['id']}/scan")
    assert response.status_code == 200, response.text

    after = {path.relative_to(repo_path).as_posix() for path in repo_path.rglob("*")}
    assert before == after

    artifact_path = Path(response.json()["artifacts"][0]["path"])
    assert repo_path.resolve() not in artifact_path.resolve().parents


def test_scan_endpoint_404_for_unknown_repository(client: TestClient) -> None:
    response = client.post("/repositories/00000000-0000-0000-0000-000000000000/scan")
    assert response.status_code == 404
    assert response.json()["detail"] == "Repository not found"


def test_scan_endpoint_rescan_updates_dna(client: TestClient) -> None:
    project = create_project(client)
    build_repo("rescan-target")
    repository = register_repository(client, project["id"], "rescan-target")

    first = client.post(f"/repositories/{repository['id']}/scan")
    assert first.status_code == 200, first.text

    second = client.post(f"/repositories/{repository['id']}/scan")
    assert second.status_code == 200, second.text

    dna = second.json()["dna"]
    assert dna["risk_flags"] == second.json()["summary"]["risk_flags"]
    assert dna["confidence"] == 0.65
