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
- Plane status: `ArchetypeOS` project live and seeded (AOS-1..AOS-9, 10 modules, Sprint 2 cycle); briefly down again late 2026-07-05 (AOS-3 → Done update pending); markdown state files remain the durable fallback board and win on conflict

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
- PR #14: Repository Scanner MVP (AOS-RUNTIME-002)
- PR #15: Post-merge state reconciliation for AOS-RUNTIME-002
- PR #21: Build Process Hardening (AOS-PROC-001)
- PR #22: Post-merge state reconciliation for AOS-PROC-001
- PR #23: Knowledge Vault Seed (AOS-KNOW-001)

## Current Objective

AOS-ARCH-001 — Architecture Spine Graph API (Plane AOS-5) is in review on this branch: graph query/correction endpoints plus rescan upsert preserving node ids and manual corrections. PR to be opened.

## Active Branch

- `claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` for post-merge state reconciliation)

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
- Method: local ruff 0.8.6 + compileall + pytest (25 API tests including 5 new architecture tests, existing scan tests unchanged) in the isolated remote session; GitHub CI pending after PR creation
- Evidence: exit codes 0 for ruff, compileall, and pytest
- Limitations: SQLite-only locally; Plane still down (AOS-3 → Done and AOS-5 → In Progress board updates pending); markdown carries state per the precedence rule
- Required Next Verifier: GitHub CI / PR Guardian, then Orchestrator review

## In Scope Now

- architecture graph API (AOS-ARCH-001)
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
| Plane integration depth | Board adopted | Sync discipline = AOS-9. |
| Agent dashboard implementation | Deferred | Engineering Control Tower design exists; implementation comes after scanner/runtime data. |
| Multi-agent live communication | Deferred | Durable artifact communication first. |
| Verification Engine implementation | Deferred | Protocol and provider abstraction first; automated provider selection later. |
| Local Level 2 verification | Blocked | Resume when Windows 11/WSL workstation access returns. |

## Blockers

- Local WSL/Docker Level 2 verification on the user's workstation: pending confirmation.

## Next Recommended Task

Merge the AOS-ARCH-001 PR after CI passes under the Manual Merge Gate. Then AOS-8 (control tower dashboard slice, now unblocked by the graph API) or AOS-4 (scan history) are the leading candidates; AOS-7 awaits workstation confirmation.

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