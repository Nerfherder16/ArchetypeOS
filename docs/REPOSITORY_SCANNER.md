# Repository Scanner

## Purpose

The Repository Scanner produces a deterministic, read-only report describing a registered repository's structure, ecosystems, and basic risk signals. It is the foundation for Repository DNA, architecture graph seeding, and future PR Guardian and knowledge work.

## Read-Only Guarantee

- Inspects paths, names, and filesystem metadata only.
- Never opens or reads file contents. Secret-like files are flagged by name/path only; contents are never read or echoed.
- Never writes into the scanned repository.
- Never executes code found in the scanned repository.
- Never follows symlinks.
- The ignore list (`IGNORED_DIRS`) is pruned from `os.walk` before descent, so ignored directories such as `node_modules`, `.venv`, `venv`, `__pycache__`, `dist`, `build`, `.next`, and caches are never traversed into.

## Report Schema

Returned by `scan_repository()` in `apps/api/app/repository_scanner.py`.

Legacy keys (present since the original scanner; unchanged shape):

| Key | Type | Description |
| --- | --- | --- |
| `folder_map` | list[str] | top-level directory names |
| `file_count` | int | number of non-ignored files |
| `language_mix` | dict[str, int] | language -> file count |
| `package_managers` | list[str] | detected package managers |
| `package_manifests` | list[str] | manifest file paths |
| `deployment_files` | list[str] | deployment file paths |
| `readme_files` | list[str] | readme file paths |
| `risk_flags` | list[str] | warning-severity messages |
| `architecture_nodes` | list[dict] | graph nodes |
| `architecture_edges` | list[dict] | graph edges |

New keys (added by AOS-RUNTIME-002):

| Key | Type | Description |
| --- | --- | --- |
| `root_name` | str | repository directory name |
| `repository_path` | str | path that was scanned |
| `manifests` | list[dict] | `{path, kind}`, kind is an ecosystem tag |
| `docker_files` | list[dict] | `{path, kind}`, kind is `dockerfile` or `compose` |
| `ci_files` | list[dict] | `{path, kind}`, kind is `github_actions`, `gitlab`, `jenkins`, or `circleci` |
| `folder_structure` | list[dict] | `{path, type, depth}`, directories up to depth 4 |
| `summary` | dict | aggregate counts and flags (see below) |
| `risk_signals` | list[dict] | `{severity, code, path, message}` structured signals |
| `notes` | list[str] | truncation and diagnostic notes |

`summary` fields: `total_files_seen`, `total_dirs_seen`, `languages`, `primary_language_hints` (top 3 non-markup languages by file count), `has_docker`, `has_ci`, `has_tests`, `has_env_example`.

The new keys are a strict superset of the legacy report. No legacy key was removed or reshaped, so the `POST /repositories/{id}/scan` endpoint, `RepositoryDNA` persistence, and artifact writing required zero changes.

## Risk Signal Codes

| Code | Severity | Meaning |
| --- | --- | --- |
| `ENV_FILE_PRESENT` | warning | a `.env` file exists; secrets should not be exposed or committed |
| `SECRET_LIKE_FILENAME` | warning | a filename or suffix matches known secret patterns (e.g. `id_rsa`, `*.pem`, `*.key`, `credentials.json`) |
| `DEPENDENCY_DIR_PRESENT` | info | a dependency directory (`node_modules`, `.venv`, `venv`) was present and skipped |
| `BUILD_ARTIFACT_DIR_PRESENT` | info | a build artifact directory (`dist`, `build`, `.next`) was present and skipped |
| `MISSING_TESTS` | warning | code files exist outside test directories but no test files or test directories were found |
| `NO_CI_CONFIG` | warning | no CI configuration file was detected |
| `DOCKER_WITHOUT_ENV_TEMPLATE` | warning | Docker files exist but no `.env.example`/`.env.sample` template was found |
| `MULTIPLE_ECOSYSTEMS` | info | manifests span more than one language ecosystem |
| `SCAN_TRUNCATED` | warning | the file scan stopped after `MAX_FILES` (20000) files |

## Determinism

- The report contains no timestamps.
- Directory and file traversal uses `os.walk` with `dirnames`/`filenames` sorted at every level, and all list-valued outputs are sorted before being returned.
- A `MAX_FILES` guard (20000) truncates file collection deterministically and records a `SCAN_TRUNCATED` signal plus a note when triggered. `folder_structure` has its own cap (`MAX_FOLDER_STRUCTURE` = 500).
- Scanning the same repository twice with no filesystem changes produces an identical report.

## Integration

- `POST /repositories/{repository_id}/scan` calls `scan_repository()` and returns the full report under `summary` in the response body.
- The report is persisted to `RepositoryDNA.scan_summary` alongside the existing legacy-derived fields (`language_mix`, `package_managers`, `deployment_files`, `risk_flags`).
- The report is also serialized to a JSON artifact and written under the ArchetypeOS-owned artifact root (`settings.artifact_root`, keyed by project and repository id) — never inside the scanned repository. The artifact is checksummed with `sha256` and recorded as an `Artifact` row (`artifact_type: repository_scan`).

## Future Work

- AOS-RUNTIME-003: persist scan history over time instead of a single latest snapshot.
- AOS-PRG-002: PR Guardian consuming scanner output (e.g. risk signals) as part of pull request checks.
- AOS-ARCH-001: Architecture Spine Graph built from scanner-derived nodes and edges.
