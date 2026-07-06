# Current State

## Purpose

This file is the durable project state checkpoint for ArchetypeOS.

Every new engineering session should read this before planning or implementation.

## Status

- Project: ArchetypeOS
- Phase: v0.1 COMPLETE (2026-07-05); post-v0.1 development underway
- Current sprint: Sprint 5 delivered (PRs #43–#48; AOS-18 Done). Intelligence Phase 1 (AOS-COUNCIL-001, PR #49, AOS-19). AOS-PORTFOLIO-001 merged (PR #53 — 5-repo reality test, AOS-21 Done). Intelligence arc: AOS-COUNCIL-PHASEA (PR #54), PHASEC (PR #55), PHASEC2A (PR #56), PHASEC2B (PR #57) — **Phase C COMPLETE end to end**. RFC-0008 (content extraction) proposed (PR #58). AOS-ARCH-SEMANTICS-001 merged (PR #59 — Phase B: compose/service architecture edges + source-classified language weighting; LES-013 closed, LES-014 compose half done). **The founding "feed a repo → extract what's useful → Obsidian for reuse → surface what's useful *for* a target" arc is now mature end-to-end.** Merged: AOS-LLM-ISOLATION-001 (PR #60, LES-021 provider isolation), AOS-DISTILL-001 (PR #61, RFC-0008 MVP README distillation), AOS-DISTILL-002 (PR #62, Phase 2 code-aware distillation), AOS-TRANSFER-001 (PR #63, RFC-0009 Knowledge Transfer Engine MVP). Then the **first end-to-end reality test** (2026-07-06) showed the loop connects but distillation evidence quality was the bottleneck, driving the operator "design to the mature-state target" rule (`ORCHESTRATOR_PLAYBOOK.md`) and three layered packages: AOS-DISTILL-003 (PR #64 — deterministic floor + framework evidence), AOS-DISTILL-004 (PR #65 — reasoned `DNA.purpose`, live-validated), AOS-TRANSFER-002 (PR #66 — transfer need-coverage calibration). The full reality test now confirms the loop returns the correct repo #1 on every query with meaningful confidence. RFC-0009 embeddings underway: **RFC-0010 merged (#69); AOS-EMBED-001 (Part 1 — vector-store + retrieval infra, pgvector, NO torch) merged (#70, `6833440`)** — the semantic `recommend_reuse` path + pgvector storage + the Postgres-service CI job are live (the CI job passed on real Postgres). **Part 2 (AOS-EMBED-002 — the real sentence-transformers/torch embedder + Orchestrator live validation) queued, awaiting operator go** (it's the package that pulls in torch). Plane AOS-25. The Control Tower "Reuse" view remains a separate increment. Tandem: a laptop Orchestrator session works AOS-20 (doc-staleness) on its own branch; shared visibility via the Plane AOS board. Orchestration Opus 4.8.
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
- PR #58: RFC-0008 (Knowledge Distillation Engine — repository content extraction, Proposed) + LES-021 (provider context contamination, open) — captured from the `free-llm-api-resources` ingestion reality test (fingerprint → abstain; the scanner never reads content). Records the tools-upstream-not-in-judges decision + the n8n edge-boundary decision. Docs/planning only; queued, not built.
- PR #59: Phase B — architecture semantics (AOS-ARCH-SEMANTICS-001) — the scanner parses Docker Compose files into `service` nodes + `depends_on` edges (+ `RepositoryDNA.runtime_services`; LES-014 compose half closed) and derives a source-classified `primary_language` (LES-013 closed). Generalized `scan.py` edge persistence (was repo-rooted); PyYAML added to api+worker; no migration. **Richer structural evidence for the Council.**

## Current Objective

**Awaiting operator direction — Phase C complete, Phase B merged.** The Intelligence decision loop runs end to end (Council reasons → drafts → human approve/reject → ADR-in-vault → Knowledge dashboard; PRs #54–#57), and the scanner's structural evidence is now richer (compose/service edges + source-classified language; PR #59). RFC-0008 (content extraction) is a Proposed RFC (PR #58), queued behind its prerequisite LES-021 (provider isolation). Open options for the next build: **RFC-0008 content extraction** (+ its LES-021 prerequisite) — the operator's founding "extract what's useful → Obsidian" intent; **scanner precision** (LES-016 manifest/ecosystem coverage, LES-017 secret-signal precision); **LES-014 manifest/import architecture edges**; the standalone **Council dashboard** (AOS-COUNCIL-002); or AOS-20 (doc-staleness), AOS-22 (backups).

## Active Branch

- `claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `8296cfc` after the PR #59 merge)

## CI Status

- CI exists
- PR Guardian exists
- Verification Protocol is active
- PR Monitoring skill exists
- Branch Isolation / Worktree Protocol is active
- WSL Windows 11 is the accepted first runtime target

## Verification Status

- Status: Verified (PR #59 merged as `8296cfc`; AOS-ARCH-SEMANTICS-001 done — Phase B)
- Level: Level 3
- Method: built by an Opus builder subagent, then Orchestrator-verified independently (builder ≠ verifier) — scanned the compose fixture (`service` nodes `{db,redis,web,worker}`, `depends_on` edges `{web→db, web→redis, worker→db}`, `runtime_services` populated, `primary_language=Python`), confirmed **rescan idempotency** (nodes 5→5, edges 3→3 — validates the `scan.py` edge-persistence generalization) and malformed-compose tolerance; api **132** / worker **7**, ruff full CI scope + compileall clean, no migration/frontend; guardian PASS_WITH_WARNINGS (the `scanner-new-ecosystem` WARN is the test-fixture files tripping the self-scan — acknowledged)
- Evidence: compose files now yield real service/`depends_on` architecture; config/docs-heavy repos report a source-classified `primary_language` (LES-013); LES-014 compose half closed (manifest/import edges remain)
- Limitations: LES-014's manifest/dependency + import-graph edges are a follow-up; language weighting is source-vs-config classification, not lines-of-code; adds a PyYAML runtime dep (compose-smoke covers the build)
- Required Next Verifier: None — Phase B complete and reconciled

- Nothing active. **AOS-DISTILL-002 merged (PR #62) — RFC-0008 Phase 2 (code-aware distillation) is live.** Distillation now reads the actual **source** (bounded/tolerant): a deterministic `## Components (from source)` section (pure `ast`+regex, CI-tested) + an optional isolated-`claude_code` `## How it works / Built for` narrative (real provider only) — both provenance-tagged. Live-validated on real free-llm `src/data.py` (named `MODEL_TO_NAME_MAPPING`, zero contamination). Awaiting operator direction. Open options: **the Knowledge Transfer Engine** (RFC-0008's "useful *for* a target repo" — relevance/retrieval, embeddings — the deferred half of the founding vision); scanner precision (LES-016 manifest/ecosystem coverage, LES-017 secret-signal precision); LES-014 manifest/import architecture edges; a Repository-page UI in the Control Tower; AOS-COUNCIL-002 (Council dashboard); AOS-20 (doc-staleness), AOS-22 (backups).

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

**Operator's direction — Phase C complete, Phase B merged.** Highest-value options: (1) **RFC-0008 — repository content extraction** (the operator's founding "feed a repo → extract what's useful → Obsidian for reuse" intent) — its prerequisite is **LES-021** (isolate the `claude_code` provider from ambient project context, a small tactical fix); this is the biggest step toward the original vision and turns content-rich repos from fingerprint-abstentions into real distilled knowledge; (2) **scanner precision** — LES-016 (broaden manifest/ecosystem coverage: .NET/JVM/Cargo) + LES-017 (test-fixture-path awareness for the secret heuristic); (3) **LES-014 manifest/import architecture edges** (the non-compose half); (4) the standalone **Council dashboard** (AOS-COUNCIL-002); (5) AOS-20 (doc-staleness), AOS-22 (backups). Recommendation: **LES-021 then RFC-0008** — it's the operator-flagged founding capability, and Phase B just made its structural counterpart richer.

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