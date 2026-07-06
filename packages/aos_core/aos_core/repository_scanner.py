"""Read-only repository scanner.

Walks a repository tree and produces a deterministic, timestamp-free report
describing its structure. The scanner inspects paths, names, and filesystem
metadata for its structural inventory. It reads file CONTENTS only for
detected Docker Compose files (to derive service and dependency edges); it
reads no other file bodies, never writes into the scanned tree, never
executes anything, and never follows symlinks.

Report schema (scan_repository return dict):
    root_name: str                 repository directory name
    repository_path: str           absolute-ish path that was scanned
    folder_map: list[str]          top-level directory names (legacy)
    file_count: int                number of non-ignored files (legacy)
    language_mix: dict[str, int]   language -> file count (legacy)
    package_managers: list[str]    detected package managers (legacy)
    package_manifests: list[str]   manifest file paths (legacy)
    deployment_files: list[str]    deployment file paths (legacy)
    readme_files: list[str]        readme file paths (legacy)
    risk_flags: list[str]          warning-severity messages (legacy)
    architecture_nodes: list[dict] graph nodes (repository, directories, compose services)
    architecture_edges: list[dict] graph edges (contains, compose depends_on)
    manifests: list[dict]          {path, kind}
    docker_files: list[dict]       {path, kind}
    ci_files: list[dict]           {path, kind}
    folder_structure: list[dict]   {path, type, depth} up to depth 4
    summary: dict                  aggregate flags and counts
    risk_signals: list[dict]       {severity, code, path, message}
    notes: list[str]               truncation and diagnostic notes
"""
from __future__ import annotations
import os
from collections import Counter
from pathlib import Path

import yaml

MANIFEST_FILES = {
    "package.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "requirements.txt": "pip",
    "pyproject.toml": "python",
    "poetry.lock": "poetry",
    "Cargo.toml": "cargo",
    "go.mod": "go",
}

MANIFEST_KINDS = {
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "setup.py": "python",
    "setup.cfg": "python",
    "poetry.lock": "python",
    "package.json": "node",
    "package-lock.json": "node",
    "pnpm-lock.yaml": "node",
    "yarn.lock": "node",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "alembic.ini": "python_migration",
    ".env.example": "env_template",
    ".env.sample": "env_template",
}

DEPLOYMENT_FILES = {"Dockerfile", "docker-compose.yml", "compose.yml", "kubernetes.yml", "helmfile.yaml"}
COMPOSE_FILES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
EXTENSIONS = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".js": "JavaScript",
    ".jsx": "JavaScript React",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cs": "C#",
    ".md": "Markdown",
    ".sh": "Shell",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
}
IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".cache",
    ".tox",
    ".coverage",
    "htmlcov",
}
DEPENDENCY_DIRS = {"node_modules", ".venv", "venv"}
BUILD_ARTIFACT_DIRS = {"dist", "build", ".next"}
TEST_DIR_NAMES = {"tests", "test", "__tests__"}
SECRET_NAMES = {"id_rsa", "id_dsa", "id_ed25519", "credentials.json", "service-account.json"}
SECRET_SUFFIXES = {".pem", ".key"}
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}
ENV_TEMPLATE_NAMES = {".env.example", ".env.sample"}
ECOSYSTEM_KINDS = {"python", "node", "rust", "go"}

# Classifies each EXTENSIONS language into a coarse role so a config/docs-heavy
# repo is not misreported as (say) YAML- or Markdown-primary (LES-013). Only the
# "source" class counts toward the derived primary language.
LANGUAGE_CLASS = {
    "Python": "source",
    "TypeScript": "source",
    "TypeScript React": "source",
    "JavaScript": "source",
    "JavaScript React": "source",
    "Go": "source",
    "Rust": "source",
    "Java": "source",
    "C#": "source",
    "Shell": "source",
    "SQL": "source",
    "YAML": "config",
    "Markdown": "docs",
    "HTML": "markup",
    "CSS": "markup",
}

MAX_FILES = 20000
MAX_FOLDER_STRUCTURE = 500
MAX_COMPOSE_SERVICES = 200


def safe_repo_path(repository_root: Path, local_path: str) -> Path:
    root = repository_root.resolve()
    candidate = (root / local_path).resolve() if not Path(local_path).is_absolute() else Path(local_path).resolve()
    if root not in candidate.parents and candidate != root:
        raise ValueError(f"Repository path must be under repository root: {root}")
    if not candidate.exists() or not candidate.is_dir():
        raise FileNotFoundError(f"Repository path does not exist: {candidate}")
    return candidate


def _is_ignored_dir(name: str) -> bool:
    return name in IGNORED_DIRS or name.endswith(".egg-info")


def _docker_kind(name: str) -> str | None:
    if name == "Dockerfile" or name.startswith("Dockerfile."):
        return "dockerfile"
    if name in COMPOSE_FILES:
        return "compose"
    return None


def _ci_kind(rel: str, name: str, suffix: str) -> str | None:
    parts = rel.split("/")
    if len(parts) == 3 and parts[0] == ".github" and parts[1] == "workflows" and suffix in {".yml", ".yaml"}:
        return "github_actions"
    if name == ".gitlab-ci.yml":
        return "gitlab"
    if name == "Jenkinsfile":
        return "jenkins"
    if rel == ".circleci/config.yml" or name == "circle.yml":
        return "circleci"
    return None


def _is_test_file(name: str) -> bool:
    if name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py")):
        return True
    return any(name.endswith(suffix) for suffix in (".test.ts", ".test.tsx", ".spec.ts", ".spec.js"))


def scan_repository(path: Path, max_files: int = MAX_FILES) -> dict:
    files: list[tuple[str, str, str]] = []
    dir_rels: list[str] = []
    encountered_ignored: list[tuple[str, str]] = []
    truncated = False

    for dirpath, dirnames, filenames in os.walk(path):
        dirnames.sort()
        filenames.sort()
        kept: list[str] = []
        for name in dirnames:
            if _is_ignored_dir(name):
                encountered_ignored.append((name, (Path(dirpath) / name).relative_to(path).as_posix()))
            else:
                kept.append(name)
        dirnames[:] = kept

        rel_dir = Path(dirpath).relative_to(path).as_posix()
        if rel_dir != ".":
            dir_rels.append(rel_dir)

        if truncated:
            continue
        for name in filenames:
            if len(files) >= max_files:
                truncated = True
                break
            rel = (Path(dirpath) / name).relative_to(path).as_posix()
            files.append((rel, name, Path(name).suffix.lower()))

    language_counts: Counter[str] = Counter()
    package_managers: set[str] = set()
    deployment_files: list[str] = []
    manifests: list[dict] = []
    docker_files: list[dict] = []
    ci_files: list[dict] = []
    signals: list[dict] = []
    manifest_kinds: set[str] = set()
    has_env_example = False
    has_code_outside_tests = False

    for rel, name, suffix in files:
        language = EXTENSIONS.get(suffix)
        if language:
            language_counts[language] += 1

        if name in MANIFEST_FILES:
            package_managers.add(MANIFEST_FILES[name])
        if name in MANIFEST_KINDS:
            kind = MANIFEST_KINDS[name]
            manifests.append({"path": rel, "kind": kind})
            manifest_kinds.add(kind)

        if name in DEPLOYMENT_FILES or rel in DEPLOYMENT_FILES:
            deployment_files.append(rel)
        docker_kind = _docker_kind(name)
        if docker_kind:
            docker_files.append({"path": rel, "kind": docker_kind})
        ci_kind = _ci_kind(rel, name, suffix)
        if ci_kind:
            ci_files.append({"path": rel, "kind": ci_kind})

        if name in ENV_TEMPLATE_NAMES:
            has_env_example = True
        if name == ".env":
            signals.append(
                {
                    "severity": "warning",
                    "code": "ENV_FILE_PRESENT",
                    "path": rel,
                    "message": ".env file present; secrets should not be exposed or committed",
                }
            )
        if name in SECRET_NAMES or suffix in SECRET_SUFFIXES:
            signals.append(
                {
                    "severity": "warning",
                    "code": "SECRET_LIKE_FILENAME",
                    "path": rel,
                    "message": "Secret-like filename detected; ensure credentials are not committed",
                }
            )

        if suffix in CODE_SUFFIXES:
            parts = rel.split("/")
            in_test_dir = any(part in TEST_DIR_NAMES for part in parts[:-1])
            if not in_test_dir and not _is_test_file(name):
                has_code_outside_tests = True

    has_test_dir = any(rel.rsplit("/", 1)[-1] in TEST_DIR_NAMES for rel in dir_rels)
    has_test_file = any(_is_test_file(name) for _, name, _ in files)
    has_tests = has_test_dir or has_test_file

    for name, rel in encountered_ignored:
        if name in DEPENDENCY_DIRS:
            signals.append(
                {
                    "severity": "info",
                    "code": "DEPENDENCY_DIR_PRESENT",
                    "path": rel,
                    "message": f"Dependency directory present and skipped: {name}",
                }
            )
        if name in BUILD_ARTIFACT_DIRS:
            signals.append(
                {
                    "severity": "info",
                    "code": "BUILD_ARTIFACT_DIR_PRESENT",
                    "path": rel,
                    "message": f"Build artifact directory present and skipped: {name}",
                }
            )

    if has_code_outside_tests and not has_tests:
        signals.append(
            {
                "severity": "warning",
                "code": "MISSING_TESTS",
                "path": None,
                "message": "Code files present but no test files or test directories detected",
            }
        )
    if not ci_files:
        signals.append(
            {
                "severity": "warning",
                "code": "NO_CI_CONFIG",
                "path": None,
                "message": "No CI configuration detected",
            }
        )
    if docker_files and not has_env_example:
        signals.append(
            {
                "severity": "warning",
                "code": "DOCKER_WITHOUT_ENV_TEMPLATE",
                "path": None,
                "message": "Docker files present but no .env.example/.env.sample template found",
            }
        )
    if len(manifest_kinds & ECOSYSTEM_KINDS) > 1:
        signals.append(
            {
                "severity": "info",
                "code": "MULTIPLE_ECOSYSTEMS",
                "path": None,
                "message": "Manifests span multiple language ecosystems",
            }
        )

    notes: list[str] = []
    if truncated:
        signals.append(
            {
                "severity": "warning",
                "code": "SCAN_TRUNCATED",
                "path": None,
                "message": f"Scan truncated after {max_files} files",
            }
        )
        notes.append(f"file scan truncated at {max_files} files")

    signals.sort(key=lambda signal: (signal["code"], signal["path"] or ""))
    manifests.sort(key=lambda item: item["path"])
    docker_files.sort(key=lambda item: item["path"])
    ci_files.sort(key=lambda item: item["path"])

    folder_structure = [
        {"path": rel, "type": "directory", "depth": rel.count("/") + 1}
        for rel in sorted(dir_rels)
        if rel.count("/") + 1 <= 4
    ]
    if len(folder_structure) > MAX_FOLDER_STRUCTURE:
        folder_structure = folder_structure[:MAX_FOLDER_STRUCTURE]
        notes.append(f"folder_structure truncated at {MAX_FOLDER_STRUCTURE} entries")

    # Rank source-classified languages first, then everything else, each by
    # descending file count with a stable name tiebreak (LES-013). The derived
    # primary language is the top source language, falling back to the overall
    # top language when a repo has no source files at all.
    source_ranked = sorted(
        ((name, count) for name, count in language_counts.items() if LANGUAGE_CLASS.get(name) == "source"),
        key=lambda kv: (-kv[1], kv[0]),
    )
    other_ranked = sorted(
        ((name, count) for name, count in language_counts.items() if LANGUAGE_CLASS.get(name) != "source"),
        key=lambda kv: (-kv[1], kv[0]),
    )
    ranked = source_ranked + other_ranked
    primary_language_hints = [name for name, _ in ranked[:3]]
    if source_ranked:
        primary_language = source_ranked[0][0]
    elif ranked:
        primary_language = ranked[0][0]
    else:
        primary_language = None
    language_classes = {name: LANGUAGE_CLASS[name] for name in sorted(language_counts) if name in LANGUAGE_CLASS}

    top_level_dirs = sorted({rel.split("/")[0] for rel in dir_rels})[:50]
    manifest_paths = sorted(rel for rel, name, _ in files if name in MANIFEST_FILES)
    readme_paths = sorted(rel for rel, name, _ in files if name.lower().startswith("readme"))
    risk_flags = sorted({signal["message"] for signal in signals if signal["severity"] == "warning"})

    nodes = [
        {"label": path.name, "type": "repository", "confidence": 0.9, "evidence": ["registered repository path"]},
    ]
    for directory in top_level_dirs[:20]:
        nodes.append({"label": directory, "type": "directory", "confidence": 0.65, "evidence": [directory]})

    edges = [
        {"from": path.name, "to": node["label"], "type": "contains", "confidence": 0.75, "evidence": node["evidence"]}
        for node in nodes[1:]
    ]

    # Derive service nodes + depends_on edges from every detected compose file
    # (LES-014). Parsing is tolerant: a missing, malformed, or non-dict compose
    # file records a note and yields no services rather than raising.
    runtime_services: list[str] = []
    seen_services: set[str] = set()
    service_truncated = False
    for docker in docker_files:
        if docker["kind"] != "compose":
            continue
        compose_rel = docker["path"]
        try:
            raw = (path / compose_rel).read_text(encoding="utf-8")
            document = yaml.safe_load(raw)
        except Exception as exc:  # noqa: BLE001 - stay tolerant, never raise out of a scan
            notes.append(f"compose file could not be parsed ({exc.__class__.__name__}): {compose_rel}")
            continue
        services = document.get("services") if isinstance(document, dict) else None
        if not isinstance(services, dict):
            notes.append(f"compose file has no services mapping: {compose_rel}")
            continue
        for raw_name, body in services.items():
            if len(seen_services) >= MAX_COMPOSE_SERVICES:
                service_truncated = True
                break
            service = str(raw_name)
            if service not in seen_services:
                seen_services.add(service)
                runtime_services.append(service)
                nodes.append(
                    {"label": service, "type": "service", "confidence": 0.7, "evidence": [compose_rel]}
                )
            depends_on = body.get("depends_on") if isinstance(body, dict) else None
            if isinstance(depends_on, dict):
                dependencies = [str(dep) for dep in depends_on]
            elif isinstance(depends_on, list):
                dependencies = [str(dep) for dep in depends_on]
            else:
                dependencies = []
            for dependency in dependencies:
                edges.append(
                    {
                        "from": service,
                        "to": dependency,
                        "type": "depends_on",
                        "confidence": 0.7,
                        "evidence": [compose_rel],
                    }
                )
        if service_truncated:
            break
    if service_truncated:
        notes.append(f"compose services truncated at {MAX_COMPOSE_SERVICES}")

    summary = {
        "total_files_seen": len(files),
        "total_dirs_seen": len(dir_rels),
        "languages": sorted(language_counts),
        "primary_language": primary_language,
        "primary_language_hints": primary_language_hints,
        "language_classes": language_classes,
        "runtime_services": runtime_services,
        "has_docker": bool(docker_files),
        "has_ci": bool(ci_files),
        "has_tests": has_tests,
        "has_env_example": has_env_example,
    }

    return {
        "root_name": path.name,
        "repository_path": str(path),
        "folder_map": top_level_dirs,
        "file_count": len(files),
        "language_mix": dict(language_counts),
        "package_managers": sorted(package_managers),
        "package_manifests": manifest_paths,
        "deployment_files": sorted(deployment_files),
        "readme_files": readme_paths,
        "risk_flags": risk_flags,
        "architecture_nodes": nodes,
        "architecture_edges": edges,
        "manifests": manifests,
        "docker_files": docker_files,
        "ci_files": ci_files,
        "folder_structure": folder_structure,
        "summary": summary,
        "risk_signals": signals,
        "notes": notes,
    }
