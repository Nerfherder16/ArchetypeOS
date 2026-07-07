---
name: aos-scanner-dna-reference
description: Use when working on the ArchetypeOS repository scanner or RepositoryDNA. Triggers include scan_repository output questions, manifest or ecosystem detection (.csproj, pom.xml, go.mod), framework detection, SECRET_LIKE_FILENAME warnings on testdata/*.pem, primary_language misreads (YAML above Python), risk_signals codes, architecture_nodes and architecture_edges (contains, depends_on), .archetype/portfolio scan.json goldens, POST /repositories/{id}/scan, or adding an ecosystem or risk signal.
---

# ArchetypeOS Scanner and RepositoryDNA Reference

## 1. Overview

The repository scanner is the read-only structural profiler at the base of ArchetypeOS's Repository DNA, architecture graph, and knowledge-transfer pipelines. It walks a registered repository tree deterministically (sorted traversal, no timestamps), inventories manifests, languages, Docker/CI files, and risk signals, and emits a single dict report. The scan service persists that report as a `RepositoryDNA` row, seeds architecture nodes and edges, and writes the raw report to an artifact file.

Key jargon, defined once:

- **RepositoryDNA**: the persisted per-repository profile (SQLAlchemy model `RepositoryDNA` in `packages/aos_core/aos_core/models.py`), populated from a scan.
- **Risk signal**: a structured `{severity, code, path, message}` entry in the scan report; `risk_flags` is the legacy list of just the warning-severity messages.
- **Golden file**: a captured, human-annotated scan output checked into `.archetype/portfolio/<repo>/scan.json` as evidence from the AOS-21 reality tests.

## 2. When to use / When NOT to use

Use this skill when you need to:

- Interpret any field of a scan report, `scan.json` golden, or `RepositoryDNA` row.
- Change or extend ecosystem, framework, secret, language, or risk detection.
- Explain a scanner false positive or misclassification.

Do NOT use this skill for:

- Change gating, PR Guardian behavior, or merge process: see `aos-change-control`.
- General failure triage that is not scanner-specific: see `aos-debugging-playbook`.
- Why past scanner decisions were made and rejected alternatives: see `aos-failure-archaeology`.
- System-level invariants the scanner participates in: see `aos-architecture-contract`.
- Distillation tiers and council evidence built ON TOP of scan output: see `aos-knowledge-transfer-reference`.
- Running the API service that exposes the scan endpoints: see `aos-build-run-and-operate`.
- Test recipes and the evidence bar in general: see `aos-validation-and-qa`.

## 3. Source of truth: where the scanner lives

There is exactly ONE scanner implementation, as of 2026-07-06:

- File: `packages/aos_core/aos_core/repository_scanner.py`
- Import path: `from aos_core.repository_scanner import scan_repository, safe_repo_path`
- `apps/api/app/repository_scanner.py` does NOT exist. The `apps/api/app/` package contains only `main.py`, `routes/`, `schemas.py`. Any doc that says the scanner lives under `apps/api/app/` is stale (see Provenance: `docs/REPOSITORY_SCANNER.md` still says "Returned by scan_repository() in apps/api/app/repository_scanner.py" and "Never opens or reads file contents", both outdated).

Consumers (all in-repo, verified by grep):

| Consumer | Uses |
|---|---|
| `packages/aos_core/aos_core/services/scan.py` | `run_scan`: full scan, DNA persistence, graph seeding, artifact write |
| `apps/api/app/routes/scans.py` | `POST /repositories/{repository_id}/scan`, `GET .../scans`, `GET .../scans/{artifact_id}` |
| `apps/api/app/routes/repositories.py` | `safe_repo_path` for path validation |
| `packages/aos_core/aos_core/services/distillation.py` | imports `EXTENSIONS`, `LANGUAGE_CLASS`, `safe_repo_path` |

Read-content policy (from the module docstring): the scanner inspects paths, names, and metadata; it reads file BODIES only for (a) detected compose files (`yaml.safe_load`, tolerant) and (b) recognized manifests, byte-capped, for framework and local-dependency detection. It never writes into the scanned tree, never executes anything, never follows symlinks. `docker-compose.yml` additionally mounts the repository root read-only (`:ro`) into `api` and `worker`.

## 4. Ecosystem and manifest detection

Two lookup layers plus a suffix fallback, all in `repository_scanner.py`:

**Basename to package manager** (`MANIFEST_FILES`): `package.json` (npm), `pnpm-lock.yaml` (pnpm), `yarn.lock` (yarn), `requirements.txt` (pip), `pyproject.toml` (python), `poetry.lock` (poetry), `Cargo.toml` (cargo), `go.mod` (go), `pom.xml` (maven), `build.gradle` (gradle), `build.gradle.kts` (gradle).

**Basename to manifest kind** (`MANIFEST_KINDS`): the above plus `setup.py`, `setup.cfg`, `package-lock.json`, `alembic.ini` (python_migration), `.env.example` and `.env.sample` (env_template); JVM basenames `pom.xml`, `build.gradle`, `build.gradle.kts` map to kind `jvm`.

**Suffix fallback for .NET** (LES-016, shipped in AOS-SCAN-PRECISION-001): filenames are not fixed for .NET, so `MANIFEST_SUFFIX_KINDS = {".csproj": "dotnet", ".sln": "dotnet"}` and `MANIFEST_SUFFIX_FILES = {".csproj": "dotnet", ".sln": "dotnet"}`. The suffix branch fires only when the basename is not already in the basename maps.

**Ecosystem set**: `ECOSYSTEM_KINDS = {"python", "node", "rust", "go", "dotnet", "jvm"}`. If detected manifest kinds intersect this set in more than one member, the info-severity `MULTIPLE_ECOSYSTEMS` signal is emitted.

## 5. Framework detection from manifest bodies

Curated and conservative (AOS-DISTILL-003, aligned with LES-016). The scanner reads the bodies of at most `_MAX_MANIFESTS_READ = 100` recognized manifests, each capped at `_MANIFEST_READ_CAP = 512_000` bytes, wrapped in tolerant try/except (any single-manifest failure is skipped, never raised). Only four filenames have parsers (`_FRAMEWORK_PARSERS`): `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`.

Matching is table-only; unknown dependencies are never guessed:

- `_NPM_FRAMEWORKS`: express, react/react-dom, next, vue, @angular/core, svelte, @sveltejs/kit, @nestjs/core, fastify, koa, @remix-run/react.
- `_PY_FRAMEWORKS` (PEP 503 normalized): fastapi, flask, django, starlette, pydantic, pydantic-ai (+slim), langchain (+core), sqlalchemy, celery, tornado, aiohttp, sanic, streamlit.
- `_GO_FRAMEWORKS` (module path, exact or `<path>/` prefix so `/v4` still matches): gin, echo, fiber, gorilla-mux, chi, beego.

A malformed `pyproject.toml` falls back to a regex over quoted strings, still curated-table-only. Output is `result["frameworks"]`, a sorted deduped list; empty list when nothing curated matches.

## 6. Secret signals and the fixture-path downgrade (LES-017)

Constants, quoted exactly:

```python
SECRET_NAMES = {"id_rsa", "id_dsa", "id_ed25519", "credentials.json", "service-account.json"}
SECRET_SUFFIXES = {".pem", ".key"}
TEST_FIXTURE_DIRS = {"testdata", "tests", "test", "fixtures", "__tests__", "spec", "testfixtures"}
```

Behavior:

- A basename in `SECRET_NAMES` or a suffix in `SECRET_SUFFIXES` emits `SECRET_LIKE_FILENAME`. Contents are never read or echoed; the flag is name/path only.
- **Fixture downgrade** (AOS-SCAN-PRECISION-001, closing LES-017): if ANY path component is in `TEST_FIXTURE_DIRS` (`_is_test_fixture_path`), severity is `"info"` instead of `"warning"`. Because `risk_flags` is derived only from warning-severity signals, fixture hits drop out of `risk_flags` and therefore out of `RepositoryDNA.risk_flags`, but the signal is STILL emitted in `risk_signals` (precision, not suppression). A root-level or `config/real.pem` stays `"warning"`.
- A literal `.env` file emits `ENV_FILE_PRESENT` (warning). `.env.example` / `.env.sample` (`ENV_TEMPLATE_NAMES`) instead set `has_env_example`.
- The PR Guardian's separate secret block is intentionally unchanged by all of this (never weaken the Guardian).

Origin: scanning `gin-gonic/gin` flagged `testdata/certificate/{cert,key}.pem`, and `kubernetes/kubernetes` produced 71 `SECRET_LIKE_FILENAME` warnings from test certs, burying real hits.

## 7. Language classification and primary_language (LES-013)

`EXTENSIONS` maps 16 suffixes to language names (`.py` Python, `.ts` TypeScript, `.tsx` TypeScript React, `.js`/`.jsx` JavaScript (+React), `.go`, `.rs`, `.java`, `.cs`, `.md`, `.sh`, `.yml`/`.yaml`, `.sql`, `.html`, `.css`).

`LANGUAGE_CLASS` assigns each a coarse role: source (Python, TS/TSX, JS/JSX, Go, Rust, Java, C#, Shell, SQL), config (YAML), docs (Markdown), markup (HTML, CSS).

Why: raw file counts misread real repos. pydantic-ai counted YAML 1183 vs Python 564 (Python only 28 percent by file count), while claude-agent-sdk-python read correctly at 77 percent Python. Fix (AOS-ARCH-SEMANTICS-001, closing LES-013): rank source-classified languages first, each group by descending count with name tiebreak. `summary.primary_language` is the top SOURCE language, falling back to the overall top only when a repo has no source files. `summary.primary_language_hints` is the top 3 of the combined ranking; `summary.language_classes` exposes the classification. `language_mix` keeps raw counts for backward compatibility: treat it as file-distribution data, never as a primary-language verdict.

## 8. Risk signal catalog

All signals are `{severity, code, path, message}`; `path` is None for repo-level signals. Sorted by (code, path) for determinism.

| Code | Severity | Fires when |
|---|---|---|
| `ENV_FILE_PRESENT` | warning | a file named `.env` exists |
| `SECRET_LIKE_FILENAME` | warning, or info under a fixture dir | basename in `SECRET_NAMES` or suffix in `SECRET_SUFFIXES` |
| `MISSING_TESTS` | warning | code files (suffix in `CODE_SUFFIXES` = .py/.ts/.tsx/.js/.jsx) exist outside test dirs/files, and no test dir (`tests`/`test`/`__tests__`) or test file (`test_*.py`, `*_test.py`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.js`) found |
| `NO_CI_CONFIG` | warning | no CI file detected (`.github/workflows/*.yml|yaml` at exactly that depth, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml`, `circle.yml`) |
| `DOCKER_WITHOUT_ENV_TEMPLATE` | warning | docker files present but no `.env.example`/`.env.sample` |
| `SCAN_TRUNCATED` | warning | more than `MAX_FILES = 20000` files |
| `DEPENDENCY_DIR_PRESENT` | info | skipped `node_modules`/`.venv`/`venv` encountered |
| `BUILD_ARTIFACT_DIR_PRESENT` | info | skipped `dist`/`build`/`.next` encountered |
| `MULTIPLE_ECOSYSTEMS` | info | manifest kinds span more than one of `ECOSYSTEM_KINDS` |

Ignored dirs (pruned before descent, never traversed): `.git`, `node_modules`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `dist`, `build`, `.next`, `.turbo`, `.cache`, `.tox`, `.coverage`, `htmlcov`, plus any `*.egg-info`.

## 9. Architecture graph extraction

Nodes and edges emitted by `scan_repository`, with fixed heuristic confidences:

| Element | Type | Confidence | Evidence |
|---|---|---|---|
| Repository root node | `repository` | 0.9 | "registered repository path" |
| Top-level directory nodes (first 20) | `directory` | 0.65 | the directory name |
| Root-to-directory edges | `contains` | 0.75 | directory name |
| Compose service nodes | `service` | 0.7 | compose file path |
| Compose `depends_on` edges (list AND map form) | `depends_on` | 0.7 | compose file path |
| Manifest local-dependency edges | `depends_on` | 0.6 | `"<manifest> local dependency -> <target>"` |

Compose parsing (LES-014 compose half, AOS-ARCH-SEMANTICS-001): every detected compose file (`docker-compose.yml`, `docker-compose.yaml`, `compose.yml`, `compose.yaml`) is `yaml.safe_load`ed tolerantly; malformed or non-mapping files add a note and yield nothing. Services capped at `MAX_COMPOSE_SERVICES = 200`. `summary.runtime_services` preserves declaration order and feeds `RepositoryDNA.runtime_services`.

Manifest-derived edges (LES-014 manifest half, AOS-ARCH-EDGES-001, merged to main via PR 78 as of 2026-07-06): `_LOCAL_DEP_PARSERS` extract local path dependencies from `requirements.txt` (`-e ../pkg` and bare `./`/`../` lines), `pyproject.toml` (poetry `path =` and `tool.uv.sources` path), `package.json` (`file:` and `link:` protocols), and `go.mod` (`replace ... => ../shared`, single-line and block form). Paths are resolved relative to the manifest's directory, collapsed to TOP-LEVEL-DIRECTORY granularity, deduped, capped at `MAX_LOCAL_DEP_EDGES = 200`; paths escaping the repo root or with unresolved endpoints are skipped silently.

NOT implemented, as of 2026-07-06: source IMPORT-graph edges (edges derived from `import` statements in code). LES-014's index row is closed (compose half plus manifest half both shipped), and import-graph edges are explicitly scoped as a separate future follow-up. Do not claim the scanner reads source files to build the graph; it does not.

`run_scan` upserts these into `ArchitectureNode` / `ArchitectureEdge` DB rows (directory and service nodes parented to the root node; edges resolved by label; the DB root node is registered under both the repository name and `scan["root_name"]`).

## 10. RepositoryDNA schema and population

Model (`packages/aos_core/aos_core/models.py`, class `RepositoryDNA`, table `repository_dna`):

| Field | Type | Filled by `run_scan` with |
|---|---|---|
| `repository_id` | GUID FK, unique | the scanned repository |
| `purpose`, `maturity` | text / string | NOT set by scan (nullable) |
| `language_mix` | JSON dict | `scan["language_mix"]` (raw file counts) |
| `package_managers` | JSON list | `scan["package_managers"]` |
| `frameworks` | JSON list | `scan["frameworks"]` |
| `runtime_services` | JSON list | `scan["summary"]["runtime_services"]` |
| `deployment_files` | JSON list | `scan["deployment_files"]` |
| `risk_flags` | JSON list | `scan["risk_flags"]` (warnings only; fixture-downgraded secret hits excluded) |
| `scan_summary` | JSON dict | the ENTIRE scan report |
| `confidence` | float | hard-coded `0.65` |
| `evidence` | JSON list | `["read-only repository scanner"]` |
| (status via mixin) | | `"draft"` |

The scan report itself (return of `scan_repository`) carries the full schema documented in the module docstring: legacy keys (`folder_map`, `file_count`, `language_mix`, `package_managers`, `package_manifests`, `deployment_files`, `readme_files`, `risk_flags`, `architecture_nodes`, `architecture_edges`) plus structured keys (`root_name`, `repository_path`, `manifests`, `docker_files`, `ci_files`, `frameworks`, `folder_structure` capped at `MAX_FOLDER_STRUCTURE = 500` entries and depth 4, `summary`, `risk_signals`, `notes`).

## 11. Where scan outputs land

**Runtime artifacts**: `run_scan` writes the full report to `<artifact_root>/<project_id>/<repository_id>/repository-scan-<artifact_id>.json` with a sha256 checksum recorded in an `Artifact` row (`artifact_type="repository_scan"`). Default `artifact_root` is `./data/artifacts` (`packages/aos_core/aos_core/config.py`). Trigger and retrieval:

```bash
# cwd: repo root, API running on :8000 (see aos-build-run-and-operate)
curl -s -X POST http://localhost:8000/repositories/<repository_id>/scan
curl -s http://localhost:8000/repositories/<repository_id>/scans
curl -s http://localhost:8000/repositories/<repository_id>/scans/<artifact_id>
```

**Golden files**: `.archetype/portfolio/<repo>/scan.json` for `claude-agent-sdk-python`, `example-voting-app`, `gin`, `kubernetes`, `pydantic-ai`. These are CONDENSED, human-annotated captures from the AOS-21 reality tests (keys like `repo`, `remote_url`, `note`, `language_mix_by_file_count`), NOT raw `scan_repository` output. The clones themselves are gitignored under `repositories/`.

## 12. Worked example: annotated excerpt from `.archetype/portfolio/gin/scan.json`

```jsonc
{
  "repo": "gin-gonic/gin",                 // golden-file metadata, not a scanner key
  "package_managers": ["go"],              // go.mod detected via MANIFEST_FILES
  "summary": {
    "total_files_seen": 130,
    "total_dirs_seen": 17,
    "languages": ["Go", "Markdown", "YAML"],
    "primary_language_hints": ["Go"],      // Go is the only source language here
    "has_ci": true,                        // .github/workflows present
    "has_docker": false,
    "has_tests": false                     // gin uses *_test.go, which the
                                           // test heuristics (py/ts/js only) miss
  },
  "risk_signals": [
    { "code": "SECRET_LIKE_FILENAME", "severity": "warning",
      "path": "testdata/certificate/cert.pem", "..." : "..." },
    { "code": "SECRET_LIKE_FILENAME", "severity": "warning",
      "path": "testdata/certificate/key.pem" }
    // CAPTURE-TIME NOTE: this golden predates AOS-SCAN-PRECISION-001.
    // A re-scan today emits these with severity "info" (testdata is in
    // TEST_FIXTURE_DIRS) and they no longer appear in risk_flags.
  ],
  "architecture": { "node_count": 10, "edge_count": 9,
    "edge_types": ["contains"] }           // no compose file, no local-path
                                           // manifest deps: contains-only is
                                           // correct for gin, not a gap
}
```

This one golden exhibits both open-then-closed scanner lessons: the LES-017 fixture-cert false positive (now downgraded) and, historically, the LES-014 contains-only graph. It also shows a real remaining edge: `has_tests: false` on a heavily tested Go repo, because `_is_test_file` and `TEST_DIR_NAMES` do not cover `*_test.go` (candidate gap, unfixed as of 2026-07-06; note LES-016 predicted "likely Java/Rust too" for detection breadth).

## 13. How to add a new ecosystem or risk signal

Route the change through `aos-change-control` (work package in `.archetype/work/AOS-*.md`, TDD RED to GREEN, local gate, PR Guardian, manual merge gate). Never bypass the Guardian or the RFC process; if the change alters the report schema shape, check whether an RFC is needed first.

Files to touch, in order:

1. `apps/api/tests/test_scanner.py`: write the failing test FIRST. Follow the existing patterns: `tmp_path` fixture repos built inline (see `test_scan_detects_dotnet_jvm_rust_ecosystems` for an ecosystem, `test_secret_like_filename_fixture_aware` for a signal). Assert on `manifests` kinds, `package_managers`, and `risk_signals` code/severity/path tuples, never on brittle counts (LES-012 pattern: derive expectations from the fixture).
2. `packages/aos_core/aos_core/repository_scanner.py`: extend the constant tables. New ecosystem: add basenames to `MANIFEST_FILES` + `MANIFEST_KINDS` (or suffixes to `MANIFEST_SUFFIX_*` when filenames are not fixed) and the kind to `ECOSYSTEM_KINDS`. New risk signal: emit a `{severity, code, path, message}` dict; remember `risk_flags`/DNA only pick up `severity == "warning"`.
3. Preserve invariants the tests enforce: determinism (`test_determinism`: two scans byte-identical), read-only (`test_read_only_guarantee`: filesystem snapshot unchanged), backward-compatible legacy keys (`test_backward_compatible_keys`), tolerance (malformed inputs add notes, never raise).
4. `docs/REPOSITORY_SCANNER.md`: update the schema/signal tables (and fix its stale claims while you are there; the doc-staleness detector `tools/doc_staleness.py` covers state docs, not this reference).
5. If the change was defect-driven, record a lesson in `knowledge/wiki/lessons/` per RFC-0004, in the same change set.

Run the tests (verified working as of 2026-07-06; 25 pass):

```bash
# cwd: /path/to/ArchetypeOS repo root
# with aos_core pip-installed (pip install -e packages/aos_core):
PYTHONPATH=apps/api python -m pytest apps/api/tests/test_scanner.py -q
# without the editable install:
PYTHONPATH=apps/api:packages/aos_core python -m pytest apps/api/tests/test_scanner.py -q
# full local gate before PR:
bash scripts/pre_pr_guardian.sh
```

## 14. Task tier guide

Routing home is `aos-model-routing`; tiers here are operator guidance, candidate status.

| Task in this skill's scope | Tier |
|---|---|
| Look up a constant, signal code, or schema field | Haiku |
| Interpret a scan.json or DNA row for a known repo | Haiku |
| Add a new ecosystem via the constant tables plus tests | Sonnet |
| Add or reclassify a risk signal (severity semantics touch DNA) | Sonnet |
| Diagnose a novel scanner false positive on a real external repo | Sonnet |
| Design new edge semantics (e.g. import-graph edges) or change confidence policy | Opus |
| Change the read-content policy (what bodies the scanner may read) | Opus |

## 15. Common mistakes

- Citing `apps/api/app/repository_scanner.py` as the scanner location. It is `packages/aos_core/aos_core/repository_scanner.py`; the old path appears only in stale docs.
- Treating `language_mix` or its top entry as the primary language. Use `summary.primary_language` (source-classified, LES-013).
- Claiming the scanner reads no file bodies. It reads compose files and up to 100 byte-capped manifests, nothing else.
- Treating an info-severity `SECRET_LIKE_FILENAME` under `testdata/` as a finding to fix, or conversely assuming the signal was removed. It is downgraded, still emitted.
- Saying manifest dependency edges are missing. Compose `depends_on` and local-path manifest edges are both shipped; only source import-graph edges remain unimplemented.
- Comparing a fresh scan against `.archetype/portfolio/*/scan.json` field by field. Goldens are condensed captures from specific commits; gin's still shows pre-downgrade `warning` severities.
- Adding a warning signal without realizing it lands in `RepositoryDNA.risk_flags` and every downstream DNA consumer.
- Weakening the PR Guardian's secret block "for consistency" with the scanner's fixture downgrade. They are deliberately separate; never weaken the Guardian.

## 16. Provenance and maintenance

Authored 2026-07-06 on branch `laptop/aos-selfheal-doc-loop` (HEAD AOS-SELFHEAL-001, since merged as PR #80; everything cited here is also in origin/main unless noted). Derived from:

- `packages/aos_core/aos_core/repository_scanner.py` (all constants, caps, confidences)
- `packages/aos_core/aos_core/services/scan.py`, `packages/aos_core/aos_core/models.py`, `packages/aos_core/aos_core/config.py`
- `apps/api/app/routes/scans.py`, `apps/api/tests/test_scanner.py` (25 tests passing 2026-07-06)
- `.archetype/portfolio/{gin,kubernetes,pydantic-ai,claude-agent-sdk-python,example-voting-app}/scan.json`
- `knowledge/wiki/lessons/LES-013.md`, `LES-014.md`, `LES-016.md`, `LES-017.md`, `index.md`
- `docs/REPOSITORY_SCANNER.md` (partially stale, see below), `scripts/pre_pr_guardian.sh`

Known repo inconsistencies, as of 2026-07-06:

- `docs/REPOSITORY_SCANNER.md` still claims the scanner never reads file contents and lives under `apps/api/app/`; both superseded by the compose/manifest body reads and the aos_core move.
- `LES-014.md` and `LES-017.md` carry `## Status: open` headers while their own Content sections and `knowledge/wiki/lessons/index.md` mark them closed. Trust the index and the code.

Re-verification commands (cwd repo root):

| Fact | Re-check |
|---|---|
| Scanner location and single implementation | `find . -name repository_scanner.py -not -path "*/.git/*" \| grep -v __pycache__` |
| Manifest/suffix/ecosystem tables | `grep -n "MANIFEST_SUFFIX_KINDS\|ECOSYSTEM_KINDS" packages/aos_core/aos_core/repository_scanner.py` |
| Fixture dirs and secret sets | `grep -n "TEST_FIXTURE_DIRS\|SECRET_NAMES\|SECRET_SUFFIXES" packages/aos_core/aos_core/repository_scanner.py` |
| Caps (20000/500/200/200/512000/100) | `grep -n "MAX_FILES\|MAX_FOLDER_STRUCTURE\|MAX_COMPOSE_SERVICES\|MAX_LOCAL_DEP_EDGES\|_MANIFEST_READ_CAP\|_MAX_MANIFESTS_READ" packages/aos_core/aos_core/repository_scanner.py` |
| DNA confidence 0.65 and evidence string | `grep -n "dna.confidence\|dna.evidence" packages/aos_core/aos_core/services/scan.py` |
| Artifact path scheme and artifact_root default | `grep -n "artifact_dir\|artifact_root" packages/aos_core/aos_core/services/scan.py packages/aos_core/aos_core/config.py` |
| Scan endpoints | `grep -n "@router" apps/api/app/routes/scans.py` |
| Scanner test count and pass state | `PYTHONPATH=apps/api:packages/aos_core python -m pytest apps/api/tests/test_scanner.py -q` |
| LES-013/014/016/017 status | `grep -n "LES-01[3467]" knowledge/wiki/lessons/index.md` |
| Import-graph edges still unimplemented | `grep -n "ast\|import_graph\|imports" packages/aos_core/aos_core/repository_scanner.py` (expect no import-parsing code) and `grep -n "import-graph\|import graph" knowledge/wiki/lessons/LES-014.md` |
| AOS-ARCH-EDGES-001 merged | `git log origin/main --oneline --grep ARCH-EDGES` |
