# Current State

## Purpose

This file is the durable project state checkpoint for ArchetypeOS.

Every new engineering session should read this before planning or implementation.

## Status

- Project: ArchetypeOS
- Phase: v0.1 foundation
- Current sprint: Sprint 2 — Operating Loop and first runtime proof
- Source of truth: GitHub repository
- First runtime target: Windows 11 + WSL 2 Ubuntu
- Plane status: pinned/offline due to local power outage; markdown state files remain fallback execution board

## Recently Merged

- PR #1: Runtime foundation
- PR #2: CI and deterministic PR Guardian
- PR #3: CI enforcement and branch protection documentation
- PR #5: Repository Registry MVP
- PR #6: Verification Protocol
- PR #7: Agent Communication Bus and PR Monitoring skill
- PR #8: Branch Isolation / Worktree Protocol
- PR #10: Independent Architecture Review artifact
- PR #11: Engineering OS Strategy and WSL Windows 11 Runtime Target
- PR #12: Operating Loop planning docs recovery
- PR #13: State reconciliation

## Current Objective

AOS-RUNTIME-002 — Repository Scanner MVP implemented on `claude/aos-runtime-002-scanner-1egyjw`; PR to be opened and verified by CI.

## Active Branch

- `claude/aos-runtime-002-scanner-1egyjw`

## CI Status

- CI exists
- PR Guardian exists
- Verification Protocol is active
- PR Monitoring skill exists
- Branch Isolation / Worktree Protocol is active
- WSL Windows 11 is the accepted first runtime target

## Verification Status

- Status: Verification pending
- Level: Level 2
- Method: local ruff 0.8.6 + compileall + pytest (16 API tests, 1 worker test) in isolated remote session
- Evidence: exit codes 0 for ruff/compileall/pytest; self-scan of ArchetypeOS repo produced a correct report
- Limitations: local Python 3.11 vs CI 3.12; web build and compose smoke pending in CI; user workstation WSL/Docker still blocked; GitHub CI / PR Guardian pending
- Required Next Verifier: GitHub CI / PR Guardian, then Orchestrator merge review

## In Scope Now

- repository scanner MVP extension
- scanner docs
- state updates

## Out Of Scope Now

- local WSL/Docker verification
- Plane sync
- desktop automation
- browser automation
- wake word
- autonomous coding without approval gates
- production deployment

## Open Decisions

| Decision | Status | Notes |
| --- | --- | --- |
| Plane integration depth | Pinned | Resume when local Plane returns. |
| Agent dashboard implementation | Deferred | Engineering Control Tower design exists; implementation comes after scanner/runtime data. |
| Multi-agent live communication | Deferred | Durable artifact communication first. |
| Verification Engine implementation | Deferred | Protocol and provider abstraction first; automated provider selection later. |
| Local Level 2 verification | Blocked | Resume when Windows 11/WSL workstation access returns. |

## Blockers

- Local Plane unavailable during power outage.
- Local WSL/Docker Level 2 verification unavailable during power outage.

## Next Recommended Task

Merge AOS-RUNTIME-002 — Repository Scanner MVP after CI and PR Guardian pass. Then assign AOS-KNOW-001 — Knowledge Vault Seed.

## Required Reading For New Sessions

1. `docs/CURRENT_STATE.md`
2. `docs/ACTIVE_WORK.md`
3. `docs/HANDOFF.md`
4. `docs/RECENT_CHANGES.md`
5. `docs/CAPABILITY_MAP.md`
6. `docs/V0_1_SCOPE_LOCK.md`
7. `docs/CONCRETE_BUILD_PATH.md`
8. `docs/VERIFICATION_PROTOCOL.md`
9. `docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md`
10. `docs/ENGINEERING_OS_STRATEGY.md`
11. `docs/WSL_WIN11_RUNTIME_TARGET.md`
12. Relevant RFCs and domain docs

## Update Rule

Update this file after every meaningful PR merge, scope change, blocker, or sprint transition.