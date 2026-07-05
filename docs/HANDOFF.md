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

AOS-SCHED-001 — Scheduler seed: schedules-as-data + control-plane scheduler, RFC-0007 / RFC-0006 Phase 3a (Plane AOS-18; Sprint 5 package 5), folding in the AOS-WORKERRUN-001 (PR #46) reconciliation

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `3fe8afb`)

### PR

To be opened.

### Status

In Review — `Schedule` model + Alembic migration `0002` (first real migration, no-drift clean), a control-plane `apps/scheduler` service materializing due schedules into jobs via one shared `enqueue_job` path, Schedule CRUD API (Orchestrator-verified on a 3.12 venv: 75 api tests, migration no-drift = 0 ops). AOS-WORKERRUN-001 merged as `3fe8afb` (PR #46; RFC-0006 Phase 2). RFC-0007 Accepted. AOS-18 stays In Progress (Phase 3a of 3).

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- `aos_core.models.Schedule` (AuditMixin table `schedules`: project_id?, name, job_type, payload, interval_seconds, enabled, last_run_at, next_run_at); Alembic migration `0002_schedule.py` (`down_revision='0001'`, only the schedules table, `import aos_core.models` added).
- `aos_core.services.jobs`: `QUEUE` + `enqueue_job(db, client, ...)` (create Job + `client.lpush`; no redis dep in aos_core). `apps/worker` + `apps/api` import `QUEUE` from here (single source); `POST /jobs` uses `enqueue_job`.
- `aos_core.services.scheduler.run_due_schedules(db, client, now)` — the tested tick (enqueue due schedules, advance last/next_run_at).
- `apps/api`: `ScheduleCreate/Read/Update` schemas + routes (`POST/GET /projects/{id}/schedules`, `GET/PATCH/DELETE /schedules/{id}`, `POST /schedules/{id}/run`).
- `apps/scheduler` (new, thin): `app/main.py` loop calling `run_due_schedules` every 30s (try/except per tick), `requirements.txt` (redis), repo-root Dockerfile; compose `scheduler` service (single instance).
- CI: **added `scheduler` to the compose-smoke build + up lists** (review remediation — compose-smoke enumerates services explicitly; LES-011).
- Tests: `test_schedules_api.py` (CRUD, missing-project/schedule 404s, run-now) + `test_scheduler.py` (`run_due_schedules` enqueues due + skips not-due + disabled). 75 api total.
- PR #46 reconciled (AOS-WORKERRUN-001 → Merged; RFC-0006 Phase 2 done); AOS-18 stays In Progress (Phase 3a of 3).

### Files changed

- `packages/aos_core/aos_core/models.py`, `packages/aos_core/aos_core/services/{jobs,scheduler}.py` (new)
- `apps/api/app/main.py`, `apps/api/app/schemas.py`, `apps/api/alembic/versions/0002_schedule.py` (new)
- `apps/worker/app/worker.py` (QUEUE import)
- `apps/scheduler/**` (new: app + requirements + Dockerfile), `docker-compose.yml` (scheduler), `.github/workflows/ci.yml` (compose-smoke build/up)
- `apps/api/tests/test_schedules_api.py` + `test_scheduler.py` (new)
- `docs/rfc/RFC-0007-...md` (Accepted), `knowledge/wiki/lessons/LES-011.md` + index, `docs/CAPABILITY_MAP.md`
- `.archetype/work/AOS-SCHED-001.md` (new spec); `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- On a Python 3.12 venv: migration `0002` upgrade → 22 tables incl. `schedules`; no-drift autogenerate probe → **0 op operations**.
- `PYTHONPATH=apps/api pytest apps/api/tests -q` → **75 passed** (69 + 6 new); `apps/worker/tests` → 5 passed; ruff (incl. `apps/scheduler`) + compileall clean.

### Known Risks

- The migration `0002` + scheduler container are proven on Postgres only by CI compose-smoke (no local docker). compose-smoke now builds + boots the scheduler (LES-011).
- Single-instance scheduler: a duplicate scheduler replica would double-enqueue. HA (leader election) is deferred per RFC-0007; run exactly one scheduler.

### Blockers

- None.

### Verification Status

Verification pending

### Verification Level

Level 4

### Verification Method

Orchestrator independently verified on a 3.12 venv: migration `0002` upgrade (22 tables) + no-drift probe (0 ops); api suite 75 passed (schedule CRUD, run-now, `run_due_schedules` tick); worker 5 unchanged; ruff/compile clean. GitHub CI compose-smoke (migration `0002` on fresh Postgres + scheduler builds/boots) pending on the PR; merge under the Manual Merge Gate.

### Evidence

- No-drift = 0 ops after `0002`; 75 api tests incl. the scheduler tick; scheduler service + compose block; one enqueue path in `aos_core.services.jobs`.

### Limitations

Interval cadence only (cron later); single-instance scheduler; dashboard is AOS-SCHED-002. Docker/migration-on-Postgres proven only by CI compose-smoke.

### Required Next Verifier

GitHub CI (compose-smoke) / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge the AOS-SCHED-001 PR after CI passes. AOS-SCHED-002 (scheduler dashboard: schedules UI + enqueue buttons + job history) closes AOS-18. AOS-21 (second repo) can run in parallel.

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