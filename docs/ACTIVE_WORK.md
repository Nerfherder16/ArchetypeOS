# Active Work

## Purpose

This file is the markdown fallback execution board for ArchetypeOS.

## Active Work Items

### AOS-CI-001 — Verification Protocol

- Status: Merged
- Owner: CI / DevOps Agent
- PR: #6
- Verification Status: Verified

### AOS-ORCH-001 — Orchestration State Discipline

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #3

### AOS-RUNTIME-001 — Repository Registry MVP

- Status: Merged
- Owner: Runtime Agent
- PR: #5
- Verification Status: Verified

### AOS-ORCH-002 — Branch Isolation / Worktree Protocol

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #8
- Verification Status: Verified

### AOS-PMO-001 — Operating Loop Roadmap Review

- Status: In Review
- Owner: Chief Architect / Orchestrator
- Branch: `docs/operating-loop-roadmap`
- Goal: Inventory current roadmap, document the operating loop, capture Claude Code workflow research, create Plane blueprint, and define Engineering Control Tower.
- Dependencies:
  - PR #5 merged
  - PR #7 merged
  - PR #8 merged
- Acceptance Criteria:
  - roadmap review exists
  - workflow research exists
  - app creation loop exists
  - Plane blueprint exists
  - Control Tower design exists
  - state files updated
  - verification metadata recorded
- Verification Status: Verification pending
- Verification Level: Level 1
- Verification Method: GitHub connector documentation updates; pending GitHub CI / PR Guardian.
- Evidence: Planning docs added on branch.
- Limitations: Local Level 2 execution unavailable in connector-only session.
- Required Next Verifier: GitHub CI / PR Guardian.

### AOS-RUNTIME-002 — Repository Scanner MVP

- Status: Ready
- Owner: Runtime Agent
- Branch: TBD
- Goal: Add read-only repository scanner.
- Dependencies:
  - AOS-RUNTIME-001
  - AOS-ORCH-002
  - AOS-PMO-001
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
  - branch isolation/worktree protocol
  - repository scanner output shape
- Acceptance Criteria:
  - knowledge structure exists
  - manifest schema exists
  - hot/index/log/overview pages exist
  - verification metadata recorded in handoff and PR

## Blocked Work

- Plane sync is blocked until local Plane is available again.

## Deferred Work

- desktop automation
- browser automation
- wake word
- full voice streaming
- marketplace
- simulation lab
- graph database

## Update Rule

Every active branch or PR must update this file when work status changes.