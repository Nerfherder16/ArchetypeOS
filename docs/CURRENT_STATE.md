# Current State

## Purpose

This file is the durable project state checkpoint for ArchetypeOS.

Every new engineering session should read this before planning or implementation.

## Status

- Project: ArchetypeOS
- Phase: v0.1 COMPLETE (2026-07-05); post-v0.1 development underway
- Current sprint: Sprint 5 delivered (PRs #43–#48; AOS-18 Done). Intelligence Phase 1 (AOS-COUNCIL-001, PR #49, AOS-19). Hardening: AOS-APIROUTES-001 (PR #50, AOS-24). Knowledge read path complete (PRs #51/#52, AOS-23 Done). AOS-PORTFOLIO-001 merged (PR #53 — 5-repo reality test, AOS-21 Done). AOS-COUNCIL-PHASEA merged (PR #54 — first real Agent Council run). AOS-COUNCIL-PHASEC merged (PR #55 — the decision loop). AOS-COUNCIL-PHASEC2A merged (PR #56 — Decision → Knowledge ADR export). **AOS-COUNCIL-PHASEC2B merged (PR #57 — the decision-approval UI + worker-driven e2e) — Phase C COMPLETE end to end.** Next: operator's direction (Phase B / Council dashboard / scanner precision). Orchestration Opus 4.8.
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
- PR #55: The decision loop (AOS-COUNCIL-PHASEC, RFC-0005 Phase 2) — `CouncilReview` → governed draft `Decision` (idempotent, evidence-linked) → named-human approve/reject with an `ApprovalRecord` audit trail; **abstention blocks approval** (a `needs_evidence` draft → 409, LES-019 operationalized); pending drafts surface in the digest. No new tables/migration (reuses `Decision`+`ApprovalRecord`); backend only. **The Council → Decision → memory arc of `DECISION_LIFECYCLE.md` is live.**
- PR #56: Decision → Knowledge — repo-vault ADR export (AOS-COUNCIL-PHASEC2A, Phase C Part 2a) — an approved `Decision` renders into an ADR under `knowledge/wiki/decisions/` (source of truth) + a re-syncable `KnowledgePage` (`page_type="decision"`); local-first write (compose `:ro` → graceful 409, export decoupled from approval); `sync_knowledge` re-derives decision pages so a DB reset loses nothing; approved-only + idempotent. No new tables/migration; backend only. **Decisions now land in the vault and on the Knowledge dashboard.**
- PR #57: The Control Tower decision-approval view + worker-driven e2e (AOS-COUNCIL-PHASEC2B, Phase C Part 2b) — the Decision Loop UI (enqueue review → draft → approve/reject with a named approver → export ADR; 409s as readable inline errors). Full worker-driven Playwright e2e (`serve-api.sh` runs the worker against a throwaway vault copy; `database.py` sqlite WAL/busy_timeout for file DBs) drives both the approve and the 409 branches deterministically. Guardian BLOCK on `missing-core-tests` fixed with a real test (LES-020, closed). No backend/API/schema change. **Phase C is COMPLETE end to end.**

## Current Objective

**Phase C is COMPLETE — awaiting operator direction on the next build.** With AOS-COUNCIL-PHASEC2B (PR #57) merged, the Intelligence decision loop runs end to end and is drivable from the Control Tower: **Council reasons (real Claude via `claude_code`, honest abstention) → drafts a governed Decision → a named human approves/rejects (with an `ApprovalRecord`; abstention blocks approval, LES-019) → an approved decision exports to an ADR in the source-of-truth vault → surfaces on the Knowledge dashboard.** The four-PR arc: #54 (Council reasons/abstains) → #55 (draft → approve/reject) → #56 (ADR-in-vault) → #57 (UI + worker-driven e2e). Open options for the next build: **Phase B** — architecture semantics (LES-014 dependency/compose edges; `example-voting-app` is a ready test) + language weighting (LES-013); the standalone **Council dashboard** (AOS-COUNCIL-002); scanner precision (LES-016 manifest/ecosystem coverage, LES-017 secret-signal precision); or AOS-20 (doc-staleness), AOS-22 (backups).

## Active Branch

- `claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `78709e3` after the PR #57 merge)

## CI Status

- CI exists
- PR Guardian exists
- Verification Protocol is active
- PR Monitoring skill exists
- Branch Isolation / Worktree Protocol is active
- WSL Windows 11 is the accepted first runtime target

## Verification Status

- Status: Verified (PR #57 merged as `78709e3`; AOS-COUNCIL-PHASEC2B done; **Phase C complete**)
- Level: Level 4
- Method: CI run 28788348725 all 6 jobs green on head `2406ecd` (incl. the worker-driven **web-e2e** job — the first CI run of the worker-in-harness); built by an Opus builder subagent, then Orchestrator-verified independently (builder ≠ verifier) — **full Playwright 7/7 headless** (worker drains the queue; approve path + 409-blocked path both assert real state), strict `tsc` + `vite build` exit 0, api **126** / worker **7**, ruff full CI scope + compileall clean, vault stays clean, no backend/API/schema change; guardian PASS (after a `missing-core-tests` BLOCK was fixed with a real test — LES-020)
- Evidence: the decision loop is drivable end to end from the UI; deterministic e2e proves both the approve and the abstention-409 branches; sqlite WAL guard excludes `:memory:`/Postgres
- Limitations: uses the existing project-scoped Decisions section (a standalone Council dashboard is AOS-COUNCIL-002); ADR export remains local-first (compose `:ro` → 409)
- Required Next Verifier: None — Phase C complete and reconciled

## In Scope Now

- **RFC-0008 (PR open, docs/planning)** — captures the **Knowledge Distillation Engine** (repository content extraction) from the operator's founding intent, motivated by the `free-llm-api-resources` ingestion reality test (fingerprint → abstain; the scanner never reads content). Settles the **tools-upstream-not-in-judges** decision (LES-021 is the evidence). Records **LES-021** (provider context contamination — a tactical prerequisite). **Phase B remains the next build** per operator direction ("write the rfc first and continue with the roadmap"). No code — RFC + lesson + captured evidence.

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

**Operator's direction — Phase C is complete.** Highest-value options: (1) **Phase B — architecture semantics**: dependency/compose-derived architecture edges (LES-014; `example-voting-app`'s compose file is a ready test) + language weighting (LES-013) — makes the *scan* evidence the Council reasons over materially richer; (2) the standalone **Council dashboard** (AOS-COUNCIL-002) — a dedicated Control Tower view for reviews across projects; (3) **scanner precision** — LES-016 (broaden manifest/ecosystem coverage: .NET/JVM/Cargo) and LES-017 (test-fixture-path awareness for the secret heuristic). Other open: AOS-20 (doc-staleness/LES-007), AOS-22 (backups). Recommendation: **Phase B**, since richer scan evidence directly improves the Council's inputs (the loop it now feeds).

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