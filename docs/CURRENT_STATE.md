# Current State

## Purpose

This file is the durable project state checkpoint for ArchetypeOS.

Every new engineering session should read this before planning or implementation.

## Status

- Project: ArchetypeOS
- Phase: v0.1 COMPLETE (2026-07-05); post-v0.1 development underway
- Current sprint: Sprint 5 delivered (PRs #43–#48; AOS-18 Done). Intelligence thrust open — AOS-COUNCIL-001 (RFC-0005 Phase 1, Plane AOS-19) in review; orchestration Opus 4.8.
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
- PR #41: Guardian evolution — lessons become rules, RFC-0004 Phase 2 (AOS-PRG-003) — **Sprint 4 complete**
- PR #42: Sprint 4 close-out + Orchestrator Handoff Pack (AOS-ORCH-004) — orchestration → Opus 4.8
- PR #43: Playwright e2e suite, enforced (AOS-WEB-001) — web tests real + guardian-enforced; LES-006 deadline closed early
- PR #44: Adopt Alembic migrations, baseline (AOS-ALEMBIC-001) — migration path adopted, no schema change
- PR #45: Extract aos_core shared package, RFC-0006 Phase 1 (AOS-CORE-001) — domain layer is now a shared package
- PR #46: Worker runs scan/digest jobs, RFC-0006 Phase 2 (AOS-WORKERRUN-001) — scans/digests run as queued jobs
- PR #47: Scheduler seed — schedules-as-data + control-plane scheduler, RFC-0007 (AOS-SCHED-001); first real Alembic migration
- PR #48: Scheduler dashboard — schedules UI + enqueue + job history, RFC-0007/RFC-0006 Phase 3b (AOS-SCHED-002) — **closes AOS-18 and the worker pipeline; RFC-0006 + RFC-0007 realized end to end**

## Current Objective

**Intelligence thrust underway** (operator-directed): AOS-COUNCIL-001 (RFC-0005 Phase 1, Plane AOS-19) in review on this branch — the Agent Council seed. A `Provider` abstraction (`DeterministicProvider` CI default + `ClaudeCodeProvider` subscription backend), the four Phase-9 agents + a rule-based Final Judge (agreements/disagreements/unsupported-claims/verdict + abstention), `CouncilReview`/`CouncilAgentOutput` tables + migration `0003`, worker `council_review` dispatch, and council trigger/read API. Backend only; the Agent Council Dashboard is AOS-COUNCIL-002 (Phase 2). This is where the platform starts to reason, atop the Sprint 5 substrate (AOS-18 Done: shared core + worker + scheduler).

## Active Branch

- `claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `350c8b0` after the PR #48 merge)

## CI Status

- CI exists
- PR Guardian exists
- Verification Protocol is active
- PR Monitoring skill exists
- Branch Isolation / Worktree Protocol is active
- WSL Windows 11 is the accepted first runtime target

## Verification Status

- Status: Verification pending (AOS-COUNCIL-001 in review; PR #48 merged as `350c8b0`)
- Level: Level 4
- Method: Orchestrator independently (3.12 venv) ran ruff/compile clean; api **92 passed** (77 + 15 new), worker **7 passed** (6 + 1); exercised `run_council` directly (4 agent outputs, disagreement surfaced, abstention on evidence-less project, 404, deterministic provider, `get_provider` mapping); alembic no-drift after `0003` — 24 tables incl. both council tables, **0 drift ops**. CI (api-tests, worker-tests, compose-smoke on Postgres) pending on the PR
- Evidence: 4 structured agent outputs + Final Judge verdict per project; disagreement explicit; abstention enforced; council trigger/read API; `council_review` job dispatch; migration `0003` applies
- Limitations: `ClaudeCodeProvider` runs only on an authed node (mocked in CI); advisory/draft-only
- Required Next Verifier: GitHub CI / PR Guardian, then Orchestrator review

## In Scope Now

- AOS-COUNCIL-001 (RFC-0005 Phase 1, Plane AOS-19): Agent Council seed — provider abstraction + 4 agents + Final Judge + tables/migration `0003` + worker dispatch + council API. Backend only.

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

Merge AOS-COUNCIL-001 after CI passes under the Manual Merge Gate (Plane AOS-19 Phase 1). Then AOS-COUNCIL-002 — the Agent Council Dashboard (trigger a review, per-agent status/output/confidence, surface disagreement, Final Judge panel; Playwright e2e) — closes the Phase-9 "disagreements are visible" acceptance end to end. Lighter backlog: AOS-21 (second repo), AOS-20 (LES-007 doc-staleness), AOS-22 (backups), AOS-23 (knowledge read path).

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