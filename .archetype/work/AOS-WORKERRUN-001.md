# AOS-WORKERRUN-001 — Worker Runs Scan/Digest Jobs (RFC-0006 Phase 2)

## Status

In Progress

## Origin

RFC-0006 (Accepted) Phase 2. AOS-CORE-001 (merged, PR #45) put the domain layer in `aos_core`; now the worker imports it and runs real jobs off the Redis queue. This delivers the original AOS-18 goal's step 1: repository scans and digests as queued jobs. Plane AOS-18 (In Progress — 3-phase tracker). Sprint 5 package 4.

## Verified Baseline

Confirmed by inspection:

- `apps/worker/app/worker.py`: own `engine`/`SessionLocal` from `.config`; `jobs_table()` via `Table` reflection; `mark_job(job_id, status, result, error)` (increments `attempts` on "running", sets result/error/finished_at on completed/failed); `run_job(job_id)` is a STUB producing a test result; `main()` = `brpop` loop calling `run_job`, catching exceptions → `mark_job(failed)`. `QUEUE = "archetypeos:jobs"`.
- `apps/worker/app/config.py`: Settings (database_url, redis_url, artifact_root, repository_root) — duplicates `aos_core.config.Settings` (which also has cors_origins) for the worker's needs.
- `POST /jobs` (api) enqueues `lpush archetypeos:jobs <job.id>` with `job_type`, `repository_id`/`project_id`, `payload`. Job model has `attempts`, `status`, `result`, `error`, `started_at`, `finished_at`.
- `aos_core.services.scan.run_scan(repository_id, db)` persists a scan and returns a dict; `aos_core.services.digest.build_digest(project_id, db)` returns an unpersisted `NightlyDigest` (the api route adds/commits it).
- `apps/worker/Dockerfile`: context `./apps/worker`, `CMD python -m app.worker`. compose worker `build.context: ./apps/worker`. Worker `requirements.txt`: sqlalchemy, psycopg[binary], redis, pydantic-settings, pytest.
- CI `worker-tests`: `pip install -r apps/worker/requirements.txt` then `PYTHONPATH=apps/worker pytest apps/worker/tests`. `test_worker.py` has 1 test (queue name).

## In-Scope Files

- `apps/worker/app/worker.py` (dispatch + retries via aos_core), `apps/worker/app/config.py` (DELETE — use aos_core.config)
- `apps/worker/requirements.txt` (drop what aos_core provides; keep redis, pytest), `apps/worker/Dockerfile` (repo-root context + install aos_core), `docker-compose.yml` (worker service build)
- `.github/workflows/ci.yml` (worker-tests installs aos_core)
- `apps/worker/tests/test_worker.py` (end-to-end scan-job test + retry test)
- state docs + this spec (fold PR #45 reconciliation in)

## Out-of-Scope

- dashboard enqueue controls + scheduler (Phase 3, AOS-SCHED-001)
- new job types beyond repository_scan / project_digest / test
- changing the api's `POST /jobs` (already enqueues correctly)
- schema changes

## Design

- **Worker imports aos_core**: `from aos_core.config import get_settings`, `from aos_core.database import SessionLocal`, `from aos_core.models import Job`, `from aos_core.services.scan import run_scan`, `from aos_core.services.digest import build_digest`. Delete `apps/worker/app/config.py`. Use `aos_core.database.SessionLocal` (same DATABASE_URL env). Replace `jobs_table()` reflection with ORM `Job` reads/writes in `mark_job`.
- **Dispatch** in `run_job(job_id)`: load `Job`; `mark_job(running)` (increments attempts); on `job_type`:
  - `"repository_scan"`: `result = run_scan(job.repository_id, db)` → `mark_job(completed, result={"scanned": job.repository_id, "artifact": ...})` (store a compact summary, not the whole report).
  - `"project_digest"`: `digest = build_digest(job.project_id, db); db.add(digest); db.commit(); db.refresh(digest)` → `mark_job(completed, result={"digest_id": digest.id, "summary": digest.summary})`.
  - `"test"` / unknown: the existing stub result (backward compat — the alpha-run test job and `test_worker` stay valid).
- **Retries**: `MAX_ATTEMPTS = 3`. In `main()`'s exception handler: if the job's `attempts < MAX_ATTEMPTS`, re-enqueue (`lpush QUEUE job_id`) and set status back to `queued`; else `mark_job(failed, error=...)`. (attempts is incremented by `mark_job(running)` each pass, so a job runs at most MAX_ATTEMPTS times.)
- **Docker**: worker Dockerfile context → repo root (`COPY packages/aos_core` + `pip install`, then `COPY apps/worker/...`); compose worker `build: {context: ., dockerfile: apps/worker/Dockerfile}`. requirements.txt keeps `redis`, `pytest` (aos_core provides sqlalchemy/psycopg/pydantic-settings).
- **CI**: `worker-tests` job adds `pip install -e ./packages/aos_core`.

## Acceptance Criteria

- Worker runs a real scan job — evidence: `test_run_scan_job` — set up a sqlite DB (`aos_core.database.Base.metadata.create_all`), a project + repository pointing at a demo repo dir, insert a `repository_scan` Job, call `run_job(job_id)`; assert job status `completed` and a scan artifact row + RepositoryDNA exist.
- Worker runs a digest job — evidence: `test_run_digest_job` — insert a `project_digest` Job, `run_job`; assert `completed` and a `NightlyDigest` row exists with the digest id in `result`.
- Retry then fail — evidence: `test_retry_exhaustion` — a job whose type dispatch raises (e.g. unknown repository_id → run_scan raises) re-enqueues up to MAX_ATTEMPTS then marks `failed` (assert attempts and final status).
- Backward compat — evidence: `test_worker_queue_name_is_stable` still passes; a `test` job still completes with the stub result.
- Nothing else broken — evidence: worker suite green with aos_core installed; api suite (69) unaffected; ruff/compileall exit 0.
- Postgres path — evidence: CI compose-smoke green (worker image built from the new context, boots against Postgres).

## Verification Plan

Level 2: `pip install -e ./packages/aos_core`; ruff/compileall; `PYTHONPATH=apps/worker pytest apps/worker/tests` (new e2e tests). Level 4 (local): Orchestrator runs the enqueue→run_job→artifact-exists test on sqlite directly (the real proof the worker executes domain logic). Level 3: CI worker-tests (installs aos_core) + compose-smoke (worker image from new context). Merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): worker dispatch + retries + Docker/CI + tests. Orchestrator (Opus 4.8): spec, independent run of the end-to-end scan-job test, review of Docker/compose diffs, PR, gate.

## Board Linkage

- Plane: AOS-18 (In Progress — Phase 2 of 3), Sprint 5 cycle `8bc59801-82c5-4550-b188-9f15323a1ddc`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
