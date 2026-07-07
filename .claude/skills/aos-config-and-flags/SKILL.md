---
name: aos-config-and-flags
description: Use when changing or debugging ArchetypeOS configuration, env vars, or flags. Symptoms include wrong DATABASE_URL or REDIS_URL, port collisions on 5432/6379/8000/5173, EMBEDDING_PROVIDER not taking effect, fastembed not activating, pgvector or embedder pytest markers skipping, accepted_warnings.json or review_by expiry questions, accepted-warning-expired BLOCK, compose-smoke missing a new service (LES-011), alembic upgrade head failing at container start, or core.hooksPath hook setup.
---

# AOS Config and Flags

## 1. Overview

This is the catalog of every configuration axis in ArchetypeOS (AOS), the Engineering Intelligence Platform in this repo. For each axis: allowed values, default, status, where it is defined, what reads it, and the guard that catches mistakes. All facts verified against the repo as of 2026-07-06 on branch `laptop/aos-selfheal-doc-loop` (HEAD is AOS-SELFHEAL-001, since merged as PR #80; everything else cited is on `origin/main`).

Key architecture fact: runtime settings live in ONE place, the pydantic `Settings` class in `packages/aos_core/aos_core/config.py`. It is a `BaseSettings` with `env_file=".env"` and `extra="ignore"`, so each lowercase field maps to the same name uppercased in the environment (`database_url` reads `DATABASE_URL`). Docker Compose injects env vars per service; local runs can also use a `.env` file in the process cwd.

## 2. When to use / When NOT to use

Use this skill when:

- Adding, renaming, or defaulting any env var, build arg, pytest marker, or Guardian registry entry.
- A service reads the wrong database, Redis, or path, or a flag "does nothing".
- CI skips tests you expected to run (marker gating), or compose-smoke never exercised a new service.
- Deciding whether a warning can be accepted, and for how long.

Do NOT use this skill for:

- Bringing the stack up from scratch, endpoint map, artifact layout: see `aos-build-run-and-operate`.
- Guardian verdict semantics, override policy, merge gating: see `aos-change-control` (never bypass PR Guardian, the head-SHA-pinned manual merge gate, or the RFC process).
- Diagnosing a live failure by symptom: see `aos-debugging-playbook`.
- Embedding and distillation internals behind `EMBEDDING_PROVIDER`: see `aos-knowledge-transfer-reference`.
- Test-writing recipes for the gated suites: see `aos-validation-and-qa`.

## 3. Runtime settings (packages/aos_core/aos_core/config.py)

`Settings` fields, their env var names, and verified defaults:

| Field / env var | Default (no env) | Compose value (docker-compose.yml) | Read by | Status |
|---|---|---|---|---|
| `database_url` / `DATABASE_URL` | `sqlite:///./archetypeos_dev.db` | `postgresql+psycopg://archetypeos:archetypeos@postgres:5432/archetypeos` on api, worker, scheduler | SQLAlchemy engine, alembic `env.py` | production |
| `redis_url` / `REDIS_URL` | `redis://localhost:6379/0` | `redis://redis:6379/0` on api, worker, scheduler | job queue | production |
| `artifact_root` / `ARTIFACT_ROOT` | `./data/artifacts` | `/data/artifacts` on api, worker, scheduler (volume `archetype_data`) | scan and job artifact writes, e.g. `aos_core/services/scan.py` | production |
| `repository_root` / `REPOSITORY_ROOT` | `./repositories` | `/repositories` on api, worker, scheduler (read-only mount of `HOST_REPOSITORY_ROOT`) | scanner, onboarding | production |
| `knowledge_root` / `KNOWLEDGE_ROOT` | `./knowledge` | `/knowledge` on api ONLY (read-only mount of `HOST_KNOWLEDGE_ROOT`) | knowledge sync, distillation export, ADR export (`apps/api/app/routes/repositories.py`) | production |
| `cors_origins` / `CORS_ORIGINS` | `http://localhost:5173` | same, on api only | FastAPI CORS middleware via `cors_origin_list` (comma-split) | production |
| `llm_provider` / `LLM_PROVIDER` | `deterministic` | not set in compose (stays default) | `aos_core/llm/get_provider` | `deterministic` production; `claude_code` requires the `claude` binary, experimental for container use |
| `embedding_provider` / `EMBEDDING_PROVIDER` | `deterministic` | `${EMBEDDING_PROVIDER:-deterministic}` on api AND worker | `aos_core/embeddings/get_embedder` | both values production; `fastembed` is the opt-in real tier (AOS-EMBED-002, merged via PR #73) |
| `embedding_model` / `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | not set in compose | fastembed tier only; ignored by deterministic | production |

Guards on this table:

- Unknown `llm_provider` raises `ValueError` (expected `deterministic` or `claude_code`). Unknown `embedding_provider` raises `ValueError`. `embedding_provider=fastembed` without the `fastembed` package raises with an actionable message (`packages/aos_core/aos_core/embeddings/_fastembed.py`).
- `EMBEDDING_DIM = 384` in `config.py` is a CONSTANT, not a setting. It is the single source of truth tying the pgvector column width to the all-MiniLM-L6-v2 output. Do not add an env var for it.
- `extra="ignore"` means a typoed env var (e.g. `EMBEDING_PROVIDER`) is silently ignored. There is no unknown-var guard; verify spelling against `config.py` field names.

### EMBEDDING_PROVIDER: the both-services rule

Compose comments state it explicitly: set `EMBEDDING_PROVIDER=fastembed` on api AND worker together (docker-compose.yml lines 49 to 53 and 82 to 84; a single `EMBEDDING_PROVIDER` entry in `.env` covers both since both services interpolate the same variable). The api serves retrieval, the worker produces distillation-time vectors; splitting the tiers mixes real and lexical vectors in one store. Pair `fastembed` with the pre-download build arg (section 5) for an offline node.

## 4. Compose-level variables (.env.example)

`.env.example` (repo root) is the template for a root `.env` that `docker compose` interpolates. Full verified list:

| Variable | Default in .env.example | Purpose | Guard |
|---|---|---|---|
| `POSTGRES_DB` | `archetypeos` | DB name for the `pgvector/pgvector:pg16` container | pg healthcheck |
| `POSTGRES_USER` | `archetypeos` | DB user | pg healthcheck |
| `POSTGRES_PASSWORD` | `archetypeos` | DB password (dev-grade; change off-localhost) | none |
| `POSTGRES_PORT` | `5432` | HOST-side port mapping only | `docker compose config` |
| `REDIS_PORT` | `6379` | host-side mapping | same |
| `API_PORT` | `8000` | host-side mapping | same |
| `WEB_PORT` | `5173` | host-side mapping | same |
| `DATABASE_URL` | container-internal Postgres URL (see section 3) | injected into api, worker, scheduler | entrypoint migration (section 7) |
| `REDIS_URL` | `redis://redis:6379/0` | injected into api, worker, scheduler | none direct |
| `ARTIFACT_ROOT` | `/data/artifacts` | container path on shared volume | none direct |
| `REPOSITORY_ROOT` | `/repositories` | container mount point | mount is read-only |
| `HOST_REPOSITORY_ROOT` | `./repositories` | HOST path mounted at `/repositories` | compose fails if missing (CI runs `mkdir -p repositories`) |
| `CORS_ORIGINS` | `http://localhost:5173` | api CORS allowlist, comma-separated | browser CORS errors if wrong |
| `VITE_API_BASE_URL` | `http://localhost:8000` | baked into the web build; read in `apps/web/src/api.ts` with fallback `http://localhost:8000` | web e2e |

Port-collision rule (from the `.env.example` comment): when co-hosting with another stack that owns 5432 etc., change only the host port vars (`POSTGRES_PORT`, `REDIS_PORT`, `API_PORT`, `WEB_PORT`). Container-internal wiring (`DATABASE_URL`, `REDIS_URL`) always uses the compose service names and internal ports; do not touch it.

Compose-only variables NOT present in `.env.example` (they default inside docker-compose.yml):

| Variable | Compose default | Notes |
|---|---|---|
| `EMBEDDING_PROVIDER` | `deterministic` | section 3; api and worker |
| `KNOWLEDGE_ROOT` | `/knowledge` | api only |
| `HOST_KNOWLEDGE_ROOT` | `./knowledge` | host path mounted read-only at `/knowledge` on api |

If you want them pinned, add them to your root `.env`; consider a small PR adding them to `.env.example` for discoverability (docs-only change, still goes through Guardian).

Per-service env matrix (verified against docker-compose.yml):

| Variable | api | worker | scheduler | web |
|---|---|---|---|---|
| DATABASE_URL, REDIS_URL, ARTIFACT_ROOT, REPOSITORY_ROOT | yes | yes | yes | no |
| KNOWLEDGE_ROOT | yes | no | no | no |
| CORS_ORIGINS | yes | no | no | no |
| EMBEDDING_PROVIDER | yes | yes | no | no |
| VITE_API_BASE_URL | no | no | no | yes |

## 5. Build args (not env vars)

`PREDOWNLOAD_EMBEDDING_MODEL` is a Docker BUILD ARG, default `false`, defined identically in `apps/api/Dockerfile` and `apps/worker/Dockerfile`. It controls whether the roughly 90 MB all-MiniLM-L6-v2 ONNX model is fetched at image build time. Setting it as a runtime env var does nothing.

```bash
cd /path/to/ArchetypeOS
docker compose build --build-arg PREDOWNLOAD_EMBEDDING_MODEL=true api worker
```

Companion build arg `EMBEDDING_MODEL` (default `sentence-transformers/all-MiniLM-L6-v2`) names the model to pre-download and must match `Settings.embedding_model`.

Related invariants (verified in both Dockerfiles and `apps/api/requirements-embeddings.txt`):

- `fastembed==0.5.1` is installed in the images unconditionally via `requirements-embeddings.txt`, but stays dormant unless `EMBEDDING_PROVIDER=fastembed`.
- torch is banned from the embedding tier. The `embedder-tests` CI job asserts `torch` is NOT importable and fails if it is.
- Default `false` exists so the compose-smoke CI build stays fast. Do not flip the default.

## 6. Pytest markers (pyproject.toml)

Two registered markers gate the non-hermetic suites. The gates are self-skips inside the test files, not CI-level deselection: a plain `pytest apps/api/tests` run includes them and they skip themselves when prerequisites are absent.

| Marker | Gate | Gate location | CI job |
|---|---|---|---|
| `pgvector` | skips unless `AOS_TEST_DATABASE_URL` is set AND its SQLAlchemy backend is `postgresql` | `apps/api/tests/test_pgvector_store.py` (`pytestmark`, `_is_postgres`) | `vector-store-tests` (spins up `pgvector/pgvector:pg16`, sets `AOS_TEST_DATABASE_URL=postgresql+psycopg://archetypeos:archetypeos@localhost:5432/archetypeos_test`) |
| `embedder` | `pytest.importorskip("fastembed")` | `apps/api/tests/test_fastembed_real.py` | `embedder-tests` (installs `requirements-embeddings.txt`, caches the model, asserts no torch) |

Run them locally:

```bash
cd /path/to/ArchetypeOS
# pgvector suite (needs a running Postgres with the vector extension available):
AOS_TEST_DATABASE_URL=postgresql+psycopg://archetypeos:archetypeos@localhost:5432/archetypeos_test \
  PYTHONPATH=apps/api pytest apps/api/tests -m pgvector
# embedder suite (needs: pip install -r apps/api/requirements-embeddings.txt):
PYTHONPATH=apps/api pytest apps/api/tests -m embedder
```

`AOS_TEST_DATABASE_URL` pointing at sqlite does not error, it skips: "AOS_TEST_DATABASE_URL not set to a postgresql database". A new marker must be registered in `[tool.pytest.ini_options] markers` in the root `pyproject.toml`.

## 7. Alembic migrations

- Config: `apps/api/alembic.ini` leaves `sqlalchemy.url` intentionally BLANK. `apps/api/alembic/env.py` supplies it from `aos_core.config.get_settings().database_url`, so migrations always target the same DB the app uses (sqlite in dev/test, Postgres in the container). Never hardcode a URL in alembic.ini.
- Execution: migrations run at api container start. `apps/api/docker-entrypoint.sh` is `set -e`, runs `alembic upgrade head`, then `exec uvicorn app.main:app --host 0.0.0.0 --port 8000`. A failed migration means uvicorn never starts and the api healthcheck never passes: a broken schema is surfaced, never masked. Worker and web wait on api health (`depends_on: condition: service_healthy`), so a bad migration stalls the whole stack by design.
- Versions live in `apps/api/alembic/versions/` (`0001_baseline` through `0005_repository_embedding` as of 2026-07-06; 0005 enables the pgvector `vector` extension per RFC-0010).

Local manual run: `cd apps/api && alembic upgrade head` (reads `DATABASE_URL` from env or `.env`, else the sqlite default).

## 8. Guardian accepted-warnings registry

File: `.archetype/guardian/accepted_warnings.json`. Read by `tools/pr_guardian.py` (`load_accepted_warnings` and `apply_accepted_warnings`). This is the ONLY sanctioned way to defer a Guardian WARN. It never touches BLOCKs and is not an override mechanism.

Current content as of 2026-07-06: `[]` (empty list; the sole historical entry, `web-tests-not-enforced`, was retired by real Playwright tests, see LES-009).

Entry format (a JSON list of objects; keys verified against `apply_accepted_warnings`):

```json
[
  {
    "code": "web-tests-not-enforced",
    "review_by": "2026-08-01",
    "lesson": "LES-006",
    "rationale": "web test framework scheduled as AOS-WEB-001"
  }
]
```

Semantics, exactly as implemented:

| Condition | Effect |
|---|---|
| finding severity is not `warn`, or no entry matches its `code` | untouched |
| `review_by` missing or not a valid ISO date | entry IGNORED, warning passes through unannotated (silent, so validate your date) |
| today <= `review_by` | stays WARN, message annotated `[accepted per <lesson> until <review_by>: <rationale>]` |
| today > `review_by` | escalates to BLOCK with code `accepted-warning-expired`: renew the entry or fix the underlying gap |

The `review_by` expiry is a scheduling commitment, not paperwork: LES-006 established that a warning which never changes behavior is invisible; LES-009 documents that the dated expiry is what forced AOS-WEB-001 into Sprint 5. When adding an entry, cite a lesson, write a real rationale, and treat the date as a sprint deadline. Registry parse failures fail open (treated as empty, warnings all surface), so a malformed file weakens nothing but also defers nothing.

## 9. Compose service list discipline (LES-011)

The `compose-smoke` CI job in `.github/workflows/ci.yml` enumerates services EXPLICITLY:

```yaml
- name: Build runtime images
  run: docker compose build api worker web scheduler
- name: Start core services
  run: docker compose up -d postgres redis api
...
- name: Start worker, web, and scheduler
  run: docker compose up -d worker web scheduler
```

`docker compose config` (the prior step) only validates the YAML; it builds nothing. LES-011: the `scheduler` service shipped defined-but-unbuilt in CI until Orchestrator review caught it. Rule: any NEW compose service must be added to BOTH the `docker compose build ...` line and one of the `docker compose up -d ...` lines, or its image build and boot are silently unverified. Candidate hardening (open, not implemented as of 2026-07-06): switch to bare `docker compose build` so all services are covered automatically.

## 10. Git hooks (merged via PR #80)

AOS-SELFHEAL-001 (HEAD of `laptop/aos-selfheal-doc-loop`, merged to main as PR #80) adds versioned git hooks:

- `scripts/install-hooks.sh`: run once after cloning, `bash scripts/install-hooks.sh`. It sets `git config core.hooksPath scripts/hooks` and chmods the hooks. No hook scripts are copied into `.git/hooks`; the repo directory IS the hooks dir.
- `scripts/hooks/post-merge`: after a merge or pull, runs `tools/doc_staleness.py --fix`, which writes a reconciliation DRAFT to `.archetype/reconciliation/PENDING.md` when state docs lag git. Non-blocking by contract (always exits 0), and it never edits the state docs itself. Apply the draft via the `/reconcile-state` skill. See `aos-docs-and-lessons` for the reconciliation loop.

The hooks are opt-in: run `bash scripts/install-hooks.sh` once per clone to activate them.

## 11. How to add a config axis (checklist)

1. Definition: add a lowercase field with a safe default to `Settings` in `packages/aos_core/aos_core/config.py`, with a comment naming the RFC or work package. If only compose needs it (host port, mount path), skip Settings and use a compose interpolation with an inline default instead.
2. Default: the no-env default must produce the hermetic, dependency-minimal behavior (repo precedent: `deterministic` for both `llm_provider` and `embedding_provider`). Opt IN to heavy or networked tiers, never out.
3. Validation guard: reject unknown values with a `ValueError` that names the allowed values, mirroring `get_embedder` and `get_provider`. Silent fallback on a typo is the failure mode to avoid. Placement: the guard lives in a `get_<thing>(settings)` factory function in the `aos_core` module that owns the behavior the flag selects (repo precedent: `packages/aos_core/aos_core/embeddings/__init__.py::get_embedder`, `packages/aos_core/aos_core/llm/__init__.py::get_provider`). If the flag introduces a new behavior family, create a new module under `packages/aos_core/aos_core/` with its own factory. Consumers (api, worker) call the factory with `Settings`; never validate or branch on the raw env value in consumer code.
4. Compose wiring: add `MY_VAR: ${MY_VAR:-default}` to EVERY service that reads it (check the section 4 matrix; the EMBEDDING_PROVIDER api-plus-worker pairing is the cautionary example). Add it to `.env.example` with a comment.
5. Build arg vs env var: if the value only matters at image build time (pre-downloads, bake-ins), make it an `ARG` in the Dockerfile(s) like `PREDOWNLOAD_EMBEDDING_MODEL`, and document that setting it at runtime does nothing.
6. CI wiring: if the axis enables a test tier, add a registered pytest marker in `pyproject.toml`, a self-skipping gate in the test file, and a dedicated CI job in `.github/workflows/ci.yml`. If it adds a compose service, update the compose-smoke build AND up lists (section 9). Gates the PR must pass: a config PR runs the FULL CI job set, not just the config-adjacent jobs. As of 2026-07-06 that is `pr-guardian`, `api-tests`, `worker-tests`, `vector-store-tests`, `embedder-tests`, `web-build`, `web-e2e`, `compose-smoke`, and the `ci-green` fan-in (verify with `python3 -c "import yaml; print(list(yaml.safe_load(open('.github/workflows/ci.yml'))['jobs']))"`). Merge-gate semantics (manual head-SHA-pinned gate, override policy) live in `aos-change-control`.
7. Docs: mention the axis in the work package and let the state docs pick it up through the normal reconciliation loop (`aos-docs-and-lessons`).
8. Test: every new axis needs at least one test proving the default path and one proving the guard (the ValueError). The precedent file to copy is `apps/api/tests/test_embeddings.py`: it proves the deterministic default resolves (`test_get_embedder_resolves_deterministic_default`) and that an unknown `embedding_provider` raises. Put new-axis tests in `apps/api/tests/` alongside it (API tests count for core, per the `missing-core-tests` rule). Guardian BLOCKs core changes without test changes (`missing-core-tests`), and that is correct; write the tests, do not reach for the override token; substantive code BLOCKs such as `missing-core-tests` have never been overridden (see `aos-change-control` section 8 for the verified record).
9. Guardian implications: if the axis can weaken a gate (skip a check, accept a warning), it belongs in the accepted-warnings registry pattern with a `review_by` date, or in an RFC, not in a bare env var.
10. Local gate before pushing: run `bash scripts/pre_pr_guardian.sh` from the repo root. It runs Guardian with a stub body, compileall, both pytest suites, the web build (if npm is present), and `docker compose config` (if docker is present). Expect `PASS_WITH_WARNINGS` with a `verification-pending` WARN on the stub body; anything worse means the change set is not ready. Invocation details and exit-code semantics: `aos-diagnostics-and-tooling` section 6.

## 12. Task tier guide

Routing home is `aos-model-routing`; these labels are operator guidance and candidate status, not enforced policy.

| Task in this skill's scope | Tier |
|---|---|
| Look up a default, port, or env var name; run a re-verification command | Haiku |
| Change a host port, add a var to `.env.example` | Sonnet |
| Add a full config axis end to end (Settings, guard, compose, CI, tests) | Sonnet |
| Decide whether a warning may be accepted at all, or renew an accepted-warnings entry (renewal is a re-decision, per the guardian's `accepted-warning-expired` escalation), or design a new gate or tier default | Opus |

## 13. Common mistakes

| Mistake | Reality |
|---|---|
| Setting `PREDOWNLOAD_EMBEDDING_MODEL=true` in `.env` | It is a build arg; runtime env is ignored. Rebuild with `--build-arg` or a compose `args:` block. |
| Setting `EMBEDDING_PROVIDER=fastembed` on api only | Worker distillation vectors stay lexical; set it for both (one `.env` entry covers both interpolations). |
| Editing `DATABASE_URL` to fix a host port collision | Change `POSTGRES_PORT` (host mapping) instead; `DATABASE_URL` is container-internal wiring. |
| Hardcoding `sqlalchemy.url` in `alembic.ini` | env.py deliberately overrides from Settings; the blank value is by design. |
| Expecting `pytest -m pgvector` to fail loudly without Postgres | It skips, quietly. Check the skip count in the output. |
| Typoing an env var and expecting an error | `extra="ignore"` swallows unknown vars silently. Diff your var names against `config.py`. |
| Accepted-warnings entry with a bad `review_by` date | Silently ignored; the warning shows unannotated. Use strict ISO `YYYY-MM-DD`. |
| Adding a compose service without touching ci.yml | compose-smoke never builds or boots it (LES-011). Update both explicit lists. |
| Using the registry to mute a BLOCK | Impossible by design; `apply_accepted_warnings` only touches `warn` findings. Fix the code. |
| Assuming the git hooks are active just because the scripts exist | They are opt-in. `scripts/install-hooks.sh` is on origin/main (merged via PR #80); run it once per clone, then verify with `git config core.hooksPath` (expect `scripts/hooks`). |

## 14. Provenance and maintenance

Written 2026-07-06 against `laptop/aos-selfheal-doc-loop` (HEAD f197bda, AOS-SELFHEAL-001, since merged as PR #80). At first authoring the local `origin/main` ref was f824860 (PR #79); the ref has since been fetched to a80e737 (PR #81), which includes the merged hooks and `--fix` work, and this skill's claims were re-verified against it on 2026-07-06. Derived from: `.env.example`, `docker-compose.yml`, `packages/aos_core/aos_core/config.py`, `packages/aos_core/aos_core/embeddings/__init__.py` and `_fastembed.py`, `packages/aos_core/aos_core/llm/__init__.py`, `apps/api/Dockerfile`, `apps/worker/Dockerfile`, `apps/api/requirements-embeddings.txt`, `apps/api/docker-entrypoint.sh`, `apps/api/alembic.ini`, `apps/api/alembic/env.py`, `pyproject.toml`, `apps/api/tests/test_pgvector_store.py`, `apps/api/tests/test_fastembed_real.py`, `.github/workflows/ci.yml`, `tools/pr_guardian.py`, `tools/doc_staleness.py`, `.archetype/guardian/accepted_warnings.json`, `scripts/install-hooks.sh`, `scripts/hooks/post-merge`, `scripts/pre_pr_guardian.sh`, `knowledge/wiki/lessons/LES-006.md`, `LES-009.md`, `LES-011.md`.

Flags drift. Re-verify each axis before relying on it (run from repo root):

| Fact | Re-verification command |
|---|---|
| Full env var template | `cat .env.example` |
| Settings fields and defaults | `sed -n '1,40p' packages/aos_core/aos_core/config.py` |
| EMBEDDING_PROVIDER on api AND worker | `grep -n EMBEDDING_PROVIDER docker-compose.yml` |
| Per-service env matrix and mounts | `grep -nA20 'environment:' docker-compose.yml` |
| PREDOWNLOAD build arg in both images | `grep -n ARG apps/api/Dockerfile apps/worker/Dockerfile` |
| fastembed pin, no torch | `cat apps/api/requirements-embeddings.txt` |
| Registered pytest markers | `grep -nA4 markers pyproject.toml` |
| pgvector gate condition | `grep -n AOS_TEST_DATABASE_URL apps/api/tests/test_pgvector_store.py` |
| embedder gate condition | `grep -n importorskip apps/api/tests/test_fastembed_real.py` |
| Registry contents and expiry entries | `cat .archetype/guardian/accepted_warnings.json` |
| Registry semantics (annotate vs expire-to-BLOCK) | `grep -n 'accepted-warning-expired' tools/pr_guardian.py` |
| compose-smoke explicit service lists | `grep -n 'docker compose' .github/workflows/ci.yml` |
| Migrations run at entrypoint | `cat apps/api/docker-entrypoint.sh` |
| Alembic URL comes from Settings | `grep -n 'set_main_option' apps/api/alembic/env.py` |
| Migration heads present | `ls apps/api/alembic/versions` |
| Hook installer merged to main yet | `git ls-tree origin/main scripts/ \| grep install-hooks` |
| AOS-EMBED-002 merged status | `git log origin/main --oneline --grep AOS-EMBED-002` |
