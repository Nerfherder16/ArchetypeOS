# Handoff

## Purpose

This file records the latest durable handoff for ArchetypeOS work.

Every engineering session should end by updating this file or creating a dated handoff artifact.

## Latest Handoff

### Date

2026-07-05

### Agent

Runtime Agent (Opus) under Orchestrator (Fable 5)

### Task

AOS-PRG-003 — Guardian Evolution, RFC-0004 Phase 2 (Plane AOS-15; Sprint 4 finale), folding in the AOS-LEARN-002 (PR #40) reconciliation

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `e8527b9`)

### PR

To be opened.

### Status

In Review — guardian evolution implemented and Orchestrator-verified (65/65 tests; annotation and expiry exercised live). AOS-LEARN-002 merged as `e8527b9` (PR #40; Plane AOS-14 Done).

### Completed

- LES-003 consumed: `missing-verification-metadata` BLOCK message now teaches the plain `Field: value` line format (markdown wrappers don't parse).
- LES-006 consumed: `.archetype/guardian/accepted_warnings.json` registry — accepted WARN codes are annotated with their lesson + expiry (web-tests entry expires 2026-08-01); expired acceptances escalate to BLOCK `accepted-warning-expired`, forcing a re-decision. Missing/invalid registry degrades gracefully. Blocks are never touched.
- RFC-0004 enforcement: `guardian-change-without-lesson` BLOCK (guardian diff without a lessons change; `PR_GUARDIAN_OVERRIDE_LESSON` escape) and `override-without-lesson-citation` BLOCK (any override token requires a `LES-<n>` citation).
- 10 new tests in `apps/api/tests/test_guardian_evolution.py` (65 total); all 8 existing guardian tests unchanged; guardian stays stdlib-only.
- `docs/PR_GUARDIAN.md` "Guardian Evolution (RFC-0004 Phase 2)" section.
- LES-003 and LES-006 closed in the registry, each citing this package.
- PR #40 reconciled (AOS-LEARN-002 → Merged; Plane AOS-14 Done, AOS-15 In Progress).

### Files changed

- `tools/pr_guardian.py`, `.archetype/guardian/accepted_warnings.json` (new), `apps/api/tests/test_guardian_evolution.py` (new), `docs/PR_GUARDIAN.md`
- `knowledge/wiki/lessons/LES-003.md`, `LES-006.md`, `index.md` (closures)
- `.archetype/work/AOS-PRG-003.md` (new spec)
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- `PYTHONPATH=apps/api pytest apps/api/tests -q` → 65 passed (builder run + Orchestrator re-run); ruff + compileall exit 0
- Orchestrator live exercise: acceptance annotation (2026-07-05 → warn with lesson citation) and expiry (2026-08-02 → BLOCK) against the real seed registry
- Self-application: this PR touches the guardian AND the lessons registry, satisfying its own new rule; CI guardian job executes the evolved code live on this PR

### Known Risks

- The acceptance registry is stateless by design; if the web-tests entry expires unrenewed on 2026-08-01, every web PR will BLOCK until a re-decision — intentional forcing function, but worth calendaring.

### Blockers

- None.

### Verification Status

Verification pending

### Verification Level

Level 3

### Verification Method

Local ruff/compileall/pytest (65) + live function exercise of both acceptance paths + the CI guardian job running the evolved code on its own PR. Merge under the Manual Merge Gate.

### Evidence

- Exit codes 0; 65/65; live annotation/expiry outputs in the PR body; LES-003/LES-006 closures by ID.

### Limitations

Cross-run warning history not persisted (stateless registry chosen); web tests remain a separate package candidate.

### Required Next Verifier

GitHub CI / PR Guardian (live self-test), then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge the AOS-PRG-003 PR after CI passes — that completes Sprint 4 (Self-Healing & Learning Loop). Remaining open lesson: LES-007 (doc staleness) → next sprint candidate alongside web tests and architecture-graph semantics.

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