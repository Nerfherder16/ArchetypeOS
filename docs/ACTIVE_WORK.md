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

- Status: Merged
- Owner: CI/DevOps + Orchestrator
- PR: #21
- Plane: AOS-2 (Done)
- Spec: `.archetype/work/AOS-PROC-001.md`
- Verification Status: Verified
- Notes: Level 3 GitHub CI evidence in PR #21 (run 28728454334, all 5 jobs green). Merge commit `783f329`. First PR merged under the Manual Merge Gate protocol with a head-SHA-pinned verification comment.
- Required Next Verifier: None.

### AOS-KNOW-001 — Knowledge Vault Seed

- Status: Merged
- Owner: Knowledge Agent
- PR: #23
- Plane: AOS-3 (Done)
- Spec: `.archetype/work/AOS-KNOW-001.md`
- Verification Status: Verified
- Notes: Level 3 GitHub CI evidence in PR #23 (run 28728964219, all 5 jobs green). Merge commit `87fa769`. Vault built out to full RFC-0002 structure; `KnowledgePage` API read path explicitly deferred.
- Required Next Verifier: None.

### AOS-ARCH-001 — Architecture Spine Graph API

- Status: Merged
- Owner: Runtime Agent
- PR: #25
- Plane: AOS-5 (Done)
- Spec: `.archetype/work/AOS-ARCH-001.md`
- Verification Status: Verified
- Notes: Level 3 GitHub CI evidence in PR #25 (run 28729930724, all 5 jobs green). Merge commit `b9b3024`. Rescan upsert preserves node ids and manual corrections.
- Required Next Verifier: None.

### AOS-LOCAL-001 — WSL Windows 11 Local Verification

- Status: Merged
- Owner: Human operator (`teevee-1`) + Orchestrator
- PR: #32
- Plane: AOS-7 (Done)
- Spec: `.archetype/work/AOS-LOCAL-001.md`
- Verification Status: Verified
- Notes: Level 4 — operator-executed runbook on the Windows 11 + WSL 2 target; five findings recorded and remediated (PRs #31/#32). Merge commit `d365bcd`.
- Required Next Verifier: None.

### AOS-CTRL-001 — Engineering Control Tower First Dashboard Surface

- Status: Merged
- Owner: Runtime Agent
- PR: #27
- Plane: AOS-8 (Done)
- Spec: `.archetype/work/AOS-CTRL-001.md`
- Verification Status: Verified
- Notes: Level 4 evidence — GitHub CI run 28730415566 all green plus Orchestrator-driven headless-Chromium verification (10/10 checks). Merge commit `32399e0`. Added `GET /repositories/{id}/dna`.
- Required Next Verifier: None.

### AOS-RUNTIME-003 — Repository Scan Persistence and History

- Status: Merged
- Owner: Runtime Agent
- PR: #29
- Plane: AOS-4 (Done)
- Spec: `.archetype/work/AOS-RUNTIME-003.md`
- Verification Status: Verified
- Notes: Level 3 GitHub CI evidence in PR #29 (run 28730851673, all 5 jobs green). Merge commit `7697265`. Versioned scan artifacts fix the rescan overwrite bug; history endpoints added.
- Required Next Verifier: None.

### AOS-PLANE-001 — Plane Board Sync Discipline

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #30
- Plane: AOS-9 (Done)
- Spec: `.archetype/work/AOS-PLANE-001.md`
- Verification Status: Verified
- Notes: Level 3 GitHub CI evidence in PR #30 (run 28731234910, all 5 jobs green). Merge commit `12dc5f7`. Sync Discipline + Board ID Registry live in `docs/PLANE_PROJECT_BLUEPRINT.md`.
- Required Next Verifier: None.

### AOS-PRG-002 — PR Guardian Reads Repository Scanner Output

- Status: Merged
- Owner: Runtime Agent
- PR: #33
- Plane: AOS-6 (Done)
- Spec: `.archetype/work/AOS-PRG-002.md`
- Verification Status: Verified
- Notes: Level 3 evidence — CI green on PR #33 including the guardian job executing the new scanner-informed code live. Merge commit `5f0cfdc`.
- Required Next Verifier: None.

### AOS-DEC-001 — Decision and Research Artifacts

- Status: Merged
- Owner: Runtime Agent
- PR: #34
- Plane: AOS-10 (Done)
- Spec: `.archetype/work/AOS-DEC-001.md`
- Verification Status: Verified
- Notes: Level 4 evidence — CI run 28742814441 all green plus headless-Chromium drive (7/7). Merge commit `fe158fd`. Phase 5 scope-lock criteria closed.
- Required Next Verifier: None.

### AOS-LEARN-001 — Nightly Learning Digest (Manual Run)

- Status: Merged
- Owner: Runtime Agent
- PR: #36
- Plane: AOS-11 (Done)
- Spec: `.archetype/work/AOS-LEARN-001.md`
- Verification Status: Verified
- Notes: Level 4 evidence — CI run 28743687095 all 5 jobs green plus headless-Chromium drive (7/7). Merge commit `8b39e67`. Phase 7 scope-lock criteria closed.
- Required Next Verifier: None.

### AOS-ALPHA-001 — Phase 10 Alpha Review: ArchetypeOS Evaluates ArchetypeOS

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #37
- Plane: AOS-12 (Done) — Sprint 3 complete
- Spec: `.archetype/work/AOS-ALPHA-001.md`
- Verification Status: Verified
- Notes: Level 4 evidence — CI run 28744117867 all 5 jobs green plus the live self-evaluation run itself (`.archetype/alpha/` captures, `docs/ALPHA_REVIEW_V0_1.md`). Merge commit `74c2406`. **Closes Sprint 3 and v0.1.**
- Required Next Verifier: None.

## v0.1 Status

v0.1 is COMPLETE (2026-07-05). All Sprint 1–3 packages merged and verified; Phase 10 Alpha Review published. Sprint 4 — Self-Healing & Learning Loop is now open (operator-approved): every PR, learning moment, and failure ties back into the loops.

### AOS-RUNTIME-004 — /health Graceful Degradation (Alpha Finding #1)

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator
- PR: #39
- Plane: AOS-13 (Done)
- Spec: `.archetype/work/AOS-RUNTIME-004.md`
- Verification Status: Verified
- Notes: Level 4 evidence — CI run 28745707663 all 5 jobs green (the API job exercised the degraded-Redis path, the compose smoke the all-healthy path) plus Orchestrator dual-state live probes. Merge commit `2b8febf`. Alpha finding #1 closed; recorded as LES-005.
- Required Next Verifier: None.

### AOS-LEARN-002 — Learning Feedback Loop, Phase 1 (RFC-0004)

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #40
- Plane: AOS-14 (Done)
- Spec: `.archetype/work/AOS-LEARN-002.md`
- Verification Status: Verified
- Notes: Level 2 (docs-only) — CI run 28747618699 all 5 jobs green; RFC-0004 + lessons registry (LES-001..007) live. Merge commit `e8527b9`.
- Required Next Verifier: None.

### AOS-PRG-003 — Guardian Evolution: Lessons Become Rules (RFC-0004 Phase 2)

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator
- PR: #41
- Plane: AOS-15 (Done) — **Sprint 4 complete**
- Spec: `.archetype/work/AOS-PRG-003.md`
- Verification Status: Verified
- Notes: Level 3 evidence — CI run 28748052521 all 5 jobs green including the guardian job executing the evolved code live on its own PR. Merge commit `98914f7`. LES-003/LES-006 consumed by ID; web-tests acceptance expires 2026-08-01.
- Required Next Verifier: None.

### AOS-ORCH-004 — Sprint 4 Close-Out + Orchestrator Handoff Pack

- Status: Merged
- Owner: Chief Architect / Orchestrator (Fable 5 — final Fable package)
- PR: #42
- Plane: n/a (process package)
- Spec: n/a
- Verification Status: Verified
- Notes: Level 2 (docs/scripts-only) — CI run 28748558659 all 5 jobs green. Merge commit `74e9370`. Delivered the Orchestrator Playbook, committed web-drive harness, Board ID Registry backfill (Sprints 3–4), HANDOFF transition, LES-008. **Sprint 4 complete; orchestration handed to Opus 4.8.**
- Required Next Verifier: None.

## Sprint 5 — Enforcement & Foundations (open)

Cycle `8bc59801-82c5-4550-b188-9f15323a1ddc`. Operator-approved order: AOS-16 (web tests, deadline 2026-08-01) → AOS-17 (Alembic) → AOS-18 (worker pipeline); AOS-21 (second repo) parallel. First package under the Opus 4.8 orchestrator.

### AOS-WEB-001 — Web Test Framework: Playwright Suite, Enforced

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #43
- Plane: AOS-16 (Done)
- Spec: `.archetype/work/AOS-WEB-001.md`
- Verification Status: Verified
- Notes: Level 4 — CI run 28750193960 all 6 jobs green incl. the new `web-e2e` job running Playwright on ubuntu, plus Orchestrator's own headless run (3/3). Merge commit `821171e`. Guardian enforces web tests; accepted-warnings retired; LES-006 deadline closed early; LES-009 recorded.
- Required Next Verifier: None.

### AOS-ALEMBIC-001 — Adopt Alembic Migrations (Baseline)

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #44
- Plane: AOS-17 (Done)
- Spec: `.archetype/work/AOS-ALEMBIC-001.md`
- Verification Status: Verified
- Notes: Level 4 — CI run 28750732119 all 6 jobs green incl. compose-smoke running `alembic upgrade head` against fresh Postgres via the new entrypoint, plus Orchestrator's own sqlite round-trip (no-drift = 0 ops). Merge commit `96550b8`.
- Required Next Verifier: None.

### AOS-CORE-001 — Extract aos_core Shared Package (RFC-0006 Phase 1)

- Status: In Review
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
- Plane: AOS-18 (In Progress, high — Phase 1 tracker), Sprint 5 cycle
- PR: to be opened
- Spec: `.archetype/work/AOS-CORE-001.md`; RFC: `docs/rfc/RFC-0006-Shared-Core-Domain-Library.md` (Accepted)
- Goal: extract an installable `aos_core` package (config/database/models/scanner + new scan/digest service modules) the api consumes; repo-root api Docker build context; alembic retargeted to `aos_core.database.Base`; guardian guards the new boundary. ZERO behavior change. Enables the worker (Phase 2) to run scans in-process.
- Verification Status: Verification pending
- Verification Level: Level 4
- Verification Method: Orchestrator independently verified on a Python 3.12 venv (the pinned interpreter) — `pip install -e ./packages/aos_core`, `PYTHONPATH=apps/api pytest` → **69 passed** (67 original unchanged + 2 new guardian tests), ruff/compileall clean, alembic no-drift = 0 ops with `aos_core.models`, and the guardian running standalone WITHOUT aos_core installed (scanner `sys.path` fallback) — the pr-guardian CI condition; CI (api-tests + web-e2e install aos_core; compose-smoke builds the api image from the new context) pending on PR
- Evidence: 69 tests pass on 3.12; no-drift 0 ops; guardian works without aos_core installed; apps/api/app reduced to main.py + schemas.py
- Limitations: Docker restructure proven only by CI compose-smoke (no local docker); worker unchanged (Phase 2)
- Required Next Verifier: GitHub CI (compose-smoke) / PR Guardian, then Orchestrator

## Blocked Work

- None. Plane is back online and fully synced (AOS-3 and AOS-5 marked Done). Workstation `teevee-1` is confirmed available via Tailscale, unblocking AOS-LOCAL-001.

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

Work status changes update both Plane and this file per the Sync Discipline section in `docs/PLANE_PROJECT_BLUEPRINT.md`; on conflict, this file (markdown) wins.