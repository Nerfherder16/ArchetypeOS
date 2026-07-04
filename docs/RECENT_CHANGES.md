# Recent Changes

## Purpose

This file gives new sessions a quick chronological view of what changed recently.

It is not a replacement for Git history. It is a human-readable coordination log.

## 2026-07-04

### Merged

- PR #1: Runtime foundation
- PR #2: CI and deterministic PR Guardian
- PR #3: CI enforcement and branch protection documentation

### Added In Current Branch

- `apps/api/tests/test_repository_registry.py`
- AOS-RUNTIME-001 state updates in `docs/CURRENT_STATE.md`, `docs/ACTIVE_WORK.md`, and `docs/HANDOFF.md`

### Verified In Current Branch

- Project creation API flow covered by tests
- Repository registration by local path covered by tests
- Read-only repository default covered by tests
- Repository path boundary rejection covered by tests
- Missing project rejection covered by tests

### Why It Matters

AOS-RUNTIME-001 turns the existing registry API/model surface into a guarded MVP flow with explicit API tests and durable handoff state.

## Update Rule

Update this file after each meaningful merge or milestone.
