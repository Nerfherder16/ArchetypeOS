# AOS-APIROUTES-001 — Split API routes by domain (control-plane hardening)

## Status

In Progress

## Origin

Lead-Architect critique (operator-relayed 2026-07-05): `apps/api/app/main.py` has grown to **487 lines / 39 routes across ~13 domains** and just gained the council routes (PR #49). Split routes by domain **before the API grows further**. Pure, behavior-preserving refactor — no new endpoints, no schema change, no behavior change. Operator-directed as the immediate next package (chose "route split first, then AOS-COUNCIL-002"). Not tied to a roadmap phase; a control-plane hardening task. Plane: new hardening issue.

## Verified Baseline

Confirmed by inspection:

- `apps/api/app/main.py` (487 lines): creates `app = FastAPI(...)`, adds `CORSMiddleware` from `settings.cors_origin_list`, an `on_startup` (mkdir artifact_root + `init_db`), a `slugify` helper (used only by `create_project`), `/health`, and **39 route handlers** decorated `@app.<verb>(...)`. Full inventory below.
- **Redis + tests (the load-bearing subtlety):** three routes create a client via `redis.Redis.from_url(settings.redis_url)` (jobs `POST /jobs`, schedules `POST /schedules/{id}/run`, council `POST /projects/{id}/council-reviews`). The api tests monkeypatch **`main.redis.Redis.from_url`** (`test_jobs_api.py`, `test_schedules_api.py`, `test_council_api.py`). That patches the `redis.Redis` **class attribute** (global to the process, reached via `app.main`'s `redis` import), so it applies no matter which module calls `redis.Redis.from_url(...)` — **provided `app.main` still `import redis`** so `main.redis` resolves. This must be preserved.
- Tests import `from app.main import app, settings` (`conftest.py`) and `import app.main as main` (the FakeRedis tests). Both must keep working unchanged.
- `apps/api/app/` currently: `__init__.py`, `main.py`, `schemas.py` (no `routes/` package yet). Guardian `CODE_PREFIXES` includes `apps/api/app/`; a code-path PR needs Acceptance Evidence + api tests present (they are — 92).

## Route inventory (must be preserved exactly — same paths, verbs, response_models, status codes, behavior)

- **projects** (3): `POST /projects`, `GET /projects`, `GET /projects/{project_id}`
- **repositories** (3): `POST /projects/{project_id}/repositories`, `GET /projects/{project_id}/repositories`, `GET /repositories/{repository_id}/dna`
- **scans** (3): `POST /repositories/{repository_id}/scan`, `GET /repositories/{repository_id}/scans`, `GET /repositories/{repository_id}/scans/{artifact_id}`
- **architecture** (3): `GET /projects/{project_id}/architecture`, `PATCH /architecture/nodes/{node_id}`, `PATCH /architecture/edges/{edge_id}`
- **jobs** (3): `POST /jobs`, `GET /jobs/{job_id}`, `GET /projects/{project_id}/jobs`
- **schedules** (6): `POST /projects/{project_id}/schedules`, `GET /projects/{project_id}/schedules`, `GET /schedules/{schedule_id}`, `PATCH /schedules/{schedule_id}`, `DELETE /schedules/{schedule_id}`, `POST /schedules/{schedule_id}/run`
- **artifacts** (2): `POST /artifacts`, `GET /projects/{project_id}/artifacts`
- **decisions** (9, the decision-intelligence domain): decisions (3) + research-notes (3) + recommendations (3)
- **digests** (3): `POST /projects/{project_id}/digests`, `GET /projects/{project_id}/digests`, `GET /digests/{digest_id}`
- **council** (3): `POST /projects/{project_id}/council-reviews`, `GET /projects/{project_id}/council-reviews`, `GET /council-reviews/{review_id}`
- **health** (1): `GET /health` — stays in `main.py` (app-level)

Total = 39 + health.

## In-Scope Files

- `apps/api/app/routes/__init__.py` (new)
- `apps/api/app/routes/projects.py`, `repositories.py`, `scans.py`, `architecture.py`, `jobs.py`, `schedules.py`, `artifacts.py`, `decisions.py`, `digests.py`, `council.py` (new — one `APIRouter` each)
- `apps/api/app/main.py` (reduced to: app + CORS + `on_startup` + `/health` + `include_router(...)` for each; **retains `import redis`** so `main.redis` resolves for tests)
- `apps/api/tests/test_route_inventory.py` (new — freezes the (method, path) set as a refactor guard)
- `docs/HANDOFF.md`, `docs/ORCHESTRATOR_PLAYBOOK.md` (document the env-pinned branch constraint — operator Decision 2a), state docs + this spec

## Out-of-Scope

- Any new endpoint, response-model, status-code, or behavior change. No `schemas.py` split (routers import from `.schemas` as today). No knowledge read path (AOS-23). No changes to `aos_core`, worker, web, CI, or Docker. No auth/versioning. Do NOT rename existing test files or change their assertions (except adding the new inventory test).

## Design

- Each `routes/<domain>.py` defines `router = APIRouter()` and moves that domain's handlers verbatim (bodies unchanged), decorated `@router.<verb>(...)` with identical path/response_model. Imports come from `aos_core.*` and `..schemas` as needed.
- `slugify` moves to `routes/projects.py` (its only caller).
- Routes needing redis (`jobs.py`, `schedules.py`, `council.py`): `import redis` + `from aos_core.config import get_settings`; `settings = get_settings()`; call `redis.Redis.from_url(settings.redis_url)` exactly as before. The global class-attr monkeypatch keeps working.
- `main.py`: keep `import redis` (even though `/health` is its only direct in-file redis use — this preserves `main.redis` for the FakeRedis tests), keep `settings`, `app`, CORS, `on_startup`, `/health`; then `from .routes import projects, repositories, ...` and `app.include_router(projects.router)` for each. No `prefix`/`tags` that would alter paths (paths already absolute in each decorator).
- **Route order**: FastAPI matches by registration order; keep the include order matching the current top-to-bottom definition order so any overlapping-path resolution is identical (there are no true overlaps here, but preserve order to be safe).
- `test_route_inventory.py`: assert `{(method, path) for route in app.routes ...}` equals a frozen expected set (the 40 above) — proves the refactor neither dropped nor added a route.

## Acceptance Criteria

- **All existing api tests pass unchanged** — evidence: `PYTHONPATH=apps/api pytest apps/api/tests` → **92 passed** (same count, no test file edited except the new inventory test), incl. the FakeRedis jobs/schedules/council tests (proves `main.redis` patch target preserved).
- **Route table identical** — evidence: `test_route_inventory.py` asserts the exact (method, path) set; green.
- **App boots** — evidence: `TestClient(app)` in conftest starts (on_startup runs); `GET /health` returns the same shape.
- **main.py materially smaller** — evidence: `main.py` reduced to app scaffolding + health + includes (target < ~60 lines); each domain in its own `routes/*.py`.
- **No behavior/schema/CI change** — evidence: `git diff` touches only `apps/api/app/**` + docs; ruff/compileall clean; no `schemas.py`/`aos_core`/worker/web/ci diffs.

## Verification Plan

Level 2: 3.12 venv — ruff + compileall on `apps/api/app`; `pytest apps/api/tests` → 92 (unchanged) + the inventory test. Level 4 (Orchestrator): independently diff the route table before/after (assert equal), boot `TestClient`, hit `/health`, and confirm the FakeRedis monkeypatch still intercepts a `POST /jobs`. Level 3: CI (api-tests + compose-smoke boots the api image). Merge under the Manual Merge Gate.

## Learning / Feedback Loop

Record a lesson (RFC-0004) only if the split surfaces a defect / guardian BLOCK / CI failure. Candidate if it holds: "a route-inventory equivalence test is the cheapest guard for a behavior-preserving API refactor." Record only if concretely useful.

## Suggested Delegation

Runtime Agent (Opus): the mechanical split + inventory test. Orchestrator (Opus 4.8): this spec; independent route-table equivalence + FakeRedis-still-works check; guardian; PR; Manual Merge Gate. Also (Orchestrator, this package): document the env-pinned branch constraint in HANDOFF + playbook.

## Board Linkage

- Plane: new hardening issue (to be created), set In Progress on start.
- Branch: `claude/aos-runtime-002-scanner-1egyjw` (env-pinned — see the branch-constraint note added to HANDOFF/playbook this package).
