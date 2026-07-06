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

AOS-KNOW-002 — Knowledge read path (RFC-0002/RFC-0004; Plane AOS-23 backend). Operator-directed substrate sequence ("aos-23, then aos-21, then reevaluate the roadmap"). vault→DB sync + KnowledgePage read API + digest open-lessons rule. (Prior: AOS-APIROUTES-001 merged PR #50 / `2c5cdcb`, AOS-24 Done — API modularized; AOS-COUNCIL-001 PR #49, AOS-19 Done.)

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `2c5cdcb` after the PR #50 merge; env-pinned — see branch note above)

### PR

#51 — **Merged** as `a462b3a` (squash). CI run 28760266463 all 6 jobs green on head `88037c3` (after a first-run ruff-F401 fix).

### Status

Merged — **repo vault stays source of truth; `KnowledgePage` is a re-syncable derived read projection** (reconciles RFC-0004's rejection of DB-primary lessons). `knowledge_root` config + `KnowledgePage.project_id` nullable (migration `0004`, sqlite batch alter) + `sync_knowledge` + read API (`POST /knowledge/sync`, `GET /knowledge/pages`(+filters), `GET /knowledge/pages/{id}`) + **digest rule 5** surfacing open lessons (RFC-0004 deferral closed). Knowledge is operational. First CI run failed on a ruff F401 in migration `0004` (local ruff had scoped to `apps/api/app`, narrower than CI's `apps/api`) — fixed, **LES-012** recorded, knowledge tests made count-agnostic. Branch restarted from `main` at `a462b3a`. **AOS-23 stays In Progress** (backend done; dashboard AOS-KNOW-003 / 23b pending an operator sequencing call: dashboard now vs jump to AOS-21).

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

Verified (PR #51 merged as `a462b3a`)

### Verification Level

Level 4

### Verification Method

CI run 28760266463 all 6 jobs green on head `88037c3` (compose-smoke applied `0004` on Postgres) plus Orchestrator's independent 3.12-venv run at CI's exact ruff scope (`apps/api packages/aos_core apps/worker tools`): api **99** / worker **7**; `sync_knowledge` on the real vault → all lessons (LES-007 the sole open), idempotent, global, missing-vault→zeros; digest surfaces the open lesson; alembic no-drift after `0004` (`knowledge_pages.project_id` nullable, **0 ops**, 24 tables). First CI run failed on a ruff F401 in migration `0004` (local ruff had scoped narrower than CI) — fixed, LES-012 recorded, knowledge tests made count-agnostic. AOS-23 stays In Progress (dashboard 23b pending); branch restarted from `main` at `a462b3a`.

### Evidence

- 4/4 e2e specs headless incl. create-schedule → run-now → job-in-history; 77 api tests; `GET /projects/{id}/jobs`; strict tsc/vite exit 0.

### Limitations

Schedule editing is enable-disable + interval only; e2e enqueue uses an ephemeral redis (local serve-api.sh / CI ensure-step). Docker on Postgres proven by CI compose-smoke.

### Required Next Verifier

GitHub CI / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Operator sequencing call: AOS-KNOW-003 (23b — dashboard Knowledge view + Playwright e2e, folding in the `./knowledge:ro` compose mount so `POST /knowledge/sync` works in compose) now, or jump to AOS-21 (second repo) and treat the dashboard as later polish. Operator-set sequence: "aos-23, then aos-21, then reevaluate the definitive roadmap" — a roadmap review follows AOS-21. Remaining: AOS-20 (doc-staleness/LES-007 — now machine-surfaced by the digest), AOS-22 (backups), AOS-COUNCIL-002 (council dashboard). A real council run on an authed node (`llm_provider=claude_code`) validates Intelligence Phase 1.

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