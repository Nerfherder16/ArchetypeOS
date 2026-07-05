# Handoff

## Purpose

This file records the latest durable handoff for ArchetypeOS work.

Every engineering session should end by updating this file or creating a dated handoff artifact.

## Latest Handoff

### Date

2026-07-05

### Agent

Orchestrator (Fable 5), delegating to Runtime Agent (Opus) for the code slice and Docs and State Support Agent (Sonnet) for the docs slice

### Task

AOS-PROC-001 — Build Process Hardening

### Branch

`claude/aos-runtime-002-scanner-1egyjw`

### PR

To be opened.

### Status

In Progress — implementation complete, PR pending.

### Completed

- Added a deterministic acceptance-evidence check to PR Guardian (`tools/pr_guardian.py`): code-path PRs (`apps/api/app/`, `apps/worker/app/`, `apps/web/src/`) must carry an `## Acceptance Evidence` section with at least one `evidence:` bullet; blocking codes `missing-acceptance-evidence` and `empty-acceptance-evidence`; override `PR_GUARDIAN_OVERRIDE_ACCEPTANCE`.
- Refactored `apps/api/tests/conftest.py` into a shared `client` fixture used across test modules.
- Added 4 scan-endpoint integration tests in `apps/api/tests/test_scan_endpoint.py`: report+DNA+artifact checksum, read-only snapshot, 404 for unknown repository, rescan updates DNA.
- Fixed a guardian lint issue (F841) surfaced while adding the acceptance-evidence check.
- Pinned the local dev toolchain: `requirements-dev.txt` (ruff==0.8.6, pytest==8.3.4), `.python-version` (3.12).
- Added `docs/rfc/RFC-0003-Work-Package-Specs.md`, `.archetype/work/TEMPLATE.md`, `.archetype/work/AOS-PROC-001.md` (dogfood spec), and `.archetype/work/AOS-KNOW-001.md` (next-task spec).
- Documented the acceptance-evidence check and a new Manual Merge Gate protocol in `docs/PR_GUARDIAN.md`.
- Documented the pre-existing compose `:ro` read-only runtime enforcement in `docs/REPOSITORY_SCANNER.md`.
- Recorded the Plane board going live: project `ArchetypeOS` (AOS) seeded with 12 labels, default states, and work items AOS-1..AOS-9; GitHub issues #16-#20 migrated and closed.

### Files changed

- `tools/pr_guardian.py`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_scan_endpoint.py`
- `requirements-dev.txt`
- `.python-version`
- `docs/rfc/RFC-0003-Work-Package-Specs.md`
- `.archetype/work/TEMPLATE.md`
- `.archetype/work/AOS-PROC-001.md`
- `.archetype/work/AOS-KNOW-001.md`
- `docs/PR_GUARDIAN.md`
- `docs/REPOSITORY_SCANNER.md`
- `docs/PLANE_PROJECT_BLUEPRINT.md`
- `docs/ACTIVE_WORK.md`
- `docs/CURRENT_STATE.md`
- `docs/HANDOFF.md`
- `docs/RECENT_CHANGES.md`

### Tests run

- `PYTHONPATH=apps/api pytest apps/api/tests -q` -> 20 passed
- `python3 -m ruff check apps/api apps/worker tools` (ruff 0.8.6) -> exit 0
- `python3 -m compileall` -> exit 0

### Known Risks

- Local WSL/Docker Level 2 verification on the user's workstation remains pending confirmation (not cleared by Plane coming back online).
- Plane and the markdown state files are now dual sources of truth; full sync discipline is not yet defined (tracked as AOS-9).
- State files are high-conflict coordination files and should be updated carefully in focused PRs.
- Connector write/branch operations can be brittle; preserve backup heads before destructive branch operations.

### Blockers

- Local WSL/Docker verification on the user's workstation: pending confirmation.

### Verification Status

Verification pending

### Verification Level

Level 2

### Verification Method

Local ruff/compileall/pytest (20 API tests including the 4 new scan-endpoint integration tests) plus PR Guardian self-checks, run in an isolated remote session bound to `claude/aos-runtime-002-scanner-1egyjw`.

### Evidence

- `PYTHONPATH=apps/api pytest apps/api/tests -q` -> 20 passed
- `ruff check apps/api apps/worker tools` -> exit 0
- `python -m compileall` -> exit 0

### Limitations

GitHub CI has not yet run because the PR is not yet opened. Required status checks cannot be enforced as a merge gate on this repository plan, so CI green must be confirmed manually on the head SHA at merge time (see `docs/PR_GUARDIAN.md` Manual Merge Gate). User workstation WSL/Docker verification remains pending confirmation.

### Required Next Verifier

GitHub CI / PR Guardian, then Orchestrator review.

### Next Recommended Step

Open the PR for AOS-PROC-001, babysit CI, merge once green and confirmed on the head SHA, then assign AOS-KNOW-001 — Knowledge Vault Seed to the Knowledge Agent using one branch and one isolated worktree.

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