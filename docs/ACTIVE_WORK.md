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
  - v0.1 scope remains locked
- Acceptance Criteria:
  - Project model exists
  - Repository model exists
  - repository can be registered by local path
  - repository mounts remain read-only by default
  - API tests exist
  - docs updated

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

## Update Rule

Every active branch or PR must update this file when work status changes.