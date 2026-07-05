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

AOS-CORE-001 — Extract aos_core shared package, RFC-0006 Phase 1 (Plane AOS-18; Sprint 5 package 3), folding in the AOS-ALEMBIC-001 (PR #44) reconciliation

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `96550b8`)

### PR

To be opened.

### Status

In Review — `aos_core` extracted, api consumes it, ZERO behavior change (Orchestrator-verified on a 3.12 venv: 69 tests pass incl. 67 unchanged, alembic no-drift = 0 ops, guardian runs without aos_core installed). AOS-ALEMBIC-001 merged as `96550b8` (PR #44; Plane AOS-17 Done). RFC-0006 Accepted.

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- `packages/aos_core/`: new installable package. `config.py`, `database.py`, `models.py`, `repository_scanner.py` moved verbatim from `apps/api/app`; new `services/scan.py` (`run_scan`, extracted from `main.py`'s scan route body) and `services/digest.py` (`build_digest`, the verbatim `_build_digest` aggregation). `pyproject.toml` (setuptools, requires-python >=3.12, deps incl. fastapi for HTTPException).
- `apps/api/app` reduced to `main.py` (routes only, imports `aos_core.*`; scan route = `return run_scan(...)`, digest route keeps its 404 + persist, calling `build_digest`) + `schemas.py`.
- Docker: `apps/api/Dockerfile` build context → repo root (`COPY packages/aos_core` + `pip install`, then `COPY apps/api/...`); compose api `build: {context: ., dockerfile: apps/api/Dockerfile}` (worker/web untouched).
- CI: `api-tests` + `web-e2e` jobs install `pip install -e ./packages/aos_core`.
- alembic `env.py` + baseline retargeted `app.` → `aos_core.`; no-drift still 0 ops.
- Guardian: new `missing-core-tests` BLOCK for `packages/aos_core/` changes without a test change; `load_scan_report` in-repo fallback imports `aos_core.repository_scanner` via `sys.path` (works in the pr-guardian CI job, which does not install aos_core). LES-010 recorded.
- Follow-on retargets required by the move: `apps/api/tests/{conftest,test_scanner}.py` import `aos_core.*` (no assertions changed).
- PR #44 reconciled (AOS-ALEMBIC-001 → Merged; Plane AOS-17 Done); RFC-0006 Accepted; AOS-18 reshaped into 3 phases.

### Files changed

- `packages/aos_core/**` (new: pyproject + 4 moved modules + services/{scan,digest}.py); `apps/api/app/{config,database,models,repository_scanner}.py` DELETED
- `apps/api/app/main.py`, `apps/api/app/schemas.py`, `apps/api/tests/{conftest,test_scanner,test_guardian_evolution}.py`
- `apps/api/Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `tools/pr_guardian.py`
- `apps/api/alembic/env.py`, `apps/api/alembic/versions/0001_baseline.py`
- `docs/rfc/RFC-0006-Shared-Core-Domain-Library.md` (Accepted), `knowledge/wiki/lessons/LES-010.md` + `index.md`, `docs/CAPABILITY_MAP.md`
- `.archetype/work/AOS-CORE-001.md` (new spec); `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- On a Python 3.12 venv (the pinned interpreter; system is 3.11): `pip install -e ./packages/aos_core` → ok; `PYTHONPATH=apps/api pytest apps/api/tests -q` → **69 passed** (67 original unchanged + 2 new guardian tests); ruff/compileall clean.
- alembic on 3.12: `upgrade head` → 21 tables; no-drift autogenerate probe → **0 schema ops** with `aos_core.models`.
- Guardian run standalone with system python (aos_core NOT installed) → consulted 3 risk signals, no ImportError (the pr-guardian CI condition).

### Known Risks

- The Docker/compose build-context restructure is proven only by CI compose-smoke (no local docker). If compose-smoke fails, check the api image build (aos_core install order, COPY paths) first.
- The guardian's scanner fallback relies on `packages/aos_core` being present at the repo path in the pr-guardian CI checkout (it is — full checkout); if that job ever switches to a sparse checkout, revisit.

### Blockers

- None.

### Verification Status

Verification pending

### Verification Level

Level 4

### Verification Method

Orchestrator independently verified on a Python 3.12 venv: editable install, 69-test suite (67 unchanged), alembic no-drift = 0 ops with `aos_core.models`, guardian running without aos_core installed. GitHub CI (api-tests + web-e2e install aos_core; compose-smoke builds the api image from the new context) pending on the PR as the Docker proof; merge under the Manual Merge Gate.

### Evidence

- 69 tests pass on 3.12 (67 original unchanged); no-drift = 0 ops; guardian works without aos_core installed; `apps/api/app` reduced to `main.py` + `schemas.py`.

### Limitations

Docker restructure proven only by CI compose-smoke. Worker unchanged — it runs jobs in Phase 2 (AOS-WORKERRUN-001).

### Required Next Verifier

GitHub CI (compose-smoke) / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge the AOS-CORE-001 PR after CI passes. RFC-0006 Phase 2 (AOS-WORKERRUN-001 — worker runs scan/digest jobs via aos_core) next; Phase 3 (AOS-SCHED-001) after. AOS-21 (second repo) can run in parallel.

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