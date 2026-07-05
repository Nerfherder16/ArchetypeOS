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

AOS-COUNCIL-001 — Agent Council seed: LLM provider abstraction + Council MVP + Final Judge, RFC-0005 Phase 1 (Plane AOS-19; the intelligence thrust's first package). Sprint 5 (PRs #43–#48) is fully merged; AOS-18 Done.

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `350c8b0` after the PR #48 merge)

### PR

#49 — **Merged** as `a56d317` (squash). CI run 28757387442 all 6 jobs green on head `8dd2fb7`.

### Status

Merged — `Provider` abstraction (`DeterministicProvider` CI default + `ClaudeCodeProvider` subscription backend), four Phase-9 agents + a rule-based Final Judge (agreements/disagreements/unsupported-claims/verdict + abstention), `CouncilReview`/`CouncilAgentOutput` + migration `0003`, worker `council_review` dispatch, council trigger/read API. **The Intelligence Layer + Agent Council + Final Judge is live (backend); AOS-19 Done.** Advisory/draft-only. Branch restarted from `main` at `a56d317`. Operator decisions honored: Claude Code SDK via subscription (no metered API/budget), four agents, dedicated tables. **Next: AOS-COUNCIL-002 — the Agent Council Dashboard.**

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
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

Verified (PR #49 merged as `a56d317`)

### Verification Level

Level 4

### Verification Method

CI run 28757387442 all 6 jobs green on head `8dd2fb7` (compose-smoke applied migration `0003` on fresh Postgres + booted all services; api-tests ran the 15 new council tests; worker-tests the dispatch test) plus Orchestrator's independent 3.12-venv run (api 92 / worker 7; `run_council` branch checks — 4 outputs, disagreement, abstention, 404, determinism, `get_provider` mapping; alembic no-drift after `0003` → 24 tables, 0 ops). AOS-19 → Done; branch restarted from `main` at `a56d317`.

### Evidence

- 4/4 e2e specs headless incl. create-schedule → run-now → job-in-history; 77 api tests; `GET /projects/{id}/jobs`; strict tsc/vite exit 0.

### Limitations

Schedule editing is enable-disable + interval only; e2e enqueue uses an ephemeral redis (local serve-api.sh / CI ensure-step). Docker on Postgres proven by CI compose-smoke.

### Required Next Verifier

GitHub CI / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge AOS-COUNCIL-001 after CI passes under the Manual Merge Gate (Plane AOS-19 Phase 1). Then AOS-COUNCIL-002 — the Agent Council Dashboard (trigger a review; per-agent status/output/confidence; surface disagreement; Final Judge panel; Playwright e2e) — closes the Phase-9 "disagreements are visible" acceptance end to end. A real council run on an authed node (flip `llm_provider=claude_code`) is the operator-side validation. Lighter backlog: AOS-21 (second repo), AOS-20 (doc-staleness/LES-007), AOS-22 (backups), AOS-23 (knowledge read path).

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