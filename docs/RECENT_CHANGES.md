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

- `docs/ORCHESTRATION_ENGINE.md`
- `docs/AGENT_HIERARCHY_AND_COMMUNICATION.md`
- `docs/CURRENT_STATE.md`
- `docs/ACTIVE_WORK.md`
- `docs/HANDOFF.md`
- `docs/RECENT_CHANGES.md`
- `docs/SESSION_BOOTSTRAP.md`
- `docs/VERIFICATION_PROTOCOL.md`

### Updated In Current Branch

- `docs/PR_GUARDIAN.md` now documents verification metadata requirements.
- `tools/pr_guardian.py` now checks PR body verification metadata.
- `.github/pull_request_template.md` now includes verification metadata.
- `scripts/pre_pr_guardian.sh` now includes temporary local verification metadata for local runs without a PR body file.
- `docs/AUTHORITY_APPROVAL_ENGINE.md` maps verification providers to authority levels.
- `docs/CAPABILITY_MAP.md` includes Verification Protocol and provider abstraction under Layer 7.

### Why It Matters

The project is moving from one long-lived conversation to a durable, multi-agent orchestration model.

State must live in the repository so future sessions can restart from current truth without relying on chat memory.

Verification must also live in the repository and PR metadata so agents can work safely across local runtimes, GitHub CI, constrained connectors, future MCP providers, and human review.

## Update Rule

Update this file after each meaningful merge or milestone.
