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

- Status: Merged
- Owner: Runtime Agent
- PR: #14
- Verification Status: Verified
- Notes: Level 3 GitHub CI evidence in PR #14 (runs 28726472816 and 28726897393, all jobs green including compose smoke). Merge commit `856e5ff`.
- Required Next Verifier: None.

### AOS-PROC-001 — Build Process Hardening

- Status: In Progress
- Owner: CI/DevOps + Orchestrator
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
- Plane: AOS-2
- PR: to be opened
- Spec: `.archetype/work/AOS-PROC-001.md`
- Goal: Enforce acceptance-evidence in PR Guardian for code-path PRs, add scan-endpoint integration test coverage and a shared test fixture, and pin the local dev toolchain.
- Acceptance Criteria (summary; full criteria with evidence pointers in the spec):
  - PR Guardian blocks code PRs missing `## Acceptance Evidence` or missing an `evidence:` bullet under it (codes `missing-acceptance-evidence`, `empty-acceptance-evidence`); override `PR_GUARDIAN_OVERRIDE_ACCEPTANCE`.
  - 4 new scan-endpoint integration tests pass (`test_scan_endpoint_produces_report_dna_and_artifact`, `test_scan_endpoint_is_read_only_against_scanned_repo`, `test_scan_endpoint_404_for_unknown_repository`, `test_scan_endpoint_rescan_updates_dna`).
  - `requirements-dev.txt` (ruff==0.8.6, pytest==8.3.4) and `.python-version` (3.12) pin the toolchain.
- Verification Status: Verification pending
- Verification Level: Level 2
- Verification Method: local ruff/compileall/pytest (20 API tests including the 4 new scan-endpoint integration tests) plus PR Guardian self-checks, run in an isolated remote session
- Evidence: exit codes 0 for ruff, compileall, and pytest
- Limitations: CI pending on PR
- Required Next Verifier: GitHub CI / PR Guardian, then Orchestrator

### AOS-KNOW-001 — Knowledge Vault Seed

- Status: Ready
- Notes: Dependencies are now satisfied; scanner output shape is documented in `docs/REPOSITORY_SCANNER.md`.
- Owner: Knowledge Agent
- Branch: TBD
- Plane: AOS-3
- Spec: `.archetype/work/AOS-KNOW-001.md`
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

- Plane back online; the `ArchetypeOS` Plane project is the live board.
- Local WSL/Docker Level 2 verification is still listed pending workstation confirmation.

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

Work status changes update both Plane and this file; on conflict, this file (markdown) wins until AOS-9 defines full sync discipline.