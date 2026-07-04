# Handoff

## Purpose

This file records the latest durable handoff for ArchetypeOS work.

Every engineering session should end by updating this file or creating a dated handoff artifact.

## Latest Handoff

### Date

2026-07-04

### Completed

- PR #1 merged: runtime foundation
- PR #2 merged: CI and deterministic PR Guardian
- PR #3 merged: CI enforcement and branch protection documentation
- Orchestration state discipline proposed in `docs/orchestration-state`
- Verification Protocol proposed in `codex/verification-protocol`

### Current Branch

- `codex/verification-protocol`

### Current Work

Add mandatory verification protocol, verification metadata requirements, PR Guardian verification metadata parsing, and provider-based verification architecture notes.

### Known Risks

- Long-running conversations create context rot.
- Plane may be unavailable due to local outage.
- Agents need hierarchy and communication rules before parallel execution expands.
- Agents may run in constrained environments where local command execution is unavailable.
- GitHub Actions status may not appear immediately after PR creation.

### Blockers

- None known.

### Verification Status

Verification pending

### Verification Level

Level 1

### Verification Method

Repository verification through GitHub connector inspection and committed patch review. GitHub CI must verify after PR creation.

### Evidence

- `docs/VERIFICATION_PROTOCOL.md` created.
- `tools/pr_guardian.py` updated to require verification metadata.
- `.github/pull_request_template.md` updated with verification fields.
- `scripts/pre_pr_guardian.sh` updated with temporary local verification metadata fallback.
- Governance docs updated to point future agents at the protocol.

### Limitations

Local Level 2 execution was not available in this connector-only session. GitHub CI Level 3 verification must run on the draft PR.

### Required Next Verifier

GitHub CI / PR Guardian, then human reviewer.

### Next Recommended Step

Review the draft PR for the Verification Protocol, wait for CI, and merge only after verification metadata and CI checks satisfy the protocol.

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
