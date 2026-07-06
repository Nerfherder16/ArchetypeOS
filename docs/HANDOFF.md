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

AOS-PORTFOLIO-001 (Plane AOS-21) — Portfolio: onboard + scan a second real repo (`pydantic/pydantic-ai`, operator-chosen), evaluate every engine. The first portfolio reality test + a repeatable repo-acquisition capability. (Prior: AOS-KNOW-003 merged PR #52 / `c022c6b` — AOS-23 Done; AOS-KNOW-002 PR #51; AOS-APIROUTES-001 PR #50 / AOS-24; AOS-COUNCIL-001 PR #49 / AOS-19.)

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `c022c6b` after the PR #52 merge; env-pinned — see branch note above)

### PR

To be opened.

### Status

In Review — `aos_core/services/onboarding.py` (`clone_repo` — the missing acquire step) + `scripts/onboard_repo.sh` + `test_onboarding.py`; captured evidence `.archetype/portfolio/pydantic-ai/scan.json` + evaluation `docs/PORTFOLIO_PYDANTIC_AI.md`; **honest lessons LES-013 (file-count language mix misreads pydantic-ai as 28% Python) + LES-014 (architecture edges tree-only) — both open**; LES-015 (self-caught e2e count-race) closed. Also fixed two count-coupled tests (digest `open_lessons==1`; e2e open-filter) to be count-agnostic after adding 2 open lessons. Orchestrator-verified: real full pipeline on pydantic-ai (all 8 manifests, ecosystems, CI detected, no crash; DNA + 14 contains edges); `clone_repo` real `file://` clone + idempotent + path-safety; api **102**; full Playwright **5/5 headless**; ruff full CI scope + compile clean. **Merging closes AOS-21; next: the definitive-roadmap reevaluation.**

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

Verification pending (AOS-PORTFOLIO-001 in review)

### Verification Level

Level 4

### Verification Method

Orchestrator ran the real full pipeline on pydantic-ai (clone → register → `run_scan` → DNA + 15 arch nodes / 14 `contains` edges + 8 manifests → digest) and captured `.archetype/portfolio/pydantic-ai/scan.json`; independently verified `clone_repo` (real `file://` clone + idempotent + all path-safety rejections); api **102 passed** (99 + 3 onboarding); full Playwright **5/5 headless** (fixed `knowledge.spec.ts` open-filter to retrying/count-agnostic after 2 new open lessons; also fixed the count-coupled digest test); ruff at full CI scope (`apps/api packages/aos_core apps/worker tools`) + compile clean. GitHub CI (api-tests, compose-smoke, web-e2e) pending on the PR; merge under the Manual Merge Gate; on merge AOS-21 → Done.

### Evidence

- 4/4 e2e specs headless incl. create-schedule → run-now → job-in-history; 77 api tests; `GET /projects/{id}/jobs`; strict tsc/vite exit 0.

### Limitations

Schedule editing is enable-disable + interval only; e2e enqueue uses an ephemeral redis (local serve-api.sh / CI ensure-step). Docker on Postgres proven by CI compose-smoke.

### Required Next Verifier

GitHub CI / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge AOS-PORTFOLIO-001 under the Manual Merge Gate — **closes AOS-21**. Then the **definitive-roadmap reevaluation** the operator flagged (bring a proposed phase map). The reality test spawned two scoped follow-ups: a language-mix weighting package (LES-013) and an architecture-semantics / dependency-edge package (LES-014, Fable-flagged). Other remaining: AOS-20 (doc-staleness/LES-007 — machine-surfaced by the digest), AOS-22 (backups), AOS-COUNCIL-002 (council dashboard). A real council run on an authed node (`llm_provider=claude_code`), now feedable with pydantic-ai data, validates Intelligence Phase 1.

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