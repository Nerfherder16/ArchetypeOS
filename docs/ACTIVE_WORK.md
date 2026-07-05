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
- PR: #6
- Verification Status: Verified
- Required Next Verifier: None.

### AOS-ORCH-001 — Orchestration State Discipline

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #3
- Verification Status: Verified
- Required Next Verifier: None.

### AOS-RUNTIME-001 — Repository Registry MVP

- Status: Merged
- Owner: Runtime Agent
- PR: #5
- Verification Status: Verified
- Required Next Verifier: None.

### AOS-ORCH-002 — Branch Isolation / Worktree Protocol

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #8
- Verification Status: Verified
- Required Next Verifier: None.

### AOS-ORCH-003 — Agent Communication Bus / PR Monitoring Skill

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #7
- Verification Status: Verified
- Required Next Verifier: None.

### AOS-REVIEW-001 — Independent Architecture Review Artifact

- Status: Merged
- Owner: External Review / Chief Architect triage
- PR: #10
- Verification Status: Verified
- Required Next Verifier: None.

### AOS-STRATEGY-001 — Engineering OS Strategy / WSL Runtime Target

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #11
- Verification Status: Verified
- Required Next Verifier: None.

### AOS-PMO-001 — Operating Loop Planning Recovery

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #12
- Verification Status: Verified
- Notes: Restored planning docs from closed PR #9 without stale state file changes.
- Required Next Verifier: None.

### AOS-PMO-002 — State Reconciliation

- Status: Merged (PR #13)
- Owner: Chief Architect / Orchestrator
- Branch: `docs/state-reconciliation`
- Goal: Reconcile durable state files after recent PRs so the repo accurately reflects current status before implementation resumes.
- Dependencies:
  - PR #7 merged
  - PR #8 merged
  - PR #10 merged
  - PR #11 merged
  - PR #12 merged
- Acceptance Criteria:
  - `docs/CURRENT_STATE.md` reflects latest merged PRs
  - `docs/ACTIVE_WORK.md` reflects true task statuses
  - `docs/HANDOFF.md` has current next step
  - `docs/RECENT_CHANGES.md` is updated
  - Plane remains pinned/offline
  - AOS-RUNTIME-002 is clearly next
- Verification Status: Verified (merged via PR #13 with CI)
- Required Next Verifier: None.

### AOS-RUNTIME-002 — Repository Scanner MVP

- Status: In Review
- Owner: Runtime Agent
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
- PR: to be opened
- Goal: Add read-only repository scanner.
- Dependencies:
  - AOS-RUNTIME-001
  - AOS-ORCH-002
  - AOS-STRATEGY-001
  - AOS-PMO-002
- Acceptance Criteria:
  - scanner detects folders, languages, manifests, Docker files, CI files, and basic risks
  - scanner writes report artifact
  - no repository writes occur
  - verification metadata recorded in handoff and PR
  - tests exist and pass in CI
- Verification Status: Verification pending
- Verification Level: Level 2
- Verification Method: local ruff 0.8.6 + compileall + pytest (16 API tests, 1 worker test) in isolated remote session
- Evidence: exit codes 0 for ruff/compileall/pytest; self-scan of ArchetypeOS repo produced a correct report
- Limitations: local Python 3.11 vs CI 3.12; web build and compose smoke pending in CI; user workstation WSL/Docker still blocked; GitHub CI / PR Guardian pending
- Required Next Verifier: GitHub CI / PR Guardian, then Orchestrator merge review.

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
  - `knowledge/` structure exists
  - manifest schema exists
  - hot/index/log/overview pages exist
  - verification metadata recorded in handoff and PR

## Blocked Work

- Plane sync is blocked until local Plane is available again.
- Local WSL/Docker Level 2 verification is blocked until power and workstation access return.

## Deferred Work

- desktop automation
- browser automation
- wake word
- full voice streaming
- autonomous coding without approval gates
- marketplace
- simulation lab
- graph database
- automated Verification Engine provider selection

## Update Rule

Every active branch or PR must update this file when work status changes, including verification status and required next verifier.