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
- Plane status: back online and fully synced; `ArchetypeOS` project live (AOS-1..AOS-9, 10 modules, Sprint 2 cycle); markdown state files remain the durable fallback board and win on conflict

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
- PR #24: Post-merge state reconciliation for AOS-KNOW-001
- PR #25: Architecture Spine Graph API (AOS-ARCH-001)

## Current Objective

Reconcile state after the PR #25 merge, then start AOS-LOCAL-001 (WSL verification on `teevee-1`) and/or AOS-8 (control tower dashboard slice, now unblocked by the graph API).

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
- Level: Level 1
- Method: post-merge state-file reconciliation; local PR Guardian on the docs diff; GitHub CI pending after PR creation. AOS-ARCH-001 itself is Verified (Level 3, PR #25, CI run 28729930724 all green).
- Evidence: state files reconciled to the PR #25 merge (`b9b3024`); Plane synced (AOS-3/AOS-5 Done)
- Limitations: docs-only change
- Required Next Verifier: GitHub CI / PR Guardian, then Orchestrator review

## In Scope Now

- post-merge state reconciliation for PR #25
- AOS-LOCAL-001 readiness (workstation unblocked)

## Out Of Scope Now

- Plane two-way sync automation (AOS-9, not started)
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
| Local Level 2 verification | Unblocked | Workstation `teevee-1` available via Tailscale; execute AOS-LOCAL-001 there. |

## Blockers

- None. Plane is back online and synced; workstation `teevee-1` confirmed available via Tailscale.

## Next Recommended Task

Merge this state reconciliation PR after CI passes. Then execute AOS-LOCAL-001 on `teevee-1` (first Level 4 runtime verification on the real target) and/or start AOS-8 (control tower dashboard slice).

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