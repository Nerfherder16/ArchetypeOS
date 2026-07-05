# RFC-0006 — Shared Core Domain Library

## Status

Accepted (operator-approved 2026-07-05). Phase 1 = AOS-CORE-001; Phase 2 = AOS-WORKERRUN-001; Phase 3 = AOS-SCHED-001.

## Problem

AOS-18 (worker pipeline) needs the worker to run repository scans and digest aggregation so the system operates on a schedule without a human clicking. But the domain logic lives entirely in `apps/api`:

- `apps/api/app/repository_scanner.py` (384 lines, stdlib-only) — the scanner
- scan persistence (upsert architecture nodes/edges preserving ids + manual corrections, versioned artifacts, DNA) is **inline** in `main.py` `scan_registered_repository` (lines ~108–283)
- digest aggregation is **inline** in `main.py` `_build_digest` (lines ~487–625)
- `models.py`, `database.py`, `config.py` — shared foundation

The worker (`apps/worker`, 81 lines) is a separate package with its own Docker build context (`context: ./apps/worker`) and does not import api code. It reaches the DB via SQLAlchemy `Table` reflection and today only runs a stub "test job." It cannot run a real scan without the scanner, the models, and the persistence logic.

The operator selected the shared-library architecture: extract the domain core into a package both apps import, so the worker runs scans **in-process** (true compute offload from the API), with no logic duplication and one source of truth.

## Decision

Create an installable Python package **`aos_core`** containing the domain layer, consumed by both `apps/api` and `apps/worker`.

### Target structure

```
packages/aos_core/
  pyproject.toml
  aos_core/
    __init__.py
    config.py         # moved from apps/api/app/config.py
    database.py       # moved (engine, Base, get_db, init_db)
    models.py         # moved (all 20 ORM tables)
    repository_scanner.py   # moved (stdlib-only scanner)
    services/
      __init__.py
      scan.py         # NEW: run_scan(repository_id, db) — persistence extracted from main.py:108-283
      digest.py       # NEW: build_digest(project_id, db) — extracted from main.py:487-625
apps/api/app/
    main.py           # FastAPI routes only; import aos_core.{models,database,services,...}
    schemas.py        # stays (Pydantic API contracts — API-specific, not domain)
    alembic/          # stays with the api (owns migrations); env.py targets aos_core.database.Base
apps/worker/app/
    worker.py         # job_type dispatch → aos_core.services.scan.run_scan / digest.build_digest
```

`schemas.py` (Pydantic request/response models) stays in `apps/api` — it is the API contract layer, not domain logic. Alembic stays with the api (one owner of migrations); `env.py` retargets to `aos_core.database.Base` (which now holds the metadata).

### Packaging / Docker

Both Dockerfiles change their build context to the **repo root** so they can copy `packages/aos_core`:

- `apps/api/Dockerfile` and `apps/worker/Dockerfile` each `COPY packages/aos_core` + `pip install ./packages/aos_core` + copy their own `app/`.
- `docker-compose.yml`: api/worker `build.context` → `.` with `dockerfile: apps/api/Dockerfile` (and worker's). The compose-smoke CI job exercises both.
- Worker `requirements.txt` gains what `aos_core` needs (it already has sqlalchemy, psycopg, redis, pydantic-settings); `aos_core`'s `pyproject.toml` declares its deps so `pip install ./packages/aos_core` pulls them.

### Phasing (three packages, each independently verifiable)

- **Phase 1 — AOS-CORE-001 (extract, api-only, ZERO behavior change).** Create `aos_core`; move config/database/models/scanner; extract `services/scan.py` + `services/digest.py`; rewrite `main.py` to import from `aos_core`; retarget alembic env.py; restructure the api Docker build context; update `apps/api/tests/conftest.py` imports. Success = all 67 API tests pass unchanged, no-drift alembic still holds, compose-smoke green. This is the big mechanical move, gated by the existing test suite proving behavior is identical.
- **Phase 2 — AOS-WORKERRUN-001 (worker runs jobs).** Worker imports `aos_core`; `worker.py` dispatches `job_type` `repository_scan` → `run_scan`, `project_digest` → `build_digest`; attempt-based retry (re-enqueue up to N, then `failed`); worker Docker restructure. Success = an end-to-end test (enqueue a scan job → worker runs it → versioned artifact + DNA exist), mirroring the Alpha-run job proof, plus compose-smoke.
- **Phase 3 — AOS-SCHED-001 (schedule + surface).** Dashboard "enqueue scan / run digest as job" controls; a scheduler that enqueues the nightly digest per project. Success = Level 4 browser drive + a scheduled-enqueue proof on teevee-1. Drafts-only and human approval unchanged — execution is automated, decisions never are.

## Alternatives considered

- **Worker triggers API over HTTP** (the recommended-but-not-chosen option): worker calls the existing endpoint; zero restructure, but the API does the CPU and it couples the worker to API availability. Rejected by operator in favor of true offload.
- **Vendor api code into the worker image** (copy `apps/api/app` into the worker): works without a shared package but duplicates the source in two images and invites drift. Rejected.
- **Monorepo tool (uv/poetry workspaces)**: cleaner dependency management but adds tooling the project doesn't yet use; `pip install ./packages/aos_core` is sufficient for now. Deferred.

## Risks

- **Build-context change touches both images' packaging** — the compose-smoke CI job is the guardrail; any packaging break turns it red. Phase 1 is scoped so the api path is proven before the worker path changes.
- **Import/test-harness churn** — `conftest.py` imports `app.main`; after extraction it may import `aos_core` for models. Contained in Phase 1 and gated by the unchanged 67-test suite.
- **Alembic retarget** — `env.py` must point at `aos_core.database.Base`; the no-drift autogenerate check (from AOS-ALEMBIC-001) re-run in Phase 1 proves the metadata still matches.
- **Guardian test-enforcement paths** — the guardian keys on `apps/api/app/` and `apps/worker/app/`; moving code to `packages/aos_core/` means guardian test-enforcement should extend to it (a small guardian evolution in Phase 1, cited by a lesson per RFC-0004).

## Effort

Three packages. Phase 1 is the largest (mechanical extraction + api Docker restructure) but de-risked by the existing suite. Phases 2–3 are additive.

## Acceptance criteria (for this RFC)

- Operator approves the `aos_core` structure, the Docker build-context change, and the three-phase plan.
- On approval, Phase 1 (AOS-CORE-001) proceeds; Plane AOS-18 is reshaped into the three phase items.

## Dependencies

- AOS-ALEMBIC-001 (merged) — migrations must retarget cleanly to `aos_core.database.Base`.
- Unblocks AOS-19 (council can live in `aos_core.services`), AOS-23 (lessons/knowledge read path).
