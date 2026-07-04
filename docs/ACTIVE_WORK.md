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

- Status: In Review
- Owner: CI / DevOps Agent
- Branch: `codex/verification-protocol`
- Goal: Make verification a mandatory engineering artifact across local, connector, CI, runtime, and human-verification environments.
- Acceptance Criteria:
  - `docs/VERIFICATION_PROTOCOL.md` exists
  - verification levels 0 through 5 are defined
  - deterministic verification decision tree exists
  - handoff template includes verification metadata
  - session bootstrap requires verification metadata
  - PR Guardian expects verification metadata in PR descriptions
  - verification provider abstraction is documented
  - Capability Map updated
  - draft PR opened
- Verification Status: Verification pending
- Verification Level: Level 1
- Verification Method: GitHub connector repository inspection and patch review
- Evidence: Protocol, docs, PR template, PR Guardian parser, and local pre-PR fallback body updated on branch
- Limitations: Local Level 2 execution unavailable in current session
- Required Next Verifier: GitHub CI / PR Guardian

### AOS-ORCH-001 — Orchestration State Discipline

- Status: In Progress
- Owner: Chief Architect / Orchestrator
- Branch: `docs/orchestration-state`
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

- Status: Ready
- Owner: Runtime Agent
- Branch: TBD
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
