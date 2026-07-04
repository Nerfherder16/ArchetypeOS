# Recent Changes

## Purpose

This file gives new sessions a quick chronological view of what changed recently.

It is not a replacement for Git history. It is a human-readable coordination log.

## 2026-07-04

### Merged

- PR #1: Runtime foundation
- PR #2: CI and deterministic PR Guardian
- PR #3: CI enforcement and branch protection documentation
- PR #6: Verification Protocol
- PR #5: Repository Registry MVP

### Added In Current Branch

- `docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md`

### Updated In Current Branch

- `docs/SESSION_BOOTSTRAP.md` now requires the Branch Isolation / Worktree Protocol during startup.
- `docs/CAPABILITY_MAP.md` now includes branch isolation, worktree protocol, connector fallback isolation, backup head preservation, and branch freshness validation.
- `docs/CURRENT_STATE.md`, `docs/ACTIVE_WORK.md`, and `docs/HANDOFF.md` now track AOS-ORCH-002.

### Verified In Current Branch

- One work package = one branch = one isolated worktree documented.
- Connector fallback documented.
- Backup head before force/reset documented.
- Branch freshness before ready-for-review documented.
- Local agents for heavy edits documented.
- ChatGPT connector review/orchestration role documented.

### Why It Matters

AOS-ORCH-002 makes parallel agent work safer by requiring branch and worktree isolation before ArchetypeOS expands into more concurrent runtime, knowledge, and CI work.

Connector-only sessions now have a documented fallback: use one branch as the logical worktree, preserve backup heads before force/reset, and rely on GitHub CI / PR Guardian for final verification.

## Update Rule

Update this file after each meaningful merge or milestone.
