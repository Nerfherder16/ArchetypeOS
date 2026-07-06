# Current State

## Purpose

This file is the durable project state checkpoint for ArchetypeOS.

Every new engineering session should read this before planning or implementation.

## Status

- Project: ArchetypeOS
- Phase: v0.1 COMPLETE (2026-07-05); post-v0.1 development underway
- Current sprint: Sprint 5 delivered (PRs #43–#48; AOS-18 Done). Intelligence Phase 1 (AOS-COUNCIL-001, PR #49, AOS-19). Hardening: AOS-APIROUTES-001 (PR #50, AOS-24). Knowledge read path complete (PRs #51/#52, AOS-23 Done). **AOS-PORTFOLIO-001 merged (PR #53 — 5-repo reality test, AOS-21 Done).** Next: definitive-roadmap reevaluation. Orchestration Opus 4.8.
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
- PR #52: Knowledge dashboard — global Control Tower Knowledge view + `./knowledge:ro` compose mount (AOS-KNOW-003) — **closes AOS-23; knowledge read path complete end to end**
- PR #53: Portfolio reality test on **five** real repos + repo-acquisition capability (AOS-PORTFOLIO-001, Plane AOS-21 Done) — scanner robust across language/deployment/scale; LES-013/014/016/017 gaps recorded

## Current Objective

**Definitive-roadmap reevaluation (operator-flagged) — this is the active work now that AOS-21 is Done.** AOS-PORTFOLIO-001 (PR #53) merged: a 5-repo portfolio reality test proved the scanner is **robust and generalizes across language / deployment style / scale** (Go + compose handled; graceful non-silent truncation at 30k files). The reality test spawned a concrete backlog of four scanner gaps (LES-013/014/016/017) and **empirically settled the depth-vs-breadth question toward depth** — further ingestion is diminishing returns; the highest-value moves are running the Agent Council over a real repo and closing LES-014 (dependency/compose architecture edges) + LES-013 (language weighting). Awaiting operator direction on the reevaluation. **Four honest gaps as open lessons:** LES-013 (file-count language mix, repo-dependent — 28% Python on pydantic-ai vs 77% on the SDK), LES-014 (architecture edges tree-only; `example-voting-app`'s compose file has the service graph it ignores), **LES-016 (new — `.csproj`/.NET manifest missed; ecosystem coverage stops at python/node/go)**, LES-017 (`SECRET_LIKE_FILENAME` flags test-cert fixtures). Ships a repeatable repo-acquisition capability (`clone_repo` + `onboard_repo.sh`), the captured scan + evaluation, and the lessons (which now surface in the digest + Knowledge dashboard — the loop consuming its own findings). Gaps are scoped follow-ups, not fixed here. Prior done this thrust: AOS-COUNCIL-001 (PR #49, AOS-19), AOS-APIROUTES-001 (PR #50, AOS-24), AOS-KNOW-002/003 (PRs #51/#52, AOS-23).

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

- Status: Verified (PR #53 merged as `b64db41`; AOS-21 Done)
- Level: Level 4
- Method: CI run 28763747860 all 6 jobs green on head `73f73ac` plus the Orchestrator's real full pipeline on **five** repos (pydantic-ai, claude-agent-sdk-python, gin, example-voting-app, kubernetes; evidence at `.archetype/portfolio/*/scan.json`); `clone_repo` verified independently; api **102**; full Playwright **5/5 headless**; ruff full CI scope + compile clean
- Evidence: scanner robust across language/deployment/scale; four gaps (LES-013/014/016/017) recorded + digest/dashboard-visible
- Limitations: gaps recorded not fixed (follow-ups); repo scans are captured evidence, not CI tests; acquisition is a script/function (no API endpoint yet)
- Required Next Verifier: None — AOS-21 complete and reconciled

## In Scope Now

- Nothing active. **Definitive-roadmap reevaluation** is the next deliverable (advisory) — then operator picks the next build package.

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

**Definitive-roadmap reevaluation** (advisory; operator-flagged) — depth-vs-breadth empirically settled toward **depth**. Highest-value next builds: (1) run the **Agent Council over a real repo** (biggest untapped signal; validates Intelligence Phase 1 on an authed node via `llm_provider=claude_code`); (2) **LES-014** architecture-semantics — dependency/compose-derived edges (`example-voting-app` is a ready test case); (3) **LES-013** language weighting. Scanner backlog also: LES-016 (broaden manifest/ecosystem coverage), LES-017 (secret-signal precision). Other open: AOS-20 (doc-staleness/LES-007 — digest-surfaced), AOS-22 (backups), AOS-COUNCIL-002 (council dashboard).

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