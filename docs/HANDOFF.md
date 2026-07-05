# Handoff

## Purpose

This file records the latest durable handoff for ArchetypeOS work.

Every engineering session should end by updating this file or creating a dated handoff artifact.

## Latest Handoff

### Date

2026-07-05

### Agent

Runtime Agent (Opus) under Orchestrator (Opus 4.8) — first package after the Fable 5 → Opus 4.8 orchestrator switch

### Task

AOS-WEB-001 — Web Test Framework: Playwright suite, enforced (Plane AOS-16; Sprint 5 package 1), folding in the AOS-ORCH-004 (PR #42) reconciliation + Board ID Registry backfill

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `74e9370`)

### PR

To be opened.

### Status

In Review — Playwright suite runs headless (Orchestrator-verified 3/3), guardian evolved to enforce web tests, accepted-warnings retired. Sprint 4 fully closed: AOS-ORCH-004 merged as `74e9370` (PR #42); orchestration is now Opus 4.8.

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- `apps/web/e2e/`: 3 `@playwright/test` specs (control-tower, decisions, digest) promoted from the `scripts/web_drive/` seed corpus; `playwright.config.ts` with a two-server `webServer` (self-booting API + web) and a `PW_LOCAL_CHROMIUM` browser seam; `serve-api.sh` (executable) booting a scratch API; `fixtures/demo-repo/` (example.py + Dockerfile so the scanner surfaces Python + the DOCKER_WITHOUT_ENV_TEMPLATE risk flag without committing a real .env).
- `.github/workflows/ci.yml`: new `web-e2e` job — installs its own Playwright browser and runs the suite headless on ubuntu (sixth CI job).
- Guardian evolution: `web-tests-not-enforced` now fires only on `apps/web/src/` changed without an `apps/web/e2e/` change (mirrors api/worker; stays WARN); `.archetype/guardian/accepted_warnings.json` retired to `[]`; 2 new guardian tests.
- LES-009 recorded + indexed (the dated warning-acceptance was a forcing function — it drove this package before the 2026-08-01 expiry).
- Board ID Registry backfilled: Sprint 5 cycle + AOS-16..23 UUIDs (fetched from Plane, LES-008); cleaned two stale ACTIVE_WORK entries (AOS-ORCH-004 In Review→Merged, duplicate AOS-PRG-003 placeholder) — live LES-007 instances.
- PR #42 reconciled (AOS-ORCH-004 → Merged; Sprint 4 COMPLETE; orchestration → Opus 4.8).

### Files changed

- `apps/web/package.json`, `apps/web/playwright.config.ts` (new), `apps/web/e2e/**` (new: 3 specs + serve-api.sh + fixtures), `apps/web/.gitignore` (new), `apps/web/package-lock.json` (new)
- `.github/workflows/ci.yml`, `tools/pr_guardian.py`, `.archetype/guardian/accepted_warnings.json`, `apps/api/tests/test_guardian_evolution.py`
- `knowledge/wiki/lessons/LES-009.md` (new) + `index.md`, `docs/PR_GUARDIAN.md`, `scripts/web_drive/README.md`
- `docs/PLANE_PROJECT_BLUEPRINT.md` (registry), `.archetype/work/AOS-WEB-001.md` (new spec)
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- `PW_LOCAL_CHROMIUM=/opt/pw-browsers/chromium npm run test:e2e` (Orchestrator's own run) → 3/3 specs pass headless
- `PYTHONPATH=apps/api pytest apps/api/tests -q` → 67 passed; `apps/worker/tests` → 1 passed; ruff + compileall exit 0

### Known Risks

- E2E specs assert on current `main.tsx` placeholders/text; they'll need updating alongside UI changes (the guardian now enforces that a web-src change ships with an e2e change).
- The `web-e2e` CI job installs a browser + boots API/web per run, adding wall time; acceptable for the enforcement it buys.

### Blockers

- None.

### Verification Status

Verification pending

### Verification Level

Level 4

### Verification Method

Orchestrator independently ran the Playwright suite headless in-container (self-booting stack via the `PW_LOCAL_CHROMIUM` seam) — 3/3 pass — plus full pytest (67 API + 1 worker) and ruff/compileall. GitHub CI (incl. the new `web-e2e` job on ubuntu with its own installed browser) pending on the PR; merge under the Manual Merge Gate.

### Evidence

- 3/3 e2e specs pass; 67 API + 1 worker green; `accepted_warnings.json` = `[]`; 2 new guardian tests; no committed `/opt/pw-browsers` path (env seam only); AOS-16..23 UUIDs fetched via `get_issue_using_readable_identifier`.

### Limitations

E2E only — no Vitest component/unit tests yet (candidate for a later package).

### Required Next Verifier

GitHub CI / PR Guardian (incl. `web-e2e`), then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge the AOS-WEB-001 PR after CI passes. Sprint 5 continues: AOS-17 (Alembic) → AOS-18 (worker pipeline); AOS-21 (second repo) can run in parallel. No new package starts without operator direction.

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