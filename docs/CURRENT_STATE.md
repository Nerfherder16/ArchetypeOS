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

## Current Objective

Establish durable orchestration and anti-context-rot workflow before deeper implementation continues.

## Active Branch

- `docs/orchestration-state`

## CI Status

- CI exists
- PR Guardian exists
- Branch protection should be enforced or documented according to `docs/BRANCH_PROTECTION.md`

## In Scope Now

- Orchestration Engine documentation
- agent hierarchy and communication model
- state files
- session bootstrap protocol
- handoff protocol
- Plane integration strategy

## Out Of Scope Now

- new runtime implementation
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

## Blockers

- None known.

## Next Recommended Task

Create the first implementation work package for the Runtime Agent: repository registry and repository scan MVP.

## Required Reading For New Sessions

1. `docs/CURRENT_STATE.md`
2. `docs/ACTIVE_WORK.md`
3. `docs/HANDOFF.md`
4. `docs/SESSION_BOOTSTRAP.md`
5. `docs/CAPABILITY_MAP.md`
6. `docs/V0_1_SCOPE_LOCK.md`
7. `docs/CONCRETE_BUILD_PATH.md`
8. Relevant RFCs and domain docs

## Update Rule

Update this file after every meaningful PR merge, scope change, blocker, or sprint transition.