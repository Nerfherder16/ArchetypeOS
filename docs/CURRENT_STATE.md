# Current State

## Purpose

This file is the durable project state checkpoint for ArchetypeOS.

Every new engineering session should read this before planning or implementation.

## Status

- Project: ArchetypeOS
- Phase: v0.1 COMPLETE (2026-07-05); post-v0.1 development underway
- Current sprint: Sprint 5 delivered (PRs #43–#48; AOS-18 Done). Intelligence Phase 1 (AOS-COUNCIL-001, PR #49, AOS-19). Hardening: AOS-APIROUTES-001 (PR #50, AOS-24). Knowledge read path complete (PRs #51/#52, AOS-23 Done). AOS-PORTFOLIO-001 merged (PR #53 — 5-repo reality test, AOS-21 Done). **AOS-COUNCIL-PHASEA merged (PR #54 — first real Agent Council run over pydantic-ai; constitution-faithful abstention; LES-018 parse fix, LES-019 recorded).** Next: operator picks next build (recommended Phase C decision loop). Orchestration Opus 4.8.
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
- PR #54: First real Agent Council run over external code (AOS-COUNCIL-PHASEA) — RFC-0005 Council run over `pydantic/pydantic-ai` with the live `claude_code` provider (4 agents, real Claude reasoning) returned a **constitution-faithful abstention** (`Insufficient evidence`, conf 0.0375); hardened the provider parse seam (LES-018 — live-model Markdown-fenced JSON) and recorded LES-019 (evidence-class mismatch → Phase C input). **Intelligence Phase 1 validated on real external code.**

## Current Objective

**Operator picks the next build — recommended Phase C (the decision loop).** AOS-COUNCIL-PHASEA (PR #54) merged: the **first real Agent Council run over external code** validated Intelligence Phase 1 end to end. Run over `pydantic/pydantic-ai` with the live `claude_code` provider (4 agents, real Claude reasoning, 132 s), the Council returned a **constitution-faithful abstention** (`Insufficient evidence`, conf 0.0375) — refusing to manufacture an adoption verdict it could not support and naming the exact evidence it would need. The reality test surfaced two honest findings: **LES-018** (live-model JSON is Markdown-fenced; the tolerant parser now strips it — **fixed**, with tests validated against the captured raw run) and **LES-019** (a structural scan is the wrong evidence class for an *adoption* question — **recorded, open**). LES-019 is the direct motivation for **Phase C**: a decision loop that feeds the Council a research/decision corpus (Council → gather/record research → draft decision → human-approve → knowledge). Open scanner backlog persists as lessons: LES-013 (language weighting), LES-014 (dependency/compose architecture edges), LES-016 (manifest/ecosystem coverage), LES-017 (secret-signal precision). Other open: AOS-20 (doc-staleness), AOS-22 (backups), AOS-COUNCIL-002 (council dashboard).

## Active Branch

- `claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `894e418` after the PR #54 merge)

## CI Status

- CI exists
- PR Guardian exists
- Verification Protocol is active
- PR Monitoring skill exists
- Branch Isolation / Worktree Protocol is active
- WSL Windows 11 is the accepted first runtime target

## Verification Status

- Status: Verified (PR #54 merged as `894e418`; AOS-COUNCIL-PHASEA done)
- Level: Level 3
- Method: CI run 28764871261 all 6 jobs green on head `225f8b4`; plus the Orchestrator's independent live Council run over pydantic-ai (4 agents via `claude_code`, 132 s, captured to `.archetype/council/pydantic-ai-review.json`), the LES-018 fix validated against that captured raw output, api **106** (+4 parser tests), worker 7, ruff full CI scope + compileall clean
- Evidence: Council returned a constitution-faithful abstention (`Insufficient evidence`, conf 0.0375); parse fix recovers 0→6 / 0→4 findings from the 3 fenced agents while the aggregate still abstains
- Limitations: the live Council run is captured evidence, not a hermetic CI test (subscription-auth provider); LES-019 (evidence-class) recorded, not fixed
- Required Next Verifier: None — AOS-COUNCIL-PHASEA complete and reconciled

## In Scope Now

- **AOS-COUNCIL-PHASEC (PR open)** — **the decision loop** (RFC-0005 Phase 2; the Decision stage of `DECISION_LIFECYCLE.md`), the LES-019 follow-up. `CouncilReview` → governed draft `Decision` (idempotent, evidence-linked) → named-human approve/reject with an `ApprovalRecord` trail. **Abstention blocks approval** — a `needs_evidence` draft returns 409 naming the gather-evidence/re-draft path. Pending drafts surface in the digest. No new tables/migration (reuses `Decision`+`ApprovalRecord`); backend only. Orchestrator-verified: api 116 / worker 7 green, ruff full CI scope + compileall clean.

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

**Phase C — the decision loop (recommended).** The first real Council run (PR #54) proved Intelligence Phase 1 and, via LES-019, showed the highest-signal next move: feed the Council the *right evidence class*. Phase C is Council → gather/record research → **draft decision** → human-approve → knowledge, closing the exact gap the pydantic-ai run exposed (it abstained and named the evidence it needed). Alternatives: **Phase B** — architecture semantics (LES-014 dependency/compose edges; `example-voting-app` is a ready test) + language weighting (LES-013); the **Council dashboard** (AOS-COUNCIL-002). Scanner backlog also open: LES-016 (manifest/ecosystem coverage), LES-017 (secret-signal precision). Other open: AOS-20 (doc-staleness/LES-007), AOS-22 (backups). Operator's call.

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