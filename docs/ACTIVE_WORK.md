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

- Status: Merged
- Owner: Runtime Agent
- Branch: `codex/repository-registry-mvp`
- PR: #5
- Goal: Implement the first project/repository registry flow.
- Verification Status: Verified
- Verification Level: Level 3
- Verification Method: GitHub Actions CI / PR Guardian after CI / DevOps connector-backed rebase onto `main`.
- Evidence: PR #5 merged after successful CI run `28710932992`.
- Limitations: Local Level 2 execution unavailable because the runtime could not resolve `github.com`.
- Required Next Verifier: None.

### AOS-ORCH-002 — Branch Isolation / Worktree Protocol

- Status: In Review
- Owner: Chief Architect / Orchestrator
- Branch: `docs/branch-isolation-worktree-protocol`
- Goal: Document one work package = one branch = one isolated worktree, including connector fallback rules.
- Dependencies:
  - Orchestration state discipline merged
  - Verification Protocol merged
  - Runtime Registry MVP merged
- Acceptance Criteria:
  - `docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md` exists
  - one work package = one branch = one isolated worktree documented
  - connector fallback documented
  - one branch per task documented
  - backup head before force/reset documented
  - branch freshness before ready-for-review documented
  - local agents recommended for heavy edits
  - ChatGPT connector role constrained to review/orchestration by default
  - session bootstrap updated
  - Capability Map updated
  - verification metadata recorded in handoff and PR
- Verification Status: Verification pending
- Verification Level: Level 1
- Verification Method: GitHub connector repository inspection and pending GitHub CI / PR Guardian.
- Evidence: Protocol doc added and state docs updated on branch.
- Limitations: Local Level 2 execution unavailable in connector-only session.
- Required Next Verifier: GitHub CI / PR Guardian.

### AOS-RUNTIME-002 — Repository Scanner MVP

- Status: Proposed
- Owner: Runtime Agent
- Branch: TBD
- Goal: Add read-only repository scanner.
- Dependencies:
  - AOS-RUNTIME-001
  - AOS-ORCH-002
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
