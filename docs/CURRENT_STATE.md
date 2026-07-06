# Current State

## Purpose

This file is the durable project state checkpoint for ArchetypeOS.

Every new engineering session should read this before planning or implementation.

## Status

- Project: ArchetypeOS
- Phase: v0.1 COMPLETE (2026-07-05); post-v0.1 development underway
- Current sprint: Sprint 5 delivered (PRs #43–#48; AOS-18 Done). Intelligence Phase 1 (AOS-COUNCIL-001, PR #49, AOS-19 Done). Hardening: AOS-APIROUTES-001 (PR #50, AOS-24 Done). Substrate sequence (operator "2 then 1"): AOS-KNOW-002 merged (PR #51, AOS-23 backend); AOS-KNOW-003 in review (AOS-23 dashboard — closes it); then AOS-21. Orchestration Opus 4.8.
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
- PR #49: Agent Council seed — LLM provider abstraction + Council MVP + Final Judge, RFC-0005 Phase 1 (AOS-COUNCIL-001) — **the Intelligence Layer + Agent Council + Final Judge is live (backend); AOS-19 Done**
- PR #50: Split API routes by domain, control-plane hardening (AOS-APIROUTES-001) — `main.py` 487→49; 10 `routes/*.py` modules; behavior-preserving; AOS-24 Done
- PR #51: Knowledge read path — vault→DB sync + KnowledgePage read API + digest open-lessons rule (AOS-KNOW-002; RFC-0002/RFC-0004; Plane AOS-23 backend phase). Knowledge is operational; repo stays source of truth. (First CI run flagged a ruff F401 in migration `0004` — fixed, LES-012 recorded, tests made count-agnostic.)
- (in review) AOS-KNOW-003: Knowledge dashboard — global Control Tower Knowledge view + `./knowledge:ro` compose mount (Plane AOS-23 dashboard phase; **closes AOS-23**)

## Current Objective

**Operator sequence "2 then 1": finish the knowledge dashboard, then the second repo.** In review: **AOS-KNOW-003** (Plane AOS-23 dashboard phase — **merging closes AOS-23**) — a global "Knowledge" Control Tower view (Sync from vault, lesson list with open-lesson badges, All/Open filter) + a `./knowledge:ro` compose mount so `POST /knowledge/sync` works in the shipped stack. Frontend + compose only. Orchestrator-verified: full Playwright suite 5/5 headless incl. the new knowledge spec, strict build clean, compose valid. Next: **AOS-21** (second repo), then a definitive-roadmap reevaluation. Prior done: AOS-COUNCIL-001 (PR #49, AOS-19), AOS-APIROUTES-001 (PR #50, AOS-24), AOS-KNOW-002 (PR #51, AOS-23 backend).

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

- Status: Verification pending (AOS-KNOW-003 in review; PR #51 merged as `a462b3a`)
- Level: Level 4
- Method: Orchestrator independently ran the **full Playwright suite headless** → **5/5 pass** incl. the new `knowledge.spec.ts` (real `POST /knowledge/sync` vs the committed vault → LES-007 open badge, ≥12 rows, Open filter → exactly 1, reload persists); strict `tsc` + `vite build` exit 0; `docker compose config` valid with the vault mount + `KNOWLEDGE_ROOT=/knowledge` resolved into the api service. CI (web-e2e, compose-smoke boots api with the mount) pending on the PR
- Evidence: knowledge visible + syncable from the Control Tower; compose stack can populate KnowledgePage; repo remains authoritative
- Limitations: only lessons render (other vault domains empty); list view (no drill-down); read-only/advisory
- Required Next Verifier: GitHub CI / PR Guardian, then Orchestrator review; on merge AOS-23 → Done

## In Scope Now

- AOS-KNOW-003 (Plane AOS-23 dashboard phase): global Knowledge view + compose vault mount. Frontend + compose only; closes AOS-23.

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

Merge AOS-KNOW-003 after CI passes under the Manual Merge Gate — **closes AOS-23**. Then **AOS-21** (second repo — the highest-value proof: ArchetypeOS understanding something other than itself). Then the definitive-roadmap reevaluation the operator flagged. Remaining after: AOS-20 (LES-007 doc-staleness — now machine-surfaced by the digest), AOS-22 (backups), AOS-COUNCIL-002 (council dashboard).

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