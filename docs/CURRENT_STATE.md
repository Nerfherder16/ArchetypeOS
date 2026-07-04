# Current State

## Purpose

This file is the durable project state checkpoint for ArchetypeOS.

Every new engineering session should read this before planning or implementation.

## Status

- Project: ArchetypeOS
- Phase: v0.1 foundation
- Current sprint: Sprint 1 — Runtime foundation and orchestration discipline
- Source of truth: GitHub repository
- Plane status: local instance may be unavailable; markdown state files are fallback execution board

## Recently Merged

- PR #1: Runtime foundation
- PR #2: CI and deterministic PR Guardian
- PR #3: CI enforcement and branch protection documentation
- PR #6: Verification Protocol
- PR #5: Repository Registry MVP

## Current Objective

Document branch isolation and worktree discipline before expanding parallel agent work.

## Active Branch

- `docs/branch-isolation-worktree-protocol`

## CI Status

- CI exists
- PR Guardian exists
- Branch protection should be enforced or documented according to `docs/BRANCH_PROTECTION.md`
- Verification Protocol is active; PR Guardian expects verification metadata in PR bodies
- AOS-ORCH-002 documentation changes are pending GitHub CI / PR Guardian verification

## Verification Status

- Status: Verification pending
- Level: Level 1
- Method: GitHub connector repository inspection for documentation and state updates; pending GitHub CI / PR Guardian
- Evidence: `docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md` added and state docs updated on `docs/branch-isolation-worktree-protocol`
- Limitations: Local Level 2 execution unavailable in connector-only session
- Required Next Verifier: GitHub CI / PR Guardian

## In Scope Now

- branch isolation protocol
- worktree protocol
- connector fallback rules
- backup head preservation before force/reset
- branch freshness checks before ready-for-review
- local-agent versus ChatGPT-connector responsibility split
- durable state updates for AOS-ORCH-002

## Out Of Scope Now

- repository scanner implementation
- desktop automation
- browser automation
- wake word
- autonomous coding without approval gates
- production deployment

## Open Decisions

| Decision | Status | Notes |
| --- | --- | --- |
| Plane integration depth | Deferred | Start with markdown fallback and later sync Plane when available. |
| Agent dashboard implementation | Deferred | Document first, build after v0.1 runtime stabilizes. |
| Multi-agent live communication | Deferred | Start with durable artifact communication. |
| Verification Engine implementation | Deferred | Protocol and provider abstraction first; automated provider selection later. |

## Blockers

- None known.

## Next Recommended Task

Review AOS-ORCH-002, wait for CI / PR Guardian, then merge if verification succeeds. After merge, proceed to AOS-RUNTIME-002 using one branch and one isolated worktree.

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
10. Relevant RFCs and domain docs

## Update Rule

Update this file after every meaningful PR merge, scope change, blocker, or sprint transition.
