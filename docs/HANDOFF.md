# Handoff

## Purpose

This file records the latest durable handoff for ArchetypeOS work.

Every engineering session should end by updating this file or creating a dated handoff artifact.

## Latest Handoff

### Date

2026-07-05

### Agent

Orchestrator (Fable 5) — FINAL Fable 5 package; orchestration hands off to Opus 4.8 after this PR (operator decision, same container/session, model switch)

### Task

AOS-ORCH-004 — Sprint 4 close-out + Orchestrator Handoff Pack, folding in the AOS-PRG-003 (PR #41) reconciliation

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `98914f7`)

### PR

To be opened.

### Status

In Review. Sprint 4 is COMPLETE: AOS-PRG-003 merged as `98914f7` (PR #41; Plane AOS-15 Done; the CI guardian job ran the evolved code live on its own PR).

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- `docs/ORCHESTRATOR_PLAYBOOK.md`: the full package loop as practiced (spec → delegate → independent verify → in-PR state updates → guardian → PR → babysit → gate → reconcile), babysitter recipe with continuation-message pattern, merge-gate template, Level 4 recipes, and the environment quirks registry (Plane MCP 400s, stop-hook noreply false positive, compound-bash kill abort, Playwright executablePath, guardian invocation rules).
- `scripts/web_drive/`: the Level 4 browser-drive harness committed from session scratchpad (drive.mjs / drive_dec.mjs / drive_digest.mjs + package.json + README with the exact run recipe) — the durable answer to "how do we run the web tests" until the real suite ships.
- Board ID Registry (`docs/PLANE_PROJECT_BLUEPRINT.md`): Sprint 3/4 cycle IDs + AOS-10..15 issue IDs backfilled; AOS-10's ID fetched from Plane after a from-memory near-miss (LES-008).
- LES-008 recorded (identifiers are verified, never reconstructed — self-caught during this package).
- Orchestrator Transition section in this file (boot order + non-negotiables + escalation triggers).
- PR #41 reconciled (AOS-PRG-003 → Merged; Plane AOS-15 Done; Sprint 4 COMPLETE).

### Files changed

- `docs/ORCHESTRATOR_PLAYBOOK.md` (new), `scripts/web_drive/` (new: 3 drives + package.json + README)
- `docs/PLANE_PROJECT_BLUEPRINT.md` (registry), `docs/CAPABILITY_MAP.md`
- `knowledge/wiki/lessons/LES-008.md` (new), `knowledge/wiki/lessons/index.md`
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- Docs/scripts-only (no `apps/`/`tools/` change): `PYTHONPATH=apps/api pytest apps/api/tests -q` → 65 passed unchanged; ruff + compileall exit 0.

### Known Risks

- The web-drive scripts are point-in-time: they assert on current placeholders/text in `apps/web/src/main.tsx` and will need updating alongside UI changes (documented in their README).

### Blockers

- None.

### Verification Status

Verification pending

### Verification Level

Level 2

### Verification Method

Docs/scripts-only package — suite unchanged-green locally; registry IDs verified against Plane at write time; GitHub CI pending on the PR; merge under the Manual Merge Gate.

### Evidence

- 65/65 pytest, ruff/compileall exit 0; AOS-10 ID fetched via `get_issue_using_readable_identifier`; playbook facts cross-checked against state docs.

### Limitations

The drive harness is not CI-wired (that is the web-tests package, due before the 2026-08-01 acceptance expiry).

### Required Next Verifier

GitHub CI / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge this PR, then switch orchestrator models (Opus 4.8). First Sprint 5 candidates, evidence-ranked: web tests (hard deadline 2026-08-01), LES-007 doc-staleness detection, architecture-graph semantics, digest breadth, KnowledgePage API read path. No Sprint 5 package starts without operator direction.

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