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

AOS-APIROUTES-001 — Split API routes by domain (control-plane hardening). Lead-Architect critique, operator-directed "route split first, then AOS-COUNCIL-002." Pure behavior-preserving refactor of `apps/api/app/main.py` into per-domain `APIRouter` modules. (Prior: AOS-COUNCIL-001 merged as PR #49 / `a56d317`, AOS-19 Done — Agent Council backend live.)

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `a56d317` after the PR #49 merge; env-pinned — see branch note above)

### PR

To be opened.

### Status

In Review — `main.py` (487 lines / 39 routes) split into 10 `apps/api/app/routes/*.py` `APIRouter` modules; `main.py` → 49 lines (app + CORS + startup + `/health` + ordered `include_router` loop, retains `import redis` so the FakeRedis `main.redis` patch target survives). Orchestrator-verified: **route table byte-identical `origin/main` vs working tree (43 pairs, empty diff)**; api **94** (92 unchanged + 2 inventory guards); FakeRedis jobs/schedules/council **11** in isolation; ruff/compile clean; diff scope `apps/api/app/**` + new test + docs. No endpoint/schema/behavior change. **Next after merge: AOS-COUNCIL-002 (Agent Council Dashboard, reframed around the Control Tower IA).**

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- **Branch name is env-pinned, not stale-by-neglect:** `claude/aos-runtime-002-scanner-1egyjw` is fixed by the session config; each package restarts it from `main` (one PR = one package, clean history). A per-package scheme (`opus/aos-<pkg>`) is adopted only if the operator reconfigures the env / grants explicit permission. See the Role-contract note in `docs/ORCHESTRATOR_PLAYBOOK.md` (Lead-Architect critique 2026-07-05, operator Decision 2a).
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- `apps/api`: `GET /projects/{project_id}/jobs` (recent jobs desc by queued_at, cap 50; 404 if project missing) — the job-history read path.
- `apps/web/src/api.ts`: types `Schedule`/`Job` + `fetchSchedules`/`createSchedule`/`setScheduleEnabled`/`deleteSchedule`/`runSchedule`/`enqueueJob`/`fetchJobs`.
- `apps/web/src/main.tsx`: "Scheduling & Jobs" section — schedules list (enable-disable, run-now, delete), create-schedule form (name / job_type select / interval), enqueue-now buttons (`Enqueue digest job`, repo select + `Enqueue scan job`), job-history list + refresh; per-section error isolation.
- `apps/web/e2e/scheduling.spec.ts` (new): create schedule → run now → job in history → disable → reload persistence.
- `apps/web/e2e/serve-api.sh`: starts an ephemeral redis on 9999 (Run-now/enqueue actually pushes to the queue) + adds `packages/aos_core` to PYTHONPATH (trap-cleaned).
- `apps/web/e2e/decisions.spec.ts`: rescoped a fragile `select` locator (my new selects collided) — behavior unchanged; enqueue buttons named `Enqueue …` to avoid colliding with digest.spec's run-digest/run-scan locators.
- CI: **added an "Ensure Redis available" step to the web-e2e job** (the e2e enqueue path needs `redis-server`; explicit rather than relying on the pre-installed binary — LES-011 family).
- Tests: `test_jobs_api.py` (list + 404, hermetic via FakeRedis). 77 api total.
- PR #47 reconciled (AOS-SCHED-001 → Merged; RFC-0007 seed done); AOS-18 stays In Progress until this merges (Phase 3b closes it).

### Files changed

- `apps/api/app/main.py` (jobs list), `apps/api/tests/test_jobs_api.py` (new)
- `apps/web/src/api.ts`, `apps/web/src/main.tsx`, `apps/web/e2e/scheduling.spec.ts` (new), `apps/web/e2e/serve-api.sh`, `apps/web/e2e/decisions.spec.ts`
- `.github/workflows/ci.yml` (web-e2e ensure-redis)
- `.archetype/work/AOS-SCHED-002.md` (new spec); `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- On a 3.12 venv: `PYTHONPATH=apps/api pytest apps/api/tests -q` → **77 passed** (75 + 2 jobs-list); `apps/worker/tests` → 6; ruff/compile clean; `apps/web` strict `tsc` + `vite build` exit 0.
- Full Playwright suite headless (`PW_LOCAL_CHROMIUM`): **4/4 pass** incl. `scheduling.spec.ts` (create schedule → run now → job in history).

### Known Risks

- The web-e2e enqueue path depends on `redis-server` on the runner — now made explicit (an "Ensure Redis" step) rather than relying on the ubuntu-latest pre-install. If web-e2e ever fails on the enqueue, check that step first.
- Single-instance scheduler still holds (AOS-SCHED-001) — run exactly one scheduler.

### Blockers

- None.

### Verification Status

Verification pending (AOS-APIROUTES-001 in review)

### Verification Level

Level 4

### Verification Method

Orchestrator independently (3.12 venv) diffed the full route table via a worktree of `origin/main` vs the working tree → **byte-identical (43 (method,path) pairs, empty diff)** — the refactor guard. api suite **94 passed** (92 prior unchanged + 2 new inventory tests); FakeRedis jobs/schedules/council tests **11 passed in isolation** (the `main.redis.Redis.from_url` patch target preserved); ruff/compile clean; `main.py` 487→49; diff scope limited to `apps/api/app/**` + the new test + docs. GitHub CI (api-tests, compose-smoke boots the api image) pending on the PR; merge under the Manual Merge Gate.

### Evidence

- 4/4 e2e specs headless incl. create-schedule → run-now → job-in-history; 77 api tests; `GET /projects/{id}/jobs`; strict tsc/vite exit 0.

### Limitations

Schedule editing is enable-disable + interval only; e2e enqueue uses an ephemeral redis (local serve-api.sh / CI ensure-step). Docker on Postgres proven by CI compose-smoke.

### Required Next Verifier

GitHub CI / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge AOS-APIROUTES-001 after CI passes under the Manual Merge Gate (Plane AOS-24). Then AOS-COUNCIL-002 — the Agent Council Dashboard, reframed around the Control Tower information hierarchy (critique #3). Then the critique's substrate priorities: AOS-23 (knowledge read path — makes stored knowledge, incl. council reviews, operational), AOS-21 (second repo — the council reasons over more than itself), AOS-20 (doc-staleness/LES-007), AOS-22 (backups). A real council run on an authed node (`llm_provider=claude_code`) is the operator-side validation of Phase 1.

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