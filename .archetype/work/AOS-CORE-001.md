# AOS-CORE-001 — Extract aos_core Shared Package (RFC-0006 Phase 1)

## Status

In Progress

## Origin

RFC-0006 (Accepted, operator-approved 2026-07-05) Phase 1. Extract the domain layer into an installable `aos_core` package that both apps import, so the worker (Phase 2) can run scans in-process. **Zero behavior change** — the existing 67-test suite + alembic no-drift + compose-smoke are the oracles. Plane AOS-18. Sprint 5 package 3.

## Verified Baseline

Confirmed by inspection:

- `apps/api/app/`: `config.py` (22), `database.py` (30), `models.py` (321, incl. GUID/JSONField TypeDecorators, AuditMixin, new_id, now_utc, 20 tables), `repository_scanner.py` (384, stdlib-only), `schemas.py` (285, Pydantic), `main.py` (653, FastAPI routes).
- Scan persistence is inline in `main.py:scan_registered_repository` (~108–283): loads repo, `scan_repository`, upserts architecture nodes/edges preserving ids + `manual_correction`, writes a versioned artifact, updates `RepositoryDNA`, sets `last_scanned_at`.
- Digest aggregation is inline in `main.py:_build_digest` (~487–625).
- `main.py` imports `from .config/.database/.models/.repository_scanner/.schemas`.
- `apps/api/alembic/env.py` imports `from app.database import Base` + `import app.models`; `versions/0001_baseline.py` has `import app.models`.
- `apps/api/tests/conftest.py` imports `from app.database import Base, get_db` and `from app.main import app, settings`; test invocation `PYTHONPATH=apps/api pytest apps/api/tests`.
- CI `api-tests` job: `pip install -r apps/api/requirements.txt` then `PYTHONPATH=apps/api pytest apps/api/tests`. `apps/api/Dockerfile` build context `./apps/api`; compose api `build.context: ./apps/api`.
- The worker is NOT touched in Phase 1 (its context stays `./apps/worker`).

## In-Scope Files

- `packages/aos_core/pyproject.toml` (new), `packages/aos_core/aos_core/__init__.py` + `config.py` + `database.py` + `models.py` + `repository_scanner.py` (moved) + `services/__init__.py` + `services/scan.py` + `services/digest.py` (new, extracted)
- `apps/api/app/config.py`, `database.py`, `models.py`, `repository_scanner.py` — DELETED (moved to aos_core)
- `apps/api/app/main.py` — imports retargeted to `aos_core.*`; scan/digest route bodies delegate to services
- `apps/api/app/schemas.py` — stays; retarget any `from .models`/`from .config` imports to `aos_core.*` if present
- `apps/api/alembic/env.py`, `apps/api/alembic/versions/0001_baseline.py` — `app.` → `aos_core.` for Base/models
- `apps/api/tests/conftest.py` — `from app.database` → `from aos_core.database`; keep `from app.main import app`
- `apps/api/requirements.txt` — add `-e ./packages/aos_core` is NOT valid in a plain requirements install-from-context; instead CI/Docker install aos_core separately (see Design)
- `apps/api/Dockerfile`, `docker-compose.yml` (api service only), `.github/workflows/ci.yml` (api-tests + web-e2e jobs that run pytest)
- `tools/pr_guardian.py` (extend test-enforcement to `packages/aos_core/`), `apps/api/tests/test_guardian_evolution.py` (cases)
- `knowledge/wiki/lessons/LES-010.md` + `index.md` (guardian change → lesson)
- `docs/CAPABILITY_MAP.md`, `docs/CONCRETE_BUILD_PATH.md` or a short `docs/ARCHITECTURE_PACKAGES.md` note; state docs + this spec (fold RFC-0006 commit + note; PR #44 already reconciled in state docs? verify)

## Out-of-Scope

- worker changes (Phase 2); any behavior/schema change; new endpoints; schemas moving out of api

## Design

- **Package**: `packages/aos_core/pyproject.toml` (name `aos_core`, deps: sqlalchemy, psycopg[binary], pydantic-settings — matching what the moved modules need). `aos_core/` holds config/database/models/repository_scanner (moved verbatim, internal relative imports preserved: database's `from . import models`, etc.) + `services/scan.py` (`run_scan(repository_id, db)` — the extracted persistence body, calling `get_settings()` internally) + `services/digest.py` (`build_digest(project_id, db)`).
- **api consumes core**: `main.py` imports `from aos_core.config import get_settings`, `from aos_core.database import engine, get_db, init_db`, `from aos_core.models import ...`, `from aos_core.repository_scanner import safe_repo_path, scan_repository`, `from aos_core.services.scan import run_scan`, `from aos_core.services.digest import build_digest`, `from .schemas import ...`. The scan route becomes a thin wrapper returning `run_scan(...)`; the digest route returns `build_digest(...)`. Route signatures, response_models, status codes, and 404 behavior UNCHANGED.
- **Installability**: `aos_core` is pip-installed (editable locally/CI, regular in Docker). Local/CI: `pip install -e ./packages/aos_core`. Tests still run `PYTHONPATH=apps/api pytest apps/api/tests` (aos_core resolves via the editable install). Docker api: build context → repo root; Dockerfile `COPY packages/aos_core` + `pip install ./packages/aos_core` + `COPY apps/api/...`; compose api `build: {context: ., dockerfile: apps/api/Dockerfile}`.
- **alembic retarget**: `env.py` `from aos_core.database import Base` + `import aos_core.models`; baseline `import aos_core.models`. The no-drift autogenerate must still be empty.
- **guardian**: `check_tests_for_code_changes` — a change under `packages/aos_core/` requires a test change (`apps/api/tests/` or `packages/aos_core/tests/`), else BLOCK `missing-core-tests` (override `TESTS`). Mirror api/worker. Cite LES-010.
- **LES-010**: moving code across a package boundary must carry its test-enforcement with it, or the guardian goes blind to the moved code.

## Acceptance Criteria

- Package extracted, api imports it — evidence: `apps/api/app/{config,database,models,repository_scanner}.py` gone; `main.py` imports `aos_core.*`; `run_scan`/`build_digest` in `aos_core/services/`.
- Zero behavior change — evidence: `pip install -e ./packages/aos_core` then `PYTHONPATH=apps/api pytest apps/api/tests` → **67 passed, unchanged**; ruff/compileall exit 0 over `packages tools apps`.
- Alembic still matches models — evidence: `alembic upgrade head` on fresh sqlite → 21 tables; autogenerate probe → **0 schema ops** (with `aos_core.models`).
- Docker/compose/CI updated coherently — evidence: compose api `build.context: .`; Dockerfile installs aos_core; CI api-tests + web-e2e install `-e ./packages/aos_core`; compose-smoke green on the PR (the Docker proof).
- Guardian guards the new boundary — evidence: `test_core_change_requires_tests` (+ clean case); all prior guardian tests unchanged.
- Nothing weakened — evidence: full suite green; no endpoint/schema/behavior change.

## Verification Plan

Level 2: `pip install -e ./packages/aos_core`; ruff/compileall/pytest (67). Level 4 (local): alembic round-trip + no-drift with `aos_core.models`. Level 3: CI api-tests, web-e2e (both now install aos_core), and **compose-smoke** (the api image built from the new context with aos_core installed + alembic + entrypoint) — the authoritative proof of the Docker restructure. Merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): the whole extraction — must prove `pip install -e` + 67 tests + no-drift locally before returning. Orchestrator (Opus 4.8): spec, independent re-run of the full suite + alembic no-drift, careful review of the Docker/compose/CI diffs (compose-smoke is CI-only), guardian re-verification, lesson, PR, gate.

## Board Linkage

- Plane: AOS-18 (In Progress, high — Phase 1 tracker), Sprint 5 cycle `8bc59801-82c5-4550-b188-9f15323a1ddc`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
