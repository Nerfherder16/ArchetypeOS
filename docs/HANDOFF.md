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

AOS-PRG-002 — PR Guardian Reads Repository Scanner Output (Plane AOS-6; Sprint 3 package 1)

### Branch

`claude/aos-runtime-002-scanner-1egyjw`

### PR

To be opened.

### Status

In Review — implementation complete and locally verified, PR pending. Sprint 2 closed with PR #32; Sprint 3 cycle live in Plane (`9d9c2fd6-3305-419a-a5e8-0c6d4d3c058b`) with AOS-6/10/11/12.

### Completed

- Guardian gains scanner-informed checks: `--scan-report <path>` input plus an in-repo scan fallback importing the stdlib-only scanner; graceful degradation to baseline behavior on any failure.
- Two new BLOCKs: committed secret-like filenames (`scanner-secret-path`) and committed `.env` files (`scanner-env-committed`) — path-based detection the diff-content regexes could not do.
- Two new WARNs: `scanner-missing-tests` corroboration and `scanner-new-ecosystem` expansion awareness. Override token `PR_GUARDIAN_OVERRIDE_SCANNER`.
- 8 new tests (40 API tests total); `docs/PR_GUARDIAN.md` documents the checks and fallback.

### Files changed

- `tools/pr_guardian.py`
- `apps/api/tests/test_guardian_scanner.py`
- `docs/PR_GUARDIAN.md`
- `.archetype/work/AOS-PRG-002.md`
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- `PYTHONPATH=apps/api pytest apps/api/tests -q` -> 40 passed (32 existing + 8 new)
- `python3 -m ruff check apps/api tools` -> exit 0; compileall -> exit 0
- Guardian self-run: "Scanner-informed checks: consulted 3 risk signals." (live in-repo scan path exercised)

### Known Risks

- Manifest basename list in the guardian is intentionally self-contained and could drift from the scanner's MANIFEST_KINDS if ecosystems are added; documented in code.

### Blockers

- None.

### Verification Status

Verification pending

### Verification Level

Level 2

### Verification Method

Local ruff/compileall/pytest plus guardian self-run exercising the live in-repo scan path. GitHub CI pending on the PR.

### Evidence

- 40/40 tests green; ruff/compileall exit 0; self-run consulted 3 live risk signals without crashing.

### Limitations

Level 3 pending. Guardian exit semantics unchanged (verified against an empty body).

### Required Next Verifier

GitHub CI / PR Guardian, then Orchestrator merge review under the Manual Merge Gate.

### Next Recommended Step

Merge the AOS-PRG-002 PR after CI passes. Loop continues: AOS-DEC-001 (Plane AOS-10), AOS-LEARN-001 (AOS-11), AOS-ALPHA-001 (AOS-12) close Sprint 3 and v0.1.

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