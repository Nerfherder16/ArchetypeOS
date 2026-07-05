# Current State

## Purpose

This file is the durable project state checkpoint for ArchetypeOS.

Every new engineering session should read this before planning or implementation.

## Status

- Project: ArchetypeOS
- Phase: v0.1 COMPLETE (2026-07-05); post-v0.1 development underway
- Current sprint: Sprint 4 COMPLETE (Self-Healing & Learning Loop, PRs #39-#41); orchestrator handoff pack in review; Sprint 5 awaits operator direction
- Source of truth: GitHub repository
- First runtime target: Windows 11 + WSL 2 Ubuntu
- Plane status: back online and fully synced; `ArchetypeOS` project live (AOS-1..AOS-9, 10 modules, Sprint 2 cycle); markdown state files remain the durable fallback board and win on conflict

## Recently Merged

- PR #1: Runtime foundation
- PR #2: CI and deterministic PR Guardian
- PR #3: CI enforcement and branch protection documentation
- PR #5: Repository Registry MVP
- PR #6: Verification Protocol
- PR #7: Agent Communication Bus and PR Monitoring skill
- PR #8: Branch Isolation / Worktree Protocol
- PR #10: Independent Architecture Review artifact
- PR #11: Engineering OS Strategy and WSL Windows 11 Runtime Target
- PR #12: Operating Loop planning docs recovery
- PR #13: State reconciliation
- PR #14: Repository Scanner MVP (AOS-RUNTIME-002)
- PR #15: Post-merge state reconciliation for AOS-RUNTIME-002
- PR #21: Build Process Hardening (AOS-PROC-001)
- PR #22: Post-merge state reconciliation for AOS-PROC-001
- PR #23: Knowledge Vault Seed (AOS-KNOW-001)
- PR #24: Post-merge state reconciliation for AOS-KNOW-001
- PR #25: Architecture Spine Graph API (AOS-ARCH-001)
- PR #26: Post-merge state reconciliation for AOS-ARCH-001
- PR #27: Engineering Control Tower first dashboard surface (AOS-CTRL-001)
- PR #28: Post-merge state reconciliation for AOS-CTRL-001
- PR #29: Repository scan persistence and history (AOS-RUNTIME-003)
- PR #30: Plane board sync discipline (AOS-PLANE-001)
- PR #31: Executable-bit fix for shell scripts (AOS-LOCAL-001 finding 1)
- PR #32: AOS-LOCAL-001 Level 4 verification handoff and remediations — Sprint 2 complete
- PR #33: PR Guardian reads repository scanner output (AOS-PRG-002)
- PR #34: Decision and Research artifacts (AOS-DEC-001)
- PR #35: /guardian Claude Code command
- PR #36: Nightly learning digest, manual run (AOS-LEARN-001)
- PR #37: Phase 10 Alpha Review — ArchetypeOS evaluates ArchetypeOS (AOS-ALPHA-001) — **v0.1 complete**
- PR #38: Post-merge reconciliation — Sprint 3 / v0.1 closed
- PR #39: /health graceful degradation (AOS-RUNTIME-004) — Alpha finding #1 closed
- PR #40: Learning Feedback Loop Phase 1, RFC-0004 (AOS-LEARN-002)

## Current Objective

AOS-ORCH-004 (Sprint 4 close-out + Orchestrator Handoff Pack) in review on this branch — the operating loop made durable for the Fable 5 → Opus 4.8 orchestrator switch: `docs/ORCHESTRATOR_PLAYBOOK.md`, committed `scripts/web_drive/` harness, Board ID Registry backfill. Folds in the PR #41 reconciliation.

## Active Branch

- `claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` for post-merge state reconciliation)

## CI Status

- CI exists
- PR Guardian exists
- Verification Protocol is active
- PR Monitoring skill exists
- Branch Isolation / Worktree Protocol is active
- WSL Windows 11 is the accepted first runtime target

## Verification Status

- Status: Verification pending
- Level: Level 2
- Method: docs/scripts-only handoff pack — suite unchanged-green (65/65, ruff/compileall exit 0); Board ID Registry entries verified against Plane at write time; GitHub CI pending after PR creation
- Evidence: `docs/ORCHESTRATOR_PLAYBOOK.md`; `scripts/web_drive/README.md`; LES-008
- Limitations: drive harness not CI-wired (web-tests package, hard deadline 2026-08-01 acceptance expiry)
- Required Next Verifier: GitHub CI / PR Guardian, then Orchestrator review

## In Scope Now

- Orchestrator handoff pack (AOS-ORCH-004)

## Out Of Scope Now

- Plane two-way sync automation (AOS-9, not started)
- desktop automation
- browser automation
- wake word
- autonomous coding without approval gates
- production deployment

## Open Decisions

| Decision | Status | Notes |
| --- | --- | --- |
| Plane integration depth | Board adopted with documented sync discipline | See `docs/PLANE_PROJECT_BLUEPRINT.md`; automation deferred. |
| Agent dashboard implementation | First surface shipped | AOS-CTRL-001 merged (PR #27); richer views come after scan history (AOS-4). |
| Multi-agent live communication | Deferred | Durable artifact communication first. |
| Verification Engine implementation | Deferred | Protocol and provider abstraction first; automated provider selection later. |
| Local Level 2 verification | Done | AOS-LOCAL-001 executed on `teevee-1` 2026-07-05; runtime Verified at Level 4 on the declared target. |

## Blockers

- None. Plane is back online and synced; workstation `teevee-1` confirmed available via Tailscale.

## Next Recommended Task

Merge the AOS-ORCH-004 handoff-pack PR, then switch orchestrator models (Opus 4.8, per the transition section in `docs/HANDOFF.md`). Sprint 5 candidates, evidence-ranked: web tests (before the 2026-08-01 acceptance expiry), LES-007 doc-staleness detection, architecture-graph semantics, digest breadth, KnowledgePage API.

## Required Reading For New Sessions

1. `docs/CURRENT_STATE.md`
2. `docs/ACTIVE_WORK.md`
3. `docs/HANDOFF.md`
4. `docs/RECENT_CHANGES.md`
5. `docs/CAPABILITY_MAP.md`
6. `docs/V0_1_SCOPE_LOCK.md`
7. `docs/CONCRETE_BUILD_PATH.md`
8. `docs/VERIFICATION_PROTOCOL.md`
9. `docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md`
10. `docs/ENGINEERING_OS_STRATEGY.md`
11. `docs/WSL_WIN11_RUNTIME_TARGET.md`
12. Relevant RFCs and domain docs

## Update Rule

Update this file after every meaningful PR merge, scope change, blocker, or sprint transition.