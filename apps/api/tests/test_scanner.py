from __future__ import annotations
import json
from pathlib import Path

import yaml

from aos_core.repository_scanner import scan_repository

FIXTURES = Path(__file__).parent / "fixtures"
COMPOSE_REPO = FIXTURES / "compose-repo"


def _snapshot(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


def _compose_expectations() -> tuple[set[str], set[tuple[str, str]], list[str]]:
    """Derive the expected service set + depends_on edge set from the fixture
    compose file itself, so the assertions stay count-agnostic (LES-012)."""
    document = yaml.safe_load((COMPOSE_REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    services = document["services"]
    edges: set[tuple[str, str]] = set()
    for name, body in services.items():
        deps = body.get("depends_on") if isinstance(body, dict) else None
        if isinstance(deps, dict):
            dep_names = list(deps)
        elif isinstance(deps, list):
            dep_names = list(deps)
        else:
            dep_names = []
        for dep in dep_names:
            edges.add((str(name), str(dep)))
    return set(services), edges, list(services)


def test_scan_repository_detects_manifest_and_languages(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.ts").write_text("console.log('ok')", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert result["package_managers"] == ["npm"]
    assert result["language_mix"]["TypeScript"] == 1
    assert "Dockerfile" in result["deployment_files"]
    assert result["architecture_nodes"]
    assert {"path": "package.json", "kind": "node"} in result["manifests"]
    assert {"path": "Dockerfile", "kind": "dockerfile"} in result["docker_files"]
    assert result["summary"]["has_docker"] is True


def test_ignored_dirs_are_skipped(tmp_path: Path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("x", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.pyc").write_text("x", encoding="utf-8")
    (tmp_path / "app.py").write_text("x", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert result["file_count"] == 1
    structure_paths = {entry["path"] for entry in result["folder_structure"]}
    assert "node_modules" not in structure_paths
    assert "__pycache__" not in structure_paths
    codes_paths = {(s["code"], s["path"]) for s in result["risk_signals"]}
    assert ("DEPENDENCY_DIR_PRESENT", "node_modules") in codes_paths


def test_env_and_secret_flagged_path_only(tmp_path: Path):
    planted_value = "fake." + "credential." * 3 + "value"
    (tmp_path / ".env").write_text(f"API_KEY={planted_value}", encoding="utf-8")
    (tmp_path / "key.pem").write_text("-----BEGIN FAKE MARKER-----", encoding="utf-8")

    result = scan_repository(tmp_path)

    signals = {(s["code"], s["path"]) for s in result["risk_signals"]}
    assert ("ENV_FILE_PRESENT", ".env") in signals
    assert ("SECRET_LIKE_FILENAME", "key.pem") in signals
    assert planted_value not in json.dumps(result)


def test_ci_detection(tmp_path: Path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: ci", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert {"path": ".github/workflows/ci.yml", "kind": "github_actions"} in result["ci_files"]
    assert result["summary"]["has_ci"] is True
    assert all(s["code"] != "NO_CI_CONFIG" for s in result["risk_signals"])


def test_no_ci_config_flagged(tmp_path: Path):
    (tmp_path / "app.py").write_text("x", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert any(s["code"] == "NO_CI_CONFIG" for s in result["risk_signals"])
    assert result["summary"]["has_ci"] is False


def test_determinism(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "src" / "b.ts").write_text("x", encoding="utf-8")
    (tmp_path / "web" / "components").mkdir(parents=True)
    (tmp_path / "web" / "components" / "app.tsx").write_text("x", encoding="utf-8")
    (tmp_path / "README.md").write_text("# hi", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")

    first = scan_repository(tmp_path)
    second = scan_repository(tmp_path)

    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_truncation(tmp_path: Path):
    for index in range(10):
        (tmp_path / f"file_{index}.py").write_text("x", encoding="utf-8")

    result = scan_repository(tmp_path, max_files=3)

    assert result["file_count"] == 3
    assert any(s["code"] == "SCAN_TRUNCATED" for s in result["risk_signals"])
    assert any("truncated" in note for note in result["notes"])


def test_backward_compatible_keys(tmp_path: Path):
    (tmp_path / "app.py").write_text("x", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert isinstance(result["folder_map"], list)
    assert isinstance(result["file_count"], int)
    assert isinstance(result["language_mix"], dict)
    assert isinstance(result["package_managers"], list)
    assert isinstance(result["deployment_files"], list)
    assert isinstance(result["risk_flags"], list)
    assert all(isinstance(flag, str) for flag in result["risk_flags"])
    assert isinstance(result["architecture_nodes"], list)
    assert isinstance(result["architecture_edges"], list)


def test_read_only_guarantee(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1", encoding="utf-8")

    before = _snapshot(tmp_path)
    scan_repository(tmp_path)
    after = _snapshot(tmp_path)

    assert before == after


def test_summary_flags_and_missing_tests(tmp_path: Path):
    (tmp_path / "app.py").write_text("x", encoding="utf-8")

    result = scan_repository(tmp_path)
    assert result["summary"]["has_tests"] is False
    assert any(s["code"] == "MISSING_TESTS" for s in result["risk_signals"])

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("x", encoding="utf-8")

    with_tests = scan_repository(tmp_path)
    assert with_tests["summary"]["has_tests"] is True
    assert all(s["code"] != "MISSING_TESTS" for s in with_tests["risk_signals"])


def test_docker_without_env_template_and_multiple_ecosystems(tmp_path: Path):
    (tmp_path / "Dockerfile").write_text("FROM scratch", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    result = scan_repository(tmp_path)
    codes = {s["code"] for s in result["risk_signals"]}
    assert "DOCKER_WITHOUT_ENV_TEMPLATE" in codes
    assert "MULTIPLE_ECOSYSTEMS" in codes
    assert result["summary"]["has_env_example"] is False

    (tmp_path / ".env.example").write_text("API_KEY=", encoding="utf-8")
    with_template = scan_repository(tmp_path)
    template_codes = {s["code"] for s in with_template["risk_signals"]}
    assert "DOCKER_WITHOUT_ENV_TEMPLATE" not in template_codes
    assert with_template["summary"]["has_env_example"] is True


def test_compose_fixture_yields_service_nodes_and_depends_on_edges():
    expected_services, expected_edges, expected_runtime = _compose_expectations()

    result = scan_repository(COMPOSE_REPO)

    service_nodes = [node for node in result["architecture_nodes"] if node["type"] == "service"]
    service_labels = {node["label"] for node in service_nodes}
    depends_edges = {
        (edge["from"], edge["to"]) for edge in result["architecture_edges"] if edge["type"] == "depends_on"
    }

    assert service_labels == expected_services
    assert depends_edges == expected_edges
    # Both the list form (web) and the map form (worker) are covered by the fixture.
    assert ("worker", "db") in depends_edges
    for node in service_nodes:
        assert node["evidence"] == ["docker-compose.yml"]
    # runtime_services preserves the compose declaration order.
    assert result["summary"]["runtime_services"] == expected_runtime
    # Only Python is a source language, so it wins over YAML/Markdown by classification.
    assert result["summary"]["primary_language"] == "Python"


def test_run_scan_populates_runtime_services_from_compose(tmp_path, monkeypatch):
    import shutil

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from aos_core.database import Base
    from aos_core.models import ArchitectureNode, Project, Repository, RepositoryDNA
    from aos_core.services.scan import run_scan
    from app.main import settings

    repository_root = tmp_path / "repositories"
    repository_root.mkdir()
    shutil.copytree(COMPOSE_REPO, repository_root / "compose-repo")
    monkeypatch.setattr(settings, "repository_root", repository_root)
    monkeypatch.setattr(settings, "artifact_root", tmp_path / "artifacts")

    engine = create_engine(
        f"sqlite:///{tmp_path / 'scanner.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    expected_services, _, _ = _compose_expectations()
    try:
        with session_local() as db:
            project = Project(name="Compose", slug="compose-scan")
            db.add(project)
            db.flush()
            repository = Repository(project_id=project.id, name="compose-repo", local_path="compose-repo")
            db.add(repository)
            db.flush()
            repository_id = repository.id
            run_scan(repository_id, db)

        with session_local() as db:
            dna = db.query(RepositoryDNA).filter(RepositoryDNA.repository_id == repository_id).first()
            assert dna is not None
            assert set(dna.runtime_services) == expected_services
            assert dna.scan_summary["summary"]["primary_language"] == "Python"

            nodes = (
                db.query(ArchitectureNode)
                .filter_by(repository_id=repository_id, type="service")
                .all()
            )
            assert {node.label for node in nodes} == expected_services
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_docs_heavy_repo_reports_source_primary_language(tmp_path: Path):
    for index in range(8):
        (tmp_path / f"doc_{index}.md").write_text("# doc\n", encoding="utf-8")
    for index in range(6):
        (tmp_path / f"conf_{index}.yml").write_text("key: value\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "util.py").write_text("y = 2\n", encoding="utf-8")

    result = scan_repository(tmp_path)

    # Markdown/YAML dominate by raw file count ...
    assert result["language_mix"]["Markdown"] > result["language_mix"]["Python"]
    assert result["language_mix"]["YAML"] > result["language_mix"]["Python"]
    # ... but Python is the only source-classified language, so it is primary.
    assert result["summary"]["primary_language"] == "Python"
    assert result["summary"]["primary_language_hints"][0] == "Python"
    assert result["summary"]["language_classes"]["Python"] == "source"
    assert result["summary"]["language_classes"]["Markdown"] == "docs"
    assert result["summary"]["language_classes"]["YAML"] == "config"


def test_repo_without_compose_has_no_service_nodes(tmp_path: Path):
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert not [node for node in result["architecture_nodes"] if node["type"] == "service"]
    assert not [edge for edge in result["architecture_edges"] if edge["type"] == "depends_on"]
    assert result["summary"]["runtime_services"] == []


def test_malformed_compose_is_tolerated(tmp_path: Path):
    # Broken YAML (unterminated flow sequence) must not crash the scan.
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  web:\n    depends_on: [oops\n", encoding="utf-8"
    )

    result = scan_repository(tmp_path)

    assert not [node for node in result["architecture_nodes"] if node["type"] == "service"]
    assert result["summary"]["runtime_services"] == []
    assert any("could not be parsed" in note for note in result["notes"])


def test_non_mapping_compose_is_tolerated(tmp_path: Path):
    # A compose file whose top level is not a mapping yields no services, not an error.
    (tmp_path / "compose.yml").write_text("- just\n- a\n- list\n", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert not [node for node in result["architecture_nodes"] if node["type"] == "service"]
    assert any("no services mapping" in note for note in result["notes"])


# --- Framework detection from manifest bodies (AOS-DISTILL-003) --------------


def test_frameworks_detected_from_manifest_bodies(tmp_path: Path):
    # A polyglot fixture: npm (express + react), pip requirements (fastapi/flask),
    # pyproject (django + pydantic), and a go.mod requiring gin.
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"express": "^4.18.0", "react": "^18.2.0", "left-pad": "1.3.0"}}',
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "fastapi==0.115.0\nflask>=3.0\nrequests==2.32.0\n# a comment\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "svc"\ndependencies = ["django>=5.0", "pydantic>=2.0", "boto3"]\n',
        encoding="utf-8",
    )
    (tmp_path / "go.mod").write_text(
        "module example.com/app\n\ngo 1.22\n\nrequire (\n"
        "\tgithub.com/gin-gonic/gin v1.10.0\n\tgithub.com/some/other v0.1.0\n)\n",
        encoding="utf-8",
    )

    result = scan_repository(tmp_path)

    assert result["frameworks"] == sorted(
        {"express", "react", "fastapi", "flask", "django", "pydantic", "gin"}
    )


def test_frameworks_ignores_unknown_dependencies(tmp_path: Path):
    # Only curated, high-confidence deps emit a framework — unknowns are never guessed.
    (tmp_path / "requirements.txt").write_text(
        "requests==2.32.0\nnumpy==2.0\nbeautifulsoup4==4.12\n", encoding="utf-8"
    )
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"lodash": "^4.17.0", "axios": "^1.6.0"}}', encoding="utf-8"
    )

    result = scan_repository(tmp_path)

    assert result["frameworks"] == []


def test_frameworks_detection_tolerates_malformed_manifests(tmp_path: Path):
    # A malformed package.json + a broken pyproject must not crash the scan; a
    # valid go.mod alongside them is still detected.
    (tmp_path / "package.json").write_text('{"dependencies": {"express": ', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project\nname = broken toml", encoding="utf-8")
    (tmp_path / "go.mod").write_text(
        "module example.com/app\n\nrequire github.com/labstack/echo/v4 v4.12.0\n", encoding="utf-8"
    )

    result = scan_repository(tmp_path)  # must not raise

    assert result["frameworks"] == ["echo"]


def test_frameworks_key_present_and_empty_without_manifests(tmp_path: Path):
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert result["frameworks"] == []
