---
name: aos-build-run-and-operate
description: Use when setting up an ArchetypeOS environment from scratch, building or starting services (docker compose up, npm run build, uvicorn), checking http://localhost:8000/health or the Control Tower on :5173, onboarding an external repository with onboard_repo.sh, installing git hooks, running post_merge_validation.sh or pre_pr_guardian.sh, or when pytest fails with ModuleNotFoundError for app or aos_core, compose smoke fails, or ports 8000/5173/5432/6379 are in question.
---

# ArchetypeOS: Build, Run, and Operate

## 1. Overview

ArchetypeOS is an Engineering Intelligence Platform (v0.1 complete 2026-07-05). The runtime is six Docker Compose services: a FastAPI API, a Redis 7 job queue, a Redis-driven job worker, a schedule ticker, a React 19/Vite web UI called the Control Tower, and Postgres 16 with the pgvector extension. All Python services share one core package, `packages/aos_core` (config, models, DB, scanner, services). This skill is the runbook for recreating that environment from nothing, building it, running it, and operating it: endpoint map, artifact conventions, repo onboarding, hooks, and post-merge validation.

First runtime target is Windows 11 + WSL 2 Ubuntu (docs/CURRENT_STATE.md, "First runtime target"). Everything below assumes a Linux shell at the repo root unless a `cd` is shown.

## 2. When to use / When NOT to use

Use this skill when:

- You need a working environment from a bare clone (deps, .env, images, services).
- You need to know which service owns which port, what an endpoint does, or where an artifact lands on disk.
- You are onboarding an external repository into the portfolio, installing git hooks, or validating main after a merge.

Do NOT use this skill when:

- Something is broken and you need triage: go to `aos-debugging-playbook` (symptom-to-experiment table).
- You need the meaning, default, or guard of a config flag such as EMBEDDING_PROVIDER: go to `aos-config-and-flags`.
- You are classifying or gating a change (Guardian, RFCs, merge gate): go to `aos-change-control`.
- You need the evidence bar or test-addition recipes: go to `aos-validation-and-qa`.
- You need scanner internals or RepositoryDNA semantics: go to `aos-scanner-dna-reference`.

## 3. From scratch

### 3.1 Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Python | 3.12 | Matches every CI job (`.github/workflows/ci.yml` uses `python-version: '3.12'`) |
| Node | 22 | Matches CI `setup-node` (`node-version: '22'`) |
| Docker + compose plugin | current | `docker compose` (plugin syntax), not `docker-compose` |
| git | current | hooks, onboarding clones |

### 3.2 Install sequence

Run from the repo root. A virtualenv is recommended but not enforced by any script.

```bash
cd /path/to/ArchetypeOS

# 1. Dev toolchain (ruff 0.8.6 + pytest 8.3.4, pinned to CI)
pip install -r requirements-dev.txt

# 2. Shared core package, editable
pip install -e ./packages/aos_core

# 3. Per-service runtime deps
pip install -r apps/api/requirements.txt        # fastapi, uvicorn, sqlalchemy, alembic, psycopg, pgvector, redis, httpx...
pip install -r apps/worker/requirements.txt     # redis, pgvector, PyYAML, pytest
pip install -r apps/scheduler/requirements.txt  # redis only

# 4. OPTIONAL: real embedding tier (fastembed/ONNX, ~50 MB, no torch).
#    Only for nodes running EMBEDDING_PROVIDER=fastembed. The default
#    "deterministic" tier needs neither file.
pip install -r apps/api/requirements-embeddings.txt
pip install -r apps/worker/requirements-embeddings.txt

# 5. Web UI deps
cd apps/web && npm install && cd ../..

# 6. Environment file for compose
cp .env.example .env
```

`.env.example` covers Postgres credentials, host port overrides (POSTGRES_PORT, REDIS_PORT, API_PORT, WEB_PORT), DATABASE_URL, REDIS_URL, ARTIFACT_ROOT, REPOSITORY_ROOT, HOST_REPOSITORY_ROOT, CORS_ORIGINS, VITE_API_BASE_URL. It does NOT list EMBEDDING_PROVIDER, KNOWLEDGE_ROOT, or HOST_KNOWLEDGE_ROOT; compose supplies defaults for those (`deterministic`, `/knowledge`, `./knowledge`). Flag semantics live in `aos-config-and-flags`.

### 3.3 Verify the checkout

Every file this runbook depends on must exist. One-shot check:

```bash
ls requirements-dev.txt .env.example docker-compose.yml pyproject.toml \
  apps/api/requirements.txt apps/api/requirements-embeddings.txt \
  apps/worker/requirements.txt apps/worker/requirements-embeddings.txt \
  apps/scheduler/requirements.txt apps/web/package.json \
  apps/api/docker-entrypoint.sh packages/aos_core/pyproject.toml \
  scripts/onboard_repo.sh scripts/pre_pr_guardian.sh scripts/post_merge_validation.sh \
  tools/pr_guardian.py tools/doc_staleness.py .github/workflows/ci.yml
```

`scripts/install-hooks.sh` and `scripts/hooks/post-merge` shipped with AOS-SELFHEAL-001 (merged as PR #80); see section 9.

## 4. Build

```bash
# Web: typecheck + production bundle (same command CI runs)
cd apps/web && npm run build && cd ../..   # runs "tsc && vite build"

# Compose: validate config, then build images
docker compose config > /dev/null           # exit 0 = valid
docker compose build api worker web scheduler
```

CI's compose-smoke job builds that explicit four-service list; postgres and redis are pulled images, not builds. Keep any local smoke identical (LES-011 trap, section 11).

The API and worker images install fastembed unconditionally, but the ~90 MB MiniLM model is NOT pre-downloaded by default. For an offline node build with the arg `PREDOWNLOAD_EMBEDDING_MODEL: "true"` (documented inline in docker-compose.yml, as of 2026-07-06).

## 5. Run

### 5.1 Service table (from docker-compose.yml)

| Service | Image / build | Host port | Role | depends_on |
|---------|---------------|-----------|------|------------|
| postgres | pgvector/pgvector:pg16 | 5432 (POSTGRES_PORT) | DB with `vector` extension | none |
| redis | redis:7-alpine, appendonly | 6379 (REDIS_PORT) | Job queue `archetypeos:jobs` | none |
| api | apps/api/Dockerfile | 8000 (API_PORT) | FastAPI; entrypoint runs `alembic upgrade head` then uvicorn | postgres, redis (healthy) |
| worker | apps/worker/Dockerfile | none | BRPOPs `archetypeos:jobs`; runs repository_scan, project_digest, council_review jobs | api (healthy), redis |
| scheduler | apps/scheduler/Dockerfile | none | 30-second tick; enqueues jobs from due schedules | postgres, redis |
| web | apps/web/Dockerfile | 5173 (WEB_PORT) | Control Tower (Vite/React 19) | api (healthy) |

Shared volumes: `archetype_data` mounted at `/data` (artifacts), `./repositories` at `/repositories` read-only (scannable repos), `./knowledge` at `/knowledge` read-only on api only (vault).

```bash
docker compose up -d          # or the CI-order staged start:
docker compose up -d postgres redis api
docker compose up -d worker web scheduler
```

### 5.2 Health verification

```bash
curl -fsS http://localhost:8000/health
```

`GET /health` in apps/api/app/main.py always returns HTTP 200 with this shape:

```json
{"status": "ok", "api": true, "database": true, "redis": true}
```

- `status: "ok"`: DB `select 1` succeeded AND Redis ping succeeded.
- `status: "degraded"`: one or both of `database` / `redis` is false. The failing dependency is the false field. It is NOT an HTTP error; scripts must check the body, not just the status code.
- No response at all: the container never started uvicorn. The entrypoint (`apps/api/docker-entrypoint.sh`) runs `alembic upgrade head` under `set -e` first, so a failed migration means health never answers by design. Check `docker compose logs api`.

Web check: `curl -fsS http://localhost:5173 > /dev/null`.

### 5.3 Control Tower (:5173)

Single-page app (apps/web/src/main.tsx), title "ArchetypeOS / Engineering Control Tower". Section headings, top to bottom, as of 2026-07-06: Runtime Health, Knowledge, Projects, the Reuse view ("Reuse across your portfolio", the Knowledge Transfer Engine surface with the WebGL radar, rendered once a project is selected), Repositories, Scan Summary, Architecture, Decisions & Research (subsections Decision Loop, Decisions, Research Notes, Recommendations), Agent Council, Nightly Digest, Scheduling & Jobs (subsections Schedules, Enqueue now, Job history), v0.1 Placeholders.

Dev mode without Docker: `cd apps/web && npm run dev` (binds 0.0.0.0:5173, expects the API at VITE_API_BASE_URL, default http://localhost:8000).

### 5.4 Running the Python services without Docker

`aos_core.config.Settings` defaults to `sqlite:///./archetypeos_dev.db` and `redis://localhost:6379/0`, and the API's startup hook calls `init_db()`, so a local API needs no Postgres and no alembic. Pattern (this is exactly what the e2e harness `apps/web/e2e/serve-api.sh` does):

```bash
# API (from repo root)
PYTHONPATH=apps/api:packages/aos_core python3 -m uvicorn app.main:app --port 8000

# Worker: NOTE apps/worker also ships an `app` package (app.worker), so its
# PYTHONPATH must put apps/worker FIRST, in a separate shell:
PYTHONPATH=apps/worker:packages/aos_core python3 -m app.worker

# Scheduler:
PYTHONPATH=apps/scheduler:packages/aos_core python3 -m app.main
```

Worker and scheduler need a reachable Redis (e.g. `docker compose up -d redis` or a local redis-server).

## 6. API endpoint map

All routes are registered in apps/api/app/main.py from apps/api/app/routes/. Prefix-free (paths are absolute). Verified against the route modules as of 2026-07-06.

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Liveness plus DB/Redis dependency status (section 5.2) |
| POST | /projects | Create project |
| GET | /projects | List projects |
| GET | /projects/{project_id} | Get one project |
| POST | /projects/{project_id}/repositories | Register a repo (name + local_path segment under REPOSITORY_ROOT) |
| GET | /projects/{project_id}/repositories | List a project's repos |
| GET | /repositories/{repository_id}/dna | RepositoryDNA (see aos-scanner-dna-reference) |
| POST | /repositories/{repository_id}/distill | Distill repo into a knowledge page |
| POST | /repositories/{repository_id}/scan | Run a scan synchronously, persist scan artifact |
| GET | /repositories/{repository_id}/scans | List scan artifacts (newest first) |
| GET | /repositories/{repository_id}/scans/{artifact_id} | Return the raw scan JSON from disk |
| GET | /projects/{project_id}/architecture | Architecture graph (nodes + edges) |
| PATCH | /architecture/nodes/{node_id} | Edit a graph node |
| PATCH | /architecture/edges/{edge_id} | Edit a graph edge |
| POST | /jobs | Enqueue a job (job_type: repository_scan, project_digest, or council_review) |
| GET | /jobs/{job_id} | Job status/result |
| GET | /projects/{project_id}/jobs | Job history for a project |
| POST | /projects/{project_id}/schedules | Create a schedule |
| GET | /projects/{project_id}/schedules | List schedules |
| GET | /schedules/{schedule_id} | Get schedule |
| PATCH | /schedules/{schedule_id} | Update schedule (e.g. enable/disable) |
| DELETE | /schedules/{schedule_id} | Delete schedule (204) |
| POST | /schedules/{schedule_id}/run | Run now: enqueue the schedule's job immediately |
| POST | /artifacts | Record an artifact |
| GET | /projects/{project_id}/artifacts | List a project's artifacts |
| POST | /projects/{project_id}/decisions | Create a decision |
| GET | /projects/{project_id}/decisions | List decisions |
| GET | /decisions/{decision_id} | Get decision |
| POST | /council-reviews/{review_id}/draft-decision | Draft a decision from a council review |
| POST | /decisions/{decision_id}/approve | Approve decision |
| POST | /decisions/{decision_id}/reject | Reject decision |
| POST | /decisions/{decision_id}/adr | Export decision as an ADR knowledge page (writes wiki/decisions/) |
| POST | /projects/{project_id}/research-notes | Create research note |
| GET | /projects/{project_id}/research-notes | List research notes |
| GET | /research-notes/{note_id} | Get research note |
| POST | /projects/{project_id}/recommendations | Create recommendation |
| GET | /projects/{project_id}/recommendations | List recommendations |
| GET | /recommendations/{recommendation_id} | Get recommendation |
| POST | /projects/{project_id}/digests | Build a nightly digest synchronously |
| GET | /projects/{project_id}/digests | List digests |
| GET | /digests/{digest_id} | Get digest |
| POST | /projects/{project_id}/council-reviews | Enqueue a council_review job (async; worker produces the review) |
| GET | /projects/{project_id}/council-reviews | List council reviews |
| GET | /council-reviews/{review_id} | Get council review |
| POST | /knowledge/sync | Sync the vault (lessons index, decision ADRs, repo distillations) into the DB |
| GET | /knowledge/pages | List knowledge pages |
| GET | /knowledge/pages/{page_id} | Get knowledge page |
| POST | /projects/{project_id}/transfer | Knowledge Transfer Engine: ranked reuse recommendations for a `need`, excluding the target project's own repos; compute-and-return, no persistence |

## 7. Artifact and data conventions

| Thing | Location | Notes |
|-------|----------|-------|
| Scan artifacts | `<ARTIFACT_ROOT>/<project_id>/<repository_id>/repository-scan-<artifact_id>.json` | Written by `aos_core/services/scan.py`; sha256 checksum stored on the Artifact row. ARTIFACT_ROOT: `./data/artifacts` locally, `/data/artifacts` (volume `archetype_data`) in compose |
| Scannable repos | `<REPOSITORY_ROOT>/<name>` | `./repositories` locally (gitignored), `/repositories` read-only in containers. `local_path` at registration is the single segment `<name>`, resolved server-side via `safe_repo_path` |
| Knowledge vault | `knowledge/` at repo root, `/knowledge` read-only in the api container | Sync sources: `knowledge/wiki/lessons/index.md`, `knowledge/wiki/decisions/*.md`, `knowledge/wiki/repositories/*.md`. DB is disposable; `POST /knowledge/sync` rebuilds |
| Lessons | `knowledge/wiki/lessons/LES-*.md` + `index.md` | Authoring rules in aos-docs-and-lessons (RFC-0004) |
| Reconciliation drafts | `.archetype/reconciliation/PENDING.md` | Written by `tools/doc_staleness.py --fix`; a DRAFT only, never auto-applied. The `--fix` flag merged via PR #80 (AOS-SELFHEAL-001) |
| Work packages | `.archetype/work/AOS-*.md` | See aos-change-control |
| Local dev DB | `./archetypeos_dev.db` (sqlite) | Only when running the API outside Docker with default settings |

## 8. Onboarding an external repository

`scripts/onboard_repo.sh` (AOS-21) does the acquire step and prints the two API calls that finish onboarding:

```bash
# Usage: onboard_repo.sh <git-url> <name> [ref]
bash scripts/onboard_repo.sh https://github.com/org/some-repo some-repo
```

What it does, verified against the script:

1. Shallow-clones the URL into `$REPOSITORY_ROOT/<name>` (default `./repositories`) via `python3 -m aos_core.services.onboarding`. Idempotent: an existing non-empty destination is returned as-is. `<name>` must be a single safe path segment (traversal is rejected).
2. Prints the register call: `curl -X POST http://localhost:8000/projects/$PROJECT_ID/repositories -H 'Content-Type: application/json' -d '{"name": "<name>", "local_path": "<name>"}'` (returns REPO_ID).
3. Prints the scan call: `curl -X POST http://localhost:8000/repositories/$REPO_ID/scan`.

The script needs `aos_core` importable; it adds `packages/aos_core` to PYTHONPATH itself, so a bare checkout works. Steps 2 and 3 need the API running. If the API runs in Docker, HOST_REPOSITORY_ROOT must point at the directory you cloned into so `/repositories/<name>` exists inside the container.

## 9. Git hooks (AOS-SELFHEAL-001, merged as PR #80)

Both files below shipped on branch `laptop/aos-selfheal-doc-loop` (HEAD commit AOS-SELFHEAL-001) and are on main via PR #80. They are opt-in per clone: run the install script once.

```bash
bash scripts/install-hooks.sh
# -> git config core.hooksPath scripts/hooks  (versioned hooks, not .git/hooks)
```

Installed hooks (contents of `scripts/hooks/` on the branch):

- `post-merge`: after any local merge/pull, runs `tools/doc_staleness.py --fix` to refresh the reconciliation draft at `.archetype/reconciliation/PENDING.md`. Non-blocking by contract (always exits 0); it writes a draft and prints where it is, it never edits the state docs. There is no pre-push hook as of 2026-07-06.

## 10. Post-merge validation and the local gate

After a merge to main, validate it:

```bash
git fetch origin main
bash scripts/post_merge_validation.sh            # defaults to origin/main
```

What it runs (verified): `python -m compileall` on api+worker app and tests, `PYTHONPATH=apps/api pytest apps/api/tests`, `PYTHONPATH=apps/worker pytest apps/worker/tests`, web `npm install && npm run build`, `docker compose config`, and (if `gh` is present) shows the latest main CI run. npm/docker/gh steps degrade to warnings when the tool is absent.

Before opening a PR, run the local gate (mirrors CI plus the deterministic PR Guardian):

```bash
git fetch origin main
bash scripts/pre_pr_guardian.sh                  # base=origin/main head=HEAD
```

Never bypass PR Guardian, the head-SHA-pinned manual merge gate, or the RFC process; a BLOCK is fixed in code, not overridden (no substantive test, secret, metadata, or acceptance BLOCK has ever been overridden; see aos-change-control section 8 for the verified override record).

## 11. Known traps

| Trap | Rule |
|------|------|
| pytest import errors (`ModuleNotFoundError: app`) | Tests are run with an explicit path: `PYTHONPATH=apps/api pytest apps/api/tests` and `PYTHONPATH=apps/worker pytest apps/worker/tests`. This is exactly what CI does; nothing else is supported |
| `app` package collision | apps/api and apps/worker BOTH ship a top-level `app` package. When running both processes from one checkout, each needs its own PYTHONPATH with its own app dir first (see section 5.4 and serve-api.sh) |
| ruff scope parity (LES-012) | Lint with CI's exact scope: `ruff check apps/api` and `ruff check apps/worker` (NOT `apps/api/app`). The narrower scope skips alembic migrations and lets lint errors reach CI |
| Compose smoke explicit lists (LES-011) | compose-smoke builds and starts explicit service lists (`build api worker web scheduler`; `up -d postgres redis api`; then `up -d worker web scheduler`). A new compose service must be added to those CI steps or it ships unverified |
| WSL2-first target | The declared first runtime target is Windows 11 + WSL 2 Ubuntu (docs/CURRENT_STATE.md). Reproduce runtime bugs there before calling them environment-specific |
| Health 200 but degraded | `/health` returns HTTP 200 even when `status` is `degraded`; parse the body (section 5.2) |
| Silent API death on bad migration | The container entrypoint aborts before uvicorn if `alembic upgrade head` fails; a never-healthy api container means read the migration logs, not the app logs |
| Council reviews are async | `POST /projects/{id}/council-reviews` only enqueues; without a running worker the review never appears |
| pgvector/embedder tests skip silently | `-m pgvector` needs AOS_TEST_DATABASE_URL pointing at Postgres; `-m embedder` needs fastembed installed. See aos-validation-and-qa |

## 12. Task tier guide

Routing home is `aos-model-routing`; these labels are operator guidance, candidate status.

| Task in this skill's scope | Tier |
|----------------------------|------|
| Health checks, curl probes, `docker compose config`, port table lookups | Haiku |
| Running the install sequence or post_merge_validation.sh and reporting output verbatim | Haiku |
| From-scratch environment build with deviation handling (missing tool, port conflict) | Sonnet |
| Onboarding a new external repo end to end (clone, register, scan, verify DNA) | Sonnet |
| Adding or changing a compose service, entrypoint, or CI smoke step | Sonnet, escalate to Opus if it touches gate scripts |
| Diagnosing a boot failure this runbook does not explain | Escalate via aos-debugging-playbook; Opus if evidence conflicts |

## 13. Common mistakes

1. Running `pytest apps/api/tests` without `PYTHONPATH=apps/api` and concluding the suite is broken.
2. Skipping `pip install -e ./packages/aos_core` and hitting `ModuleNotFoundError: aos_core` in every service.
3. Installing the `-embeddings` requirements on a deterministic-tier node "just in case": the tiers are intentionally separated; CI even asserts torch is absent. Check `aos-config-and-flags` before changing EMBEDDING_PROVIDER.
4. Treating an HTTP 200 from /health as healthy without reading `status`.
5. Confusing the two path rules: registration (`POST /projects/{id}/repositories`) 400s if `local_path` escapes REPOSITORY_ROOT or does not exist yet (server-side `safe_repo_path`: resolve, reject outside root, require an existing directory), while `onboard_repo.sh` additionally restricts `<name>` to a single path segment.
6. Forgetting `cp .env.example .env`, then debugging port or credential mismatches that are just missing env defaults.
7. Assuming the git hooks are active without installing them: they merged via PR #80 (AOS-SELFHEAL-001) but are opt-in per clone (`bash scripts/install-hooks.sh`).
8. "Fixing" a Guardian BLOCK by weakening the gate scripts instead of the code. Never. See aos-change-control.

## 14. Provenance and maintenance

Written 2026-07-06 on branch `laptop/aos-selfheal-doc-loop` (HEAD = AOS-SELFHEAL-001, since merged as PR #80; the local origin/main ref was at PR #79). Derived from: docker-compose.yml, .env.example, requirements-dev.txt, apps/{api,worker,scheduler}/requirements*.txt, apps/web/package.json, apps/api/app/main.py, apps/api/app/routes/*.py, apps/api/docker-entrypoint.sh, apps/worker/app/worker.py, apps/scheduler/app/main.py, apps/web/src/main.tsx, apps/web/src/features/reuse/ReuseView.tsx, apps/web/e2e/serve-api.sh, packages/aos_core/aos_core/config.py, packages/aos_core/aos_core/services/{scan,knowledge,onboarding,jobs}.py, scripts/{onboard_repo,install-hooks,post_merge_validation,pre_pr_guardian}.sh, scripts/hooks/post-merge, tools/doc_staleness.py, .github/workflows/ci.yml, pyproject.toml, docs/CURRENT_STATE.md, knowledge/wiki/lessons/index.md.

Re-verification commands for facts that may drift:

| Fact | Re-check |
|------|----------|
| Service/port table | `docker compose config --services && grep -n "ports:" -A1 docker-compose.yml` |
| Health response shape | `grep -n "def health" -A16 apps/api/app/main.py` |
| Endpoint map | `grep -rn -E '@router\.(get|post|put|patch|delete)' apps/api/app/routes/` |
| Python/Node versions | `grep -n "python-version\|node-version" .github/workflows/ci.yml` |
| Dep pins | `cat requirements-dev.txt apps/*/requirements*.txt` |
| Scan artifact path scheme | `grep -n "artifact_dir\|artifact_name" packages/aos_core/aos_core/services/scan.py` |
| Vault sync sources | `grep -n "wiki" packages/aos_core/aos_core/services/knowledge.py` |
| Hooks merged yet? | `git ls-tree origin/main scripts/ --name-only \| grep install-hooks` |
| doc_staleness --fix merged yet? | `git show origin/main:tools/doc_staleness.py \| grep -c '\-\-fix'` |
| Compose smoke service lists | `grep -n "docker compose build\|docker compose up" .github/workflows/ci.yml` |
| Control Tower section names | `grep -n "<h2>" apps/web/src/main.tsx` |
| Worker job types | `grep -n "job_type ==" apps/worker/app/worker.py` |
| Scheduler tick | `grep -n "TICK_SECONDS" apps/scheduler/app/main.py` |
