from __future__ import annotations
from collections import Counter
from pathlib import Path

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

DEPLOYMENT_FILES = {"Dockerfile", "docker-compose.yml", "compose.yml", "kubernetes.yml", "helmfile.yaml"}
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
}
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".pytest_cache"}


def safe_repo_path(repository_root: Path, local_path: str) -> Path:
    root = repository_root.resolve()
    candidate = (root / local_path).resolve() if not Path(local_path).is_absolute() else Path(local_path).resolve()
    if root not in candidate.parents and candidate != root:
        raise ValueError(f"Repository path must be under repository root: {root}")
    if not candidate.exists() or not candidate.is_dir():
        raise FileNotFoundError(f"Repository path does not exist: {candidate}")
    return candidate


def scan_repository(path: Path) -> dict:
    files: list[Path] = []
    dirs: list[str] = []
    for item in path.rglob("*"):
        if any(part in IGNORED_DIRS for part in item.relative_to(path).parts):
            continue
        if item.is_dir():
            dirs.append(str(item.relative_to(path)))
        elif item.is_file():
            files.append(item)

    language_counts = Counter()
    package_managers: set[str] = set()
    deployment_files: list[str] = []
    risk_flags: list[str] = []

    for file_path in files:
        rel = str(file_path.relative_to(path))
        language = EXTENSIONS.get(file_path.suffix.lower())
        if language:
            language_counts[language] += 1
        if file_path.name in MANIFEST_FILES:
            package_managers.add(MANIFEST_FILES[file_path.name])
        if file_path.name in DEPLOYMENT_FILES or rel in DEPLOYMENT_FILES:
            deployment_files.append(rel)
        if file_path.name == ".env":
            risk_flags.append(".env file present; verify secrets are not committed")

    top_level_dirs = sorted({d.split("/")[0] for d in dirs if d})[:50]
    manifest_paths = sorted(str(f.relative_to(path)) for f in files if f.name in MANIFEST_FILES)
    readme_paths = sorted(str(f.relative_to(path)) for f in files if f.name.lower().startswith("readme"))

    nodes = [
        {"label": path.name, "type": "repository", "confidence": 0.9, "evidence": ["registered repository path"]},
    ]
    for directory in top_level_dirs[:20]:
        nodes.append({"label": directory, "type": "directory", "confidence": 0.65, "evidence": [directory]})

    edges = [
        {"from": path.name, "to": node["label"], "type": "contains", "confidence": 0.75, "evidence": node["evidence"]}
        for node in nodes[1:]
    ]

    return {
        "folder_map": top_level_dirs,
        "file_count": len(files),
        "language_mix": dict(language_counts),
        "package_managers": sorted(package_managers),
        "package_manifests": manifest_paths,
        "deployment_files": sorted(deployment_files),
        "readme_files": readme_paths,
        "risk_flags": sorted(set(risk_flags)),
        "architecture_nodes": nodes,
        "architecture_edges": edges,
    }
