from fastapi.testclient import TestClient

from app.main import settings


def create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        json={"name": "ArchetypeOS", "slug": "archetypeos", "description": "Runtime registry test project"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_project_can_be_created_and_listed(client: TestClient) -> None:
    project = create_project(client)

    response = client.get("/projects")

    assert response.status_code == 200, response.text
    projects = response.json()
    assert len(projects) == 1
    assert projects[0]["id"] == project["id"]
    assert projects[0]["slug"] == "archetypeos"


def test_repository_can_be_registered_by_local_path_read_only_by_default(client: TestClient, tmp_path) -> None:
    project = create_project(client)
    repo_path = settings.repository_root / "sample-repo"
    repo_path.mkdir()

    response = client.post(
        f"/projects/{project['id']}/repositories",
        json={
            "name": "Sample Repo",
            "local_path": "sample-repo",
            "default_branch": "main",
            "remote_url": "https://github.com/example/sample-repo.git",
        },
    )

    assert response.status_code == 200, response.text
    repository = response.json()
    assert repository["project_id"] == project["id"]
    assert repository["name"] == "Sample Repo"
    assert repository["local_path"] == "sample-repo"
    assert repository["default_branch"] == "main"
    assert repository["remote_url"] == "https://github.com/example/sample-repo.git"
    assert repository["is_read_only"] is True

    list_response = client.get(f"/projects/{project['id']}/repositories")
    assert list_response.status_code == 200, list_response.text
    repositories = list_response.json()
    assert [item["id"] for item in repositories] == [repository["id"]]
    assert repositories[0]["is_read_only"] is True


def test_repository_registration_rejects_paths_outside_repository_root(client: TestClient, tmp_path) -> None:
    project = create_project(client)
    outside_repo = tmp_path / "outside-repo"
    outside_repo.mkdir()

    response = client.post(
        f"/projects/{project['id']}/repositories",
        json={"name": "Outside Repo", "local_path": str(outside_repo)},
    )

    assert response.status_code == 400
    assert "Repository path must be under repository root" in response.json()["detail"]


def test_repository_registration_requires_existing_project(client: TestClient) -> None:
    repo_path = settings.repository_root / "sample-repo"
    repo_path.mkdir()

    response = client.post(
        "/projects/00000000-0000-0000-0000-000000000000/repositories",
        json={"name": "Sample Repo", "local_path": "sample-repo"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
