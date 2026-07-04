# Active Work

## Purpose

This file is the markdown fallback execution board for ArchetypeOS.

It complements Plane. If Plane is unavailable, this file remains the active work source of truth.

## Work States

- Proposed
- Ready
- In Progress
- Blocked
- In Review
- Merged
- Deferred

## Active Work Items

### AOS-CI-001 — Verification Protocol

- Status: Merged
- Owner: CI / DevOps Agent
- Branch: `codex/verification-protocol`
- PR: #6
- Goal: Make verification a mandatory engineering artifact across local, connector, CI, runtime, and human-verification environments.
- Verification Status: Verified
- Verification Level: Level 3
- Verification Method: GitHub Actions CI and PR Guardian
- Evidence: PR #6 merged after successful CI run `28710292267`.
- Limitations: Local Level 2 execution was unavailable in the connector-only session.
- Required Next Verifier: None.

### AOS-ORCH-001 — Orchestration State Discipline

- Status: Merged
- Owner: Chief Architect / Orchestrator
- Branch: `docs/orchestration-state`
- PR: #3
- Goal: Add durable orchestration docs and state files so future sessions can restart without context rot.
- Acceptance Criteria:
  - `docs/ORCHESTRATION_ENGINE.md` exists
  - `docs/AGENT_HIERARCHY_AND_COMMUNICATION.md` exists
  - `docs/CURRENT_STATE.md` exists
  - `docs/ACTIVE_WORK.md` exists
  - `docs/HANDOFF.md` exists
  - `docs/RECENT_CHANGES.md` exists
  - `docs/SESSION_BOOTSTRAP.md` exists
  - Capability Map updated

### AOS-RUNTIME-001 — Repository Registry MVP

- Status: In Review
- Owner: Runtime Agent
- Branch: `codex/repository-registry-mvp`
- PR: #5
- Goal: Implement the first project/repository registry flow.
- Dependencies:
  - Orchestration state discipline merged
  - Verification Protocol merged
  - v0.1 scope remains locked
- Acceptance Criteria:
  - Project model exists
  - Repository model exists
  - repository can be registered by local path
  - repository mounts remain read-only by default
  - API tests exist
  - docs updated
  - verification metadata recorded in handoff and PR
- Verification Status: Verification pending
- Verification Level: Level 1
- Verification Method: CI / DevOps connector-backed rebase onto `main`, repository inspection, and pending GitHub CI rerun.
- Evidence: PR #5 branch reset onto PR #6 main commit and repository registry tests reapplied.
- Limitations: Local Level 2 execution unavailable because the runtime cannot resolve `github.com`.
- Required Next Verifier: GitHub CI / PR Guardian.

### AOS-RUNTIME-002 — Repository Scanner MVP

- Status: Proposed
- Owner: Runtime Agent
- Branch: TBD
- Goal: Add read-only repository scanner.
- Dependencies:
  - AOS-RUNTIME-001
- Acceptance Criteria:
  - scanner detects folders, languages, manifests, Docker files, CI files, and basic risks
  - scanner writes report artifact
  - no repository writes occur
  - verification metadata recorded in handoff and PR

### AOS-KNOW-001 — Knowledge Vault Seed

- Status: Proposed
- Owner: Knowledge Agent
- Branch: TBD
- Goal: Create initial knowledge vault structure and manifest.
- Dependencies:
  - repository registry model
- Acceptance Criteria:
  - `knowledge/` structure exists
  - manifest schema exists
  - hot/index/log/overview pages exist
  - verification metadata recorded in handoff and PR

## Blocked Work

None.

## Deferred Work

- desktop automation
- browser automation
- wake word
- full voice streaming
- autonomous coding
- marketplace
- simulation lab
- graph database
- automated Verification Engine provider selection

## Update Rule

Every active branch or PR must update this file when work status changes, including verification status and required next verifier.
