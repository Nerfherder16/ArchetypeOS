from __future__ import annotations
import json
from pathlib import Path
from app.repository_scanner import scan_repository


def _snapshot(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


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
    secret = "SUPER_SECRET_TOKEN_abc123"
    (tmp_path / ".env").write_text(f"API_KEY={secret}", encoding="utf-8")
    (tmp_path / "key.pem").write_text("-----BEGIN PRIVATE KEY-----", encoding="utf-8")

    result = scan_repository(tmp_path)

    signals = {(s["code"], s["path"]) for s in result["risk_signals"]}
    assert ("ENV_FILE_PRESENT", ".env") in signals
    assert ("SECRET_LIKE_FILENAME", "key.pem") in signals
    assert secret not in json.dumps(result)


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
