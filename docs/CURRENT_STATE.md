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

## Current Objective

Review and verify AOS-RUNTIME-001 — Repository Registry MVP without expanding v0.1 scope.

## Active Branch

- `codex/repository-registry-mvp`

## CI Status

- CI exists
- PR Guardian exists
- Branch protection should be enforced or documented according to `docs/BRANCH_PROTECTION.md`
- Verification Protocol is active; PR Guardian expects verification metadata in PR bodies
- AOS-RUNTIME-001 API tests have been added on the active branch
- Fresh GitHub CI rerun is required after connector-backed rebase onto `main`

## Verification Status

- Status: Verification pending
- Level: Level 1
- Method: CI / DevOps connector-backed rebase onto `main`, repository inspection, and pending GitHub CI rerun
- Evidence: PR #5 branch reset onto PR #6 main commit and repository registry API tests reapplied
- Limitations: Local Level 2 execution was unavailable because the runtime cannot resolve `github.com`
- Required Next Verifier: GitHub CI / PR Guardian

## In Scope Now

- project model verification
- repository model verification
- local-path repository registration
- read-only repository registration default
- API tests for the repository registry flow
- durable state updates for AOS-RUNTIME-001
- verification metadata compliance

## Out Of Scope Now

- repository scanner expansion beyond existing registry-adjacent behavior
- desktop automation
- browser automation
- wake word
- autonomous coding
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

Wait for PR #5 CI / PR Guardian after rebase. Merge only when verification status is `Verified` or approved `Verified with warnings`.

## Required Reading For New Sessions

1. `docs/CURRENT_STATE.md`
2. `docs/ACTIVE_WORK.md`
3. `docs/HANDOFF.md`
4. `docs/SESSION_BOOTSTRAP.md`
5. `docs/CAPABILITY_MAP.md`
6. `docs/V0_1_SCOPE_LOCK.md`
7. `docs/CONCRETE_BUILD_PATH.md`
8. `docs/VERIFICATION_PROTOCOL.md`
9. Relevant RFCs and domain docs

## Update Rule

Update this file after every meaningful PR merge, scope change, blocker, or sprint transition.
