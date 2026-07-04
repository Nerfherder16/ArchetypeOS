from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app, settings


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    repository_root = tmp_path / "repositories"
    repository_root.mkdir()
    settings.repository_root = repository_root
    settings.artifact_root = tmp_path / "artifacts"

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


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
