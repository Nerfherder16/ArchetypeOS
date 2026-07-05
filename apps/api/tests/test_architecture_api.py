from pathlib import Path

from fastapi.testclient import TestClient

from app.main import settings


def create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        json={"name": "ArchetypeOS", "slug": "arch-graph", "description": "Architecture API test project"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def build_repo(local_path: str, dirs: tuple[str, ...] = ("src", "docs")) -> Path:
    repo_path = settings.repository_root / local_path
    repo_path.mkdir(parents=True)
    for name in dirs:
        directory = repo_path / name
        directory.mkdir(parents=True)
        (directory / "placeholder.py").write_text("print('hello')\n", encoding="utf-8")
    return repo_path


def register_repository(client: TestClient, project_id: str, name: str, local_path: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/repositories",
        json={"name": name, "local_path": local_path, "default_branch": "main"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def scan_repository(client: TestClient, repository_id: str) -> dict:
    response = client.post(f"/repositories/{repository_id}/scan")
    assert response.status_code == 200, response.text
    return response.json()


def test_architecture_graph_query_after_scan(client: TestClient) -> None:
    project = create_project(client)
    build_repo("graph-target")
    repository = register_repository(client, project["id"], "Scan Target", "graph-target")
    scan_repository(client, repository["id"])

    response = client.get(f"/projects/{project['id']}/architecture")
    assert response.status_code == 200, response.text
    graph = response.json()
    nodes = graph["nodes"]
    edges = graph["edges"]

    repo_nodes = [node for node in nodes if node["type"] == "repository"]
    assert len(repo_nodes) == 1, response.text
    assert repo_nodes[0]["label"] == "Scan Target"
    root_id = repo_nodes[0]["id"]

    directory_nodes = [node for node in nodes if node["type"] == "directory"]
    directory_labels = {node["label"] for node in directory_nodes}
    assert {"src", "docs"} <= directory_labels

    for node in nodes:
        assert isinstance(node["confidence"], float)
        assert isinstance(node["evidence"], list)
        assert node["manual_correction"] is None

    node_ids = {node["id"] for node in nodes}
    contains = [edge for edge in edges if edge["type"] == "contains"]
    assert len(contains) == len(directory_nodes)
    for edge in contains:
        assert edge["from_node_id"] == root_id
        assert edge["to_node_id"] in node_ids
        assert isinstance(edge["confidence"], float)
        assert edge["manual_correction"] is None

    assert [node["label"] for node in nodes] == sorted(node["label"] for node in nodes)
    assert [edge["type"] for edge in edges] == sorted(edge["type"] for edge in edges)


def test_architecture_graph_repository_filter(client: TestClient) -> None:
    project = create_project(client)
    build_repo("repo-one", dirs=("src",))
    build_repo("repo-two", dirs=("docs",))
    repo_one = register_repository(client, project["id"], "Repo One", "repo-one")
    repo_two = register_repository(client, project["id"], "Repo Two", "repo-two")
    scan_repository(client, repo_one["id"])
    scan_repository(client, repo_two["id"])

    unfiltered = client.get(f"/projects/{project['id']}/architecture")
    assert unfiltered.status_code == 200, unfiltered.text
    all_graph = unfiltered.json()
    assert {node["repository_id"] for node in all_graph["nodes"]} == {repo_one["id"], repo_two["id"]}
    assert {edge["repository_id"] for edge in all_graph["edges"]} == {repo_one["id"], repo_two["id"]}

    filtered = client.get(
        f"/projects/{project['id']}/architecture",
        params={"repository_id": repo_one["id"]},
    )
    assert filtered.status_code == 200, filtered.text
    filtered_graph = filtered.json()
    assert {node["repository_id"] for node in filtered_graph["nodes"]} == {repo_one["id"]}
    assert {edge["repository_id"] for edge in filtered_graph["edges"]} == {repo_one["id"]}
    filtered_labels = {node["label"] for node in filtered_graph["nodes"]}
    assert "src" in filtered_labels
    assert "docs" not in filtered_labels


def test_node_manual_correction_persists(client: TestClient) -> None:
    project = create_project(client)
    build_repo("correction-target")
    repository = register_repository(client, project["id"], "Scan Target", "correction-target")
    scan_repository(client, repository["id"])

    graph = client.get(f"/projects/{project['id']}/architecture").json()
    directory_node = next(node for node in graph["nodes"] if node["type"] == "directory")

    patch = client.patch(
        f"/architecture/nodes/{directory_node['id']}",
        json={"manual_correction": "actually the web frontend"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["manual_correction"] == "actually the web frontend"

    refreshed = client.get(f"/projects/{project['id']}/architecture").json()
    corrected = next(node for node in refreshed["nodes"] if node["id"] == directory_node["id"])
    assert corrected["manual_correction"] == "actually the web frontend"

    edge = graph["edges"][0]
    edge_patch = client.patch(
        f"/architecture/edges/{edge['id']}",
        json={"manual_correction": "verified containment"},
    )
    assert edge_patch.status_code == 200, edge_patch.text
    assert edge_patch.json()["manual_correction"] == "verified containment"


def test_rescan_preserves_node_ids_and_corrections(client: TestClient) -> None:
    project = create_project(client)
    build_repo("rescan-arch-target")
    repository = register_repository(client, project["id"], "Scan Target", "rescan-arch-target")
    scan_repository(client, repository["id"])

    first = client.get(f"/projects/{project['id']}/architecture").json()
    first_ids = {node["id"] for node in first["nodes"]}
    directory_node = next(node for node in first["nodes"] if node["type"] == "directory")

    patch = client.patch(
        f"/architecture/nodes/{directory_node['id']}",
        json={"manual_correction": "curated"},
    )
    assert patch.status_code == 200, patch.text

    scan_repository(client, repository["id"])

    second = client.get(f"/projects/{project['id']}/architecture").json()
    second_ids = {node["id"] for node in second["nodes"]}
    assert len(second["nodes"]) == len(first["nodes"])
    assert second_ids == first_ids

    corrected = next(node for node in second["nodes"] if node["id"] == directory_node["id"])
    assert corrected["manual_correction"] == "curated"
    assert isinstance(corrected["confidence"], float)
    assert corrected["evidence"]


def test_architecture_api_404s(client: TestClient) -> None:
    unknown = "00000000-0000-0000-0000-000000000000"

    missing_project = client.get(f"/projects/{unknown}/architecture")
    assert missing_project.status_code == 404
    assert missing_project.json()["detail"] == "Project not found"

    missing_node = client.patch(f"/architecture/nodes/{unknown}", json={"manual_correction": "x"})
    assert missing_node.status_code == 404
    assert missing_node.json()["detail"] == "Architecture node not found"

    missing_edge = client.patch(f"/architecture/edges/{unknown}", json={"manual_correction": "x"})
    assert missing_edge.status_code == 404
    assert missing_edge.json()["detail"] == "Architecture edge not found"
