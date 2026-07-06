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

Definitive-roadmap reevaluation (advisory; operator-flagged) — now that AOS-21 is Done. (Prior: AOS-PORTFOLIO-001 merged PR #53 / `b64db41` — AOS-21 Done, 5-repo reality test; AOS-KNOW-003 PR #52 / AOS-23; AOS-KNOW-002 PR #51; AOS-APIROUTES-001 PR #50 / AOS-24; AOS-COUNCIL-001 PR #49 / AOS-19.)

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `b64db41` after the PR #53 merge; env-pinned — see branch note above)

### PR

#53 — **Merged** as `b64db41` (squash). CI run 28763747860 all 6 jobs green on head `73f73ac`.

### Status

Merged — the first portfolio reality test grew to **five** repos (pydantic-ai, claude-agent-sdk-python, gin [Go], example-voting-app [polyglot compose], kubernetes [scale, 30,560 files]) + a repeatable `clone_repo`/`onboard_repo.sh` acquisition capability. **The scanner is robust and generalizes across language / deployment style / scale** (graceful non-silent truncation at 30k files). Four honest open lessons: LES-013 (language weighting), LES-014 (dependency/compose edges), LES-016 (manifest/ecosystem coverage — .NET missed), LES-017 (secret-signal precision — acute at scale); LES-015 (e2e count-race) closed. Branch restarted from `main` at `b64db41`. **AOS-21 Done. Next: the definitive-roadmap reevaluation (depth-vs-breadth settled toward depth).**

### Note — GitHub connector expired mid-session

The GitHub MCP OAuth token expired during PR #53 (long session). git push/CI were unaffected (separate proxy auth); only PR comments/reads were blocked. Operator re-authorized; the gate was posted late. If it recurs: reconnect GitHub via `/mcp` or claude.ai connector settings — git operations keep working regardless.

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

Verified (PR #53 merged as `b64db41`; AOS-21 Done)

### Verification Level

Level 4

### Verification Method

CI run 28763747860 all 6 jobs green on head `73f73ac` plus the Orchestrator's real full pipeline on **five** repos (clone via `clone_repo` → register → `run_scan` → DNA + architecture → digest; evidence at `.archetype/portfolio/{pydantic-ai,claude-agent-sdk-python,gin,example-voting-app,kubernetes}/scan.json`); `clone_repo` verified independently (real `file://` clone + idempotent + path-safety, plus five real network clones); api **102 passed**; full Playwright **5/5 headless**; ruff full CI scope + compile clean. AOS-21 → Done; branch restarted from `main` at `b64db41`.

### Evidence

- 4/4 e2e specs headless incl. create-schedule → run-now → job-in-history; 77 api tests; `GET /projects/{id}/jobs`; strict tsc/vite exit 0.

### Limitations

Schedule editing is enable-disable + interval only; e2e enqueue uses an ephemeral redis (local serve-api.sh / CI ensure-step). Docker on Postgres proven by CI compose-smoke.

### Required Next Verifier

GitHub CI / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Deliver the **definitive-roadmap reevaluation** (advisory), then let the operator pick the next build. Depth-vs-breadth is empirically settled toward **depth**: 5 diverse repos proved the scanner robust, so further ingestion is diminishing returns. Highest-value builds: (1) run the **Agent Council over a real repo** (`llm_provider=claude_code` on an authed node — validates Intelligence Phase 1 on real external code); (2) **LES-014** dependency/compose architecture edges (`example-voting-app` is a ready test); (3) **LES-013** language weighting. Scanner backlog: LES-016 (manifest/ecosystem coverage), LES-017 (secret-signal precision). Other open: AOS-20 (doc-staleness), AOS-22 (backups), AOS-COUNCIL-002 (council dashboard).

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