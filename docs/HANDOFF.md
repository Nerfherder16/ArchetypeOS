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

AOS-WORKERRUN-001 — Worker runs scan/digest jobs, RFC-0006 Phase 2 (Plane AOS-18; Sprint 5 package 4), folding in the AOS-CORE-001 (PR #45) reconciliation

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `5d00a18`)

### PR

To be opened.

### Status

In Review — the worker imports `aos_core` and runs real scan/digest jobs off the queue with retries (Orchestrator-verified on a 3.12 venv: 5 worker tests incl. the e2e scan-job persistence proof; api 69 unaffected). AOS-CORE-001 merged as `5d00a18` (PR #45; RFC-0006 Phase 1). AOS-18 stays In Progress (3-phase tracker).

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- `apps/worker/app/worker.py`: imports `aos_core` (config/database/models + `run_scan`/`build_digest`); `mark_job` via ORM `Job`; `run_job` dispatches `repository_scan` → `run_scan` (result summary), `project_digest` → `build_digest` + persist, else the `test` stub (backward compat); `handle_failure(job_id, client, error)` retry helper — re-enqueue (`lpush QUEUE`) while `attempts < MAX_ATTEMPTS` (3), else `mark_job(failed)`. `QUEUE = "archetypeos:jobs"` unchanged.
- `apps/worker/app/config.py` DELETED (uses `aos_core.config`); `requirements.txt` trimmed to `redis` + `pytest`.
- Docker: worker Dockerfile repo-root context (`COPY packages/aos_core` + install, then `COPY apps/worker/...`); compose worker `build: {context: ., dockerfile: apps/worker/Dockerfile}` (api/web untouched).
- CI: `worker-tests` job installs `-e ./packages/aos_core`.
- Tests: 4 added to `apps/worker/tests/test_worker.py` (e2e scan job, digest job, backward-compat test job, retry-then-fail with a FakeRedis); queue-name test kept.
- No api/schema change; no guardian change (no lesson needed this package).
- PR #45 reconciled (AOS-CORE-001 → Merged; RFC-0006 Phase 1 done); AOS-18 stays In Progress (Phase 2 of 3).

### Files changed

- `apps/worker/app/worker.py`; `apps/worker/app/config.py` DELETED
- `apps/worker/requirements.txt`, `apps/worker/Dockerfile`, `docker-compose.yml` (worker), `.github/workflows/ci.yml` (worker-tests)
- `apps/worker/tests/test_worker.py`
- `.archetype/work/AOS-WORKERRUN-001.md` (new spec); `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- On a Python 3.12 venv: `PYTHONPATH=apps/worker pytest apps/worker/tests -q` → **5 passed** (queue-name + `test_run_scan_job` [enqueue → run_job → Artifact + RepositoryDNA rows exist] + digest job + backward-compat test job + retry-then-fail).
- `PYTHONPATH=apps/api pytest apps/api/tests -q` → 69 passed (unchanged); ruff/compileall clean.

### Known Risks

- The worker Docker restructure is proven only by CI compose-smoke (no local docker). If it fails, check the worker image build (aos_core COPY/install) first.
- Retries re-enqueue to the tail of the same queue with no backoff; acceptable for v0.2 (bounded at 3 attempts). A dead-letter/backoff policy is a future refinement.

### Blockers

- None.

### Verification Status

Verification pending

### Verification Level

Level 4

### Verification Method

Orchestrator independently ran the worker suite on a 3.12 venv (5 passed, incl. the e2e scan-job persistence proof) plus the api suite (69, unchanged) and ruff/compileall. GitHub CI (worker-tests installs aos_core; compose-smoke builds the worker image from the new context) pending on the PR; merge under the Manual Merge Gate.

### Evidence

- 5 worker tests pass incl. `test_run_scan_job` asserting Artifact + RepositoryDNA rows after `run_job`; api 69 unaffected; `config.py` deleted; worker imports aos_core.

### Limitations

Worker Docker restructure proven only by CI compose-smoke. Dashboard enqueue controls + nightly scheduler are Phase 3 (AOS-SCHED-001).

### Required Next Verifier

GitHub CI (compose-smoke) / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge the AOS-WORKERRUN-001 PR after CI passes. RFC-0006 Phase 3 (AOS-SCHED-001 — dashboard enqueue + nightly scheduler) closes the worker pipeline and AOS-18. AOS-21 (second repo) can run in parallel.

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