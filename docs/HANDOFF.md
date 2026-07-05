# Handoff

## Purpose

This file records the latest durable handoff for ArchetypeOS work.

Every engineering session should end by updating this file or creating a dated handoff artifact.

## Latest Handoff

### Date

2026-07-05

### Agent

Runtime Agent (Opus) under Orchestrator (Opus 4.8)

### Task

AOS-ALEMBIC-001 — Adopt Alembic migrations, baseline (Plane AOS-17; Sprint 5 package 2), folding in the AOS-WEB-001 (PR #43) reconciliation

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `821171e`)

### PR

To be opened.

### Status

In Review — Alembic baseline reproduces the 20-table schema with zero drift (Orchestrator-verified sqlite round-trip); container entrypoint runs migrations before serving. AOS-WEB-001 merged as `821171e` (PR #43; Plane AOS-16 Done).

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- `apps/api/alembic/`: `env.py` (reads URL from `app.config` settings; imports `app.models`; `target_metadata = Base.metadata`), `alembic.ini`, `script.py.mako`, and `versions/0001_baseline.py` — a model-driven baseline with 20 `op.create_table` calls (`down_revision = None`). The baseline includes `import app.models` (autogenerate omits it for the GUID/JSONField TypeDecorators — without it the migration NameErrors; documented as a review-checklist item).
- `apps/api/docker-entrypoint.sh` (executable): `set -e; alembic upgrade head; exec uvicorn ...` — a failed migration exits non-zero so the container never serves (compose-smoke catches it; never masked). `apps/api/Dockerfile` copies the alembic files + entrypoint and switches to `ENTRYPOINT`.
- `apps/api/requirements.txt`: `alembic==1.14.0`.
- `docs/DATABASE_MIGRATIONS.md`: autogenerate + review workflow, the DDL-review rule, and the one-time `alembic stamp head` for pre-existing populated databases (teevee-1).
- No schema/model change; `init_db()` create_all, `main.py`, models, and conftest untouched.
- PR #43 reconciled (AOS-WEB-001 → Merged; Plane AOS-16 Done); Board ID Registry AOS-17 spec path filled.

### Files changed

- `apps/api/requirements.txt`, `apps/api/Dockerfile`, `apps/api/docker-entrypoint.sh` (new)
- `apps/api/alembic.ini` (new), `apps/api/alembic/env.py` (new), `apps/api/alembic/script.py.mako` (new), `apps/api/alembic/versions/0001_baseline.py` (new)
- `docs/DATABASE_MIGRATIONS.md` (new), `docs/CAPABILITY_MAP.md`, `docs/PLANE_PROJECT_BLUEPRINT.md`
- `.archetype/work/AOS-ALEMBIC-001.md` (new spec)
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- Orchestrator sqlite round-trip: `alembic upgrade head` → 21 tables (20 model + alembic_version); `alembic revision --autogenerate` probe → **0 schema ops** (no drift); `alembic downgrade base` → clean. Probe deleted.
- `PYTHONPATH=apps/api pytest apps/api/tests -q` → 67 passed; `apps/worker/tests` → 1 passed; ruff + compileall exit 0.

### Known Risks

- The baseline was verified on sqlite locally (no local Postgres); model-driven DDL is portable, and CI compose-smoke exercises the entrypoint + baseline against real Postgres. If compose-smoke fails, diagnose the entrypoint/migration on Postgres first.
- Pre-existing populated databases must be `alembic stamp head`ed once (not upgraded), or the baseline would try to re-create existing tables — documented in `docs/DATABASE_MIGRATIONS.md`.

### Blockers

- None.

### Verification Status

Verification pending

### Verification Level

Level 4

### Verification Method

Orchestrator independently ran the full Alembic round-trip on a fresh sqlite DB (upgrade → 21 tables; autogenerate probe → 0 schema ops proving zero drift vs models; downgrade → clean) plus full pytest (67 API + 1 worker) and ruff/compileall. GitHub CI compose-smoke (real Postgres via the new entrypoint + baseline) pending on the PR as the authoritative proof; merge under the Manual Merge Gate.

### Evidence

- No-drift probe = 0 `op.create/drop/alter` operations; baseline = 20 `op.create_table` + `import app.models`; entrypoint executable and hard-fails on migration error; 67 + 1 tests green.

### Limitations

Baseline verified on sqlite locally; Postgres path proven by CI compose-smoke. `init_db()` create_all retained as an idempotent sqlite-dev safety net (a later package can retire it once a real schema migration exercises alembic).

### Required Next Verifier

GitHub CI (compose-smoke) / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge the AOS-ALEMBIC-001 PR after CI passes. Sprint 5 continues: AOS-18 (worker pipeline); AOS-21 (second repo) can run in parallel. No new package starts without operator direction.

## Handoff Template

```text
Date:
Agent:
Task:
Branch:
PR:
Status:
Completed:
Files changed:
Tests run:
Docs updated:
Worktree or connector fallback used:
Base ref:
Head SHA:
Backup head, if any:
Freshness check:
Verification Status:
Verification Level:
Verification Method:
Evidence:
Limitations:
Required Next Verifier:
Risks:
Blockers:
Next recommended step:
Required reader context:
```

## Rule

A task is not complete until the handoff is durable and verification metadata is recorded.