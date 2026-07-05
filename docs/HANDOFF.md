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

AOS-DEC-001 — Decision and Research Artifacts (Plane AOS-10; Sprint 3 package 2), folding in the AOS-PRG-002 (PR #33) reconciliation

### Branch

`claude/aos-runtime-002-scanner-1egyjw`

### PR

To be opened.

### Status

In Review — implementation complete, Level 4 browser verification passed (7/7), PR pending. AOS-PRG-002 merged as `5f0cfdc` (PR #33, Verified via CI incl. live guardian self-test).

### Completed

- Nine routes: create/list/read for decisions, research notes, recommendations over the existing models; 404 conventions matched.
- Scope-lock rules enforced: recommendations require non-empty evidence (422); decision research links validated (existence + same project) and stored as typed research_note evidence entries — no schema changes.
- Dashboard "Decisions & Research" section: three lists + two create forms with research-note link select; per-section error isolation.
- 6 new API tests (46 total); browser drive 7/7 including API confirmation of the typed evidence link.
- PR #33 reconciled (AOS-PRG-002 → Merged; Plane AOS-6 Done).

### Files changed

- `apps/api/app/main.py`, `apps/api/app/schemas.py`
- `apps/api/tests/test_decisions_api.py`
- `apps/web/src/api.ts`, `apps/web/src/main.tsx`
- `.archetype/work/AOS-DEC-001.md`, `.archetype/work/AOS-PRG-002.md`
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- `PYTHONPATH=apps/api pytest apps/api/tests -q` -> 46 passed
- `python3 -m ruff check apps/api tools` -> exit 0; compileall -> exit 0; `npm run build` -> exit 0
- Headless-Chromium drive: 7/7 (create research note + linked decision via forms, lists, reload persistence, typed evidence entry verified via API)

### Known Risks

- Manifest basename list in the guardian is intentionally self-contained and could drift from the scanner's MANIFEST_KINDS if ecosystems are added; documented in code.

### Blockers

- None.

### Verification Status

Verification pending

### Verification Level

Level 2

### Verification Method

Local ruff/compileall/pytest + strict tsc/vite build + Orchestrator-driven headless-Chromium run of the new section against live uvicorn+SQLite. GitHub CI pending on the PR.

### Evidence

- 46/46 tests green; builds exit 0; 7/7 browser checks; screenshot captured.

### Limitations

Browser drive is a manual Level 4 pass, not CI-repeatable. Level 3 pending.

### Required Next Verifier

GitHub CI / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge the AOS-DEC-001 PR after CI passes. Loop continues: AOS-LEARN-001 (Plane AOS-11), then AOS-ALPHA-001 (AOS-12) close Sprint 3 and v0.1.

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