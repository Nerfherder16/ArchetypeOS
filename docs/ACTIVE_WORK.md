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

### AOS-DISTILL-001 — RFC-0008 MVP: repository content extraction (distillation)

- Status: In Progress (PR open)
- Owner: Chief Architect / Orchestrator (built by Opus builder subagent; Orchestrator-verified)
- PR: (open on `claude/aos-runtime-002-scanner-1egyjw`)
- Summary: The RFC-0008 MVP (pipe + deterministic README floor). `distill_repository` reads a repo's README → provenance-tagged `wiki/repositories/<slug>.md` + re-syncable `KnowledgePage` (`page_type="repository"`) + `DNA.purpose`; council selector surfaces it; `POST /repositories/{id}/distill`. No migration/frontend. Operator flagged README-only under-captures usefulness → **code-aware distillation (Phase 2, isolated `claude_code` over bounded source) is next**, building on this.
- Verification Status: Orchestrator-verified independently (real free-llm distill → named catalog page + DNA.purpose; idempotent; sync re-derives; api 143, worker 7, ruff full CI scope + compileall clean; no migration/frontend/stray-vault)
- Required Next Verifier: GitHub CI / PR Guardian, then Manual Merge Gate.

### AOS-LLM-ISOLATION-001 — Isolate the ClaudeCodeProvider from ambient project context (LES-021)

- Status: Merged
- Owner: Chief Architect / Orchestrator (implemented + verified directly — small tactical fix)
- PR: #60 (merged as `90395fa`)
- Summary: Closes LES-021. `ClaudeCodeProvider.generate` runs `claude -p` in a fresh empty temp cwd; `_build_argv` adds `--disallowedTools` + `--strict-mcp-config` — output is a pure function of system+prompt. Live-validated (free-llm fitness judge no longer describes ArchetypeOS) + hermetic regression test. Prerequisite for RFC-0008.
- Verification Status: Orchestrator-verified (live contamination-free re-run + hermetic argv/cwd test; api 132, worker 7, ruff full CI scope + compileall clean; no deps/migration/frontend)
- Required Next Verifier: GitHub CI / PR Guardian, then Manual Merge Gate.

### AOS-ARCH-SEMANTICS-001 — Phase B: architecture semantics (compose edges) + language weighting

- Status: Merged
- Owner: Chief Architect / Orchestrator (built by Opus builder subagent; Orchestrator-verified)
- PR: #59 (merged as `8296cfc`)
- Summary: The roadmap item — enrich the scanner's structural evidence. LES-014 (compose half, closed): parse compose files → `service` nodes + `depends_on` edges (list + map forms) + `RepositoryDNA.runtime_services`; manifest/import edges remain (LES-014 stays open). LES-013 (closed): source-classified `primary_language` so config/docs-heavy repos aren't misread. Generalized `scan.py` edge persistence (was repo-rooted + directory-only dedup). PyYAML dep + compose fixture. No migration/frontend.
- Verification Status: Verified (Orchestrator independent — compose fixture edges {web→db, web→redis, worker→db}, primary_language=Python, rescan idempotent, malformed-compose tolerant; api 132, worker 7, ruff full CI scope + compileall clean; guardian PASS_WITH_WARNINGS, acknowledged)
- Required Next Verifier: None — merged and reconciled.

### AOS-COUNCIL-PHASEC2B — The Control Tower decision-approval view (frontend + worker-driven e2e)

- Status: Merged
- Owner: Chief Architect / Orchestrator (built by Opus builder subagent; Orchestrator-verified)
- PR: #57 (merged as `78709e3`) — **Phase C COMPLETE end to end**
- Summary: Phase C Part 2b — Control Tower "Decision Loop" UI: enqueue council review → draft → approve/reject (named approver) → export ADR, with inline 409s (abstention-blocks-approval; read-only vault). `api.ts` council/decision functions + `Decision` status fields. Full worker-driven e2e: `serve-api.sh` runs the worker (throwaway vault copy), `database.py` sqlite WAL/busy_timeout (file-only), `decision-loop.spec.ts` drives both the approve and 409 branches deterministically. Guardian BLOCK (`missing-core-tests`) fixed with a real test — LES-020. No backend/API/schema change.
- Verification Status: Verified (CI run 28788348725 6/6 green on `2406ecd`, incl. worker-driven web-e2e; Orchestrator independent — full Playwright 7/7 headless, tsc + vite build exit 0, api 126, worker 7, ruff full CI scope + compileall clean; vault clean; no route/schema/migration change)
- Required Next Verifier: None — merged and reconciled.

### AOS-COUNCIL-PHASEC2A — Decision → Knowledge: repo-vault ADR export

- Status: Merged
- Owner: Chief Architect / Orchestrator (built by Opus builder subagent; Orchestrator-verified)
- PR: #56 (merged as `973d532`)
- Summary: Phase C Part 2a — an approved `Decision` renders into an ADR under `knowledge/wiki/decisions/` (source of truth) + a re-syncable `KnowledgePage`. Local-first write (compose `:ro` → graceful 409); export decoupled from approval; `sync_knowledge` re-derives decision pages so a DB reset loses nothing. Approved-only + idempotent. New `services/adr.py` + `test_adr_export.py`; `POST /decisions/{id}/adr`; route freeze 45→46. No new tables/migration; backend only (the approval UI is Part 2b).
- Verification Status: Verified (CI run 28766562398 6/6 green on `a2ce32f`; Orchestrator independent — api 123, worker 7, ruff full CI scope + compileall clean; read-only→409 + idempotency asserted; no migration; no web change; no stray vault ADR)
- Required Next Verifier: None — merged and reconciled.

### AOS-COUNCIL-PHASEC — The decision loop (Council review → draft → human approve/reject → memory)

- Status: Merged
- Owner: Chief Architect / Orchestrator (built by Opus builder subagent; Orchestrator-verified)
- PR: #55 (merged as `1306138`)
- Summary: RFC-0005 Phase 2 — the Decision stage of `DECISION_LIFECYCLE.md`, motivated by LES-019. `CouncilReview` → governed draft `Decision` (idempotent, links back as evidence) → named-human approve/reject with an `ApprovalRecord` audit trail. **Abstention blocks approval** (a `needs_evidence` draft → 409 naming the re-draft path). Pending drafts surface in the digest. No new tables/migration; backend only (approval UI + repo-vault ADR rendering = Phase C Part 2). New `services/decisions.py` + `test_decisions_loop.py`; 3 endpoints; digest rule 6.
- Verification Status: Verified (Orchestrator independent — api 116, worker 7, ruff full CI scope + compileall clean; 409 + ApprovalRecord asserted; no migration; no web change; guardian PASS)
- Required Next Verifier: None — merged and reconciled.

### AOS-COUNCIL-PHASEA — First real Agent Council run (pydantic-ai) + provider parse hardening

- Status: Merged
- Owner: Chief Architect / Orchestrator
- PR: #54 (merged as `894e418`)
- Summary: Reality test for Intelligence Phase 1 — ran the RFC-0005 Council over `pydantic/pydantic-ai` with the live `claude_code` provider (4 agents, 132 s). Constitution-faithful **abstention** (`Insufficient evidence`, conf 0.0375). Surfaced + fixed LES-018 (fenced-JSON parse defect — `_loads_tolerant`) and recorded LES-019 (evidence-class mismatch → Phase C input). Shipped captured review, evaluation doc, both lessons, parser fix + 4 tests.
- Verification Status: Verified (CI run 28764871261 6/6 green on `225f8b4`; Orchestrator independent live run + api 106 / worker 7 / ruff full scope + compileall clean)
- Required Next Verifier: None — merged and reconciled.

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

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #45
- Plane: AOS-18 (In Progress — 3-phase tracker; Phase 1 done)
- Spec: `.archetype/work/AOS-CORE-001.md`; RFC: `docs/rfc/RFC-0006-Shared-Core-Domain-Library.md` (Accepted)
- Verification Status: Verified
- Notes: Level 4 — CI run 28753264841 all 6 jobs green (compose-smoke built the api image from the new repo-root context; api-tests + web-e2e installed aos_core; pr-guardian ran without it) plus Orchestrator's 3.12-venv run (69 tests, 67 unchanged; no-drift 0 ops). Merge commit `5d00a18`. Zero behavior change.
- Required Next Verifier: None.

### AOS-WORKERRUN-001 — Worker Runs Scan/Digest Jobs (RFC-0006 Phase 2)

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #46
- Plane: AOS-18 (In Progress — 3-phase tracker; Phase 2 done)
- Spec: `.archetype/work/AOS-WORKERRUN-001.md`
- Verification Status: Verified
- Notes: Level 4 — CI run 28753706406 all 6 jobs green (compose-smoke built the worker image from the new context) + Orchestrator 3.12-venv run (5 worker tests incl. the e2e scan-job persistence proof; api 69 unchanged). Merge commit `3fe8afb`. Scans/digests now run as queued jobs.
- Required Next Verifier: None.

### AOS-SCHED-001 — Scheduler Seed: Schedules-as-Data + Control-Plane Scheduler (RFC-0007 / RFC-0006 Phase 3a)

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #47
- Plane: AOS-18 (In Progress — 3-phase tracker; Phase 3a done)
- Spec: `.archetype/work/AOS-SCHED-001.md`; RFC: `docs/rfc/RFC-0007-Scheduling-Control-Plane-Job-Origination.md` (Accepted)
- Verification Status: Verified
- Notes: Level 4 — CI (all 6 jobs green incl. compose-smoke applying migration `0002` on Postgres + building/booting the scheduler container) + Orchestrator 3.12-venv run (no-drift 0 ops, 75 api tests). Merge commit `915aa34`. First real Alembic migration; control-plane scheduler live.
- Required Next Verifier: None.

### AOS-SCHED-002 — Scheduler Dashboard: Schedules UI + Enqueue + Job History (RFC-0007 / RFC-0006 Phase 3b)

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #48
- Plane: AOS-18 (Done — **Phase 3b closed it; worker pipeline complete**), Sprint 5 cycle
- Spec: `.archetype/work/AOS-SCHED-002.md`
- Verification Status: Verified
- Notes: Level 4 — CI run 28756145778 all 6 jobs green (compose-smoke built/booted api+worker+web+scheduler; web-e2e ran the new `scheduling.spec.ts` with the ensured `redis-server`; api-tests ran the jobs-list tests) plus Orchestrator's 3.12-venv run (Playwright 4/4 headless, 77 api, 6 worker, strict tsc/vite). Merge commit `350c8b0`. **Closes AOS-18 and the worker pipeline — RFC-0006 (shared core) + RFC-0007 (control-plane scheduling) realized end to end: schedules → scheduler → queued jobs → workers → dashboard.**
- Required Next Verifier: None.

## Sprint 5 Status

Sprint 5 — Enforcement & Foundations. Delivered packages 1–6: AOS-16 (web tests, PR #43), AOS-17 (Alembic baseline, PR #44), AOS-18 in three phases (AOS-CORE-001 PR #45, AOS-WORKERRUN-001 PR #46, AOS-SCHED-001 PR #47, AOS-SCHED-002 PR #48). The distributed-runtime substrate — shared core, worker job execution, control-plane scheduler + first real migration, operator dashboard — is complete. Remaining backlog (unscheduled): AOS-21 (second repo), AOS-20 (LES-007 doc-staleness), AOS-22 (backups), AOS-23 (knowledge read path).

## Intelligence Thrust (open)

Operator-directed 2026-07-05: "write RFC-0005 and start AOS-19." The Intelligence Layer + Agent Council + Final Judge begins here, atop the completed Sprint 5 substrate. Phase 1 (AOS-COUNCIL-001, PR #49) merged — AOS-19 Done. AOS-COUNCIL-002 — the Agent Council Dashboard (trigger a review; per-agent status/output/confidence; surface disagreement; Final Judge panel; Playwright e2e) — is deferred one package behind a control-plane hardening interlude (Lead-Architect critique, operator-directed): AOS-APIROUTES-001 first.

## Control-Plane Hardening (open)

Lead-Architect critique (operator-relayed 2026-07-05) flagged `main.py` growth, a stale env-pinned branch name (documented — Decision 2a), the need for a Control Tower information hierarchy before more panels, and the knowledge read path (AOS-23) gap. Operator-directed substrate sequence: "aos-23, then aos-21, then reevaluate the roadmap" (then "2 then 1" — dashboard before second repo). Delivered: AOS-APIROUTES-001 (PR #50, AOS-24 Done — API modularized); AOS-KNOW-002 (PR #51 — knowledge read path backend); AOS-KNOW-003 (PR #52 — knowledge dashboard, AOS-23 Done); **AOS-PORTFOLIO-001 (PR #53 — 5-repo portfolio reality test, AOS-21 Done).** **Next: the definitive-roadmap reevaluation** (operator-flagged) — depth-vs-breadth empirically settled toward depth. Backlog spawned by the reality test: LES-013 (language weighting), LES-014 (dependency/compose architecture edges), LES-016 (broaden manifest/ecosystem coverage), LES-017 (secret-signal precision). Also open: AOS-20 (doc-staleness, machine-surfaced by the digest), AOS-22 (backups), AOS-COUNCIL-002 (council dashboard), and running the Council over a real repo (depth).

### AOS-APIROUTES-001 — Split API routes by domain (control-plane hardening)

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #50
- Plane: AOS-24 (Done)
- Spec: `.archetype/work/AOS-APIROUTES-001.md`
- Verification Status: Verified
- Notes: Level 4 — CI run 28759105408 all 6 jobs green on head `65c3286` (incl. compose-smoke booting the api image from the split package) plus Orchestrator's independent 3.12-venv run: **route table byte-identical `origin/main` vs working tree (43 (method,path) pairs, empty diff)**, api 94 (92 unchanged + 2 inventory guards), FakeRedis jobs/schedules/council 11 in isolation (patch target preserved), ruff/compile clean, `main.py` 487→49. Merge commit `2c5cdcb`. Pure behavior-preserving refactor — API now modular (10 `routes/*.py`). Also documented the env-pinned branch constraint in HANDOFF + Playbook (Decision 2a).
- Required Next Verifier: None.

### AOS-KNOW-002 — Knowledge read path: vault→DB sync + KnowledgePage read API + digest open-lessons rule (RFC-0002/RFC-0004; Plane AOS-23 backend)

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #51
- Plane: AOS-23 (In Progress — backend phase done via this PR; the dashboard Knowledge view AOS-KNOW-003 / 23b remains, so AOS-23 stays open until it merges)
- Spec: `.archetype/work/AOS-KNOW-002.md`
- Verification Status: Verified
- Notes: Level 4 — CI run 28760266463 all 6 jobs green on head `88037c3` (compose-smoke applied migration `0004` on fresh Postgres) plus Orchestrator's independent 3.12-venv run at CI's exact ruff scope: api 99 / worker 7; `sync_knowledge` on the real vault → all lessons (12; LES-007 sole open), idempotent, global, missing-vault→zeros; digest surfaces the open lesson; alembic no-drift after `0004` (project_id nullable, 0 ops, 24 tables). Merge commit `a462b3a`. **First CI run failed on a ruff F401 in migration `0004` (local ruff had scoped to `apps/api/app`, narrower than CI's `apps/api`) — fixed, recorded LES-012, and made the knowledge tests count-agnostic.** Knowledge is operational (queryable + digest-visible); repo remains source of truth.
- Required Next Verifier: None.

### AOS-KNOW-003 — Knowledge dashboard: Control Tower Knowledge view + compose vault mount (closes AOS-23)

- Status: Merged
- Owner: Frontend/Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #52
- Plane: AOS-23 (**Done** — this dashboard phase closed it)
- Spec: `.archetype/work/AOS-KNOW-003.md`
- Verification Status: Verified
- Notes: Level 4 — CI run 28761004456 all 6 jobs green on head `6a8942e` (compose-smoke booted api with the `:/knowledge:ro` mount; web-e2e ran the knowledge spec) plus Orchestrator's independent full Playwright suite headless → **5/5** incl. `knowledge.spec.ts` (real sync vs the committed vault → LES-007 open badge, ≥12 rows, Open filter → 1, reload persists); strict tsc/vite build exit 0; `docker compose config` valid with the mount in the api service. Merge commit `c022c6b`. **AOS-23 is Done — the full knowledge read path (backend sync + API + digest visibility + dashboard) is complete, closing the AOS-KNOW-001 and RFC-0004 deferrals.**
- Required Next Verifier: None.

### AOS-PORTFOLIO-001 — Portfolio: onboard + scan a second real repo (pydantic-ai), evaluate every engine (Plane AOS-21)

- Status: Merged
- Owner: Runtime Agent (Opus, acquisition code) + Orchestrator (Opus 4.8, reality test + evaluation)
- PR: #53 (merge commit `b64db41`)
- Plane: AOS-21 (**Done**)
- Spec: `.archetype/work/AOS-PORTFOLIO-001.md`
- Goal: the first portfolio reality test — run the pipeline on **four** diverse real repos the system did not write (pydantic-ai, claude-agent-sdk-python, gin [Go], example-voting-app [polyglot compose]; operator-chosen) + a repeatable repo-acquisition capability (`clone_repo`, dogfooded on all four real network clones). Deliverables: `clone_repo` (`aos_core/services/onboarding.py`) + `scripts/onboard_repo.sh` + tests; captured scans (`.archetype/portfolio/*/scan.json`) + evaluation (`docs/PORTFOLIO_PYDANTIC_AI.md`); **four honest open lessons — LES-013 (file-count language mix, repo-dependent), LES-014 (architecture edges tree-only), LES-016 (new: `.csproj`/.NET manifest missed; ecosystem coverage stops at python/node/go), LES-017 (`SECRET_LIKE_FILENAME` on test-cert fixtures)**. Scanner is robust + broader than assumed (Go + compose handled well). Gaps are scoped follow-ups, not fixed here. LES-015 (self-caught e2e count-race) closed.
- Verification Status: Verified
- Verification Level: Level 4
- Verification Method: CI run 28763747860 all 6 jobs green on head `73f73ac` plus the Orchestrator's real full pipeline on **five** repos (pydantic-ai, claude-agent-sdk-python, gin, example-voting-app, kubernetes — clone via `clone_repo` → register → run_scan → DNA + architecture → digest, evidence at `.archetype/portfolio/*/scan.json`); `clone_repo` verified independently (real `file://` clone + idempotent + path-safety); api **102**; full Playwright **5/5 headless**; ruff full CI scope + compile clean. Merge commit `b64db41`.
- Evidence: **the scanner is robust and generalizes across language / deployment style / scale** — Go + multi-service compose handled well; at 30k files (kubernetes) it degrades gracefully (truncation surfaced via `SCAN_TRUNCATED`, DNA sane). Four honest gaps recorded as open lessons (LES-013 language weighting, LES-014 dependency/compose edges, LES-016 manifest coverage, LES-017 secret-signal precision) — all now surface in the digest + Knowledge dashboard.
- Required Next Verifier: None.

### AOS-COUNCIL-001 — Agent Council Seed: LLM Provider Abstraction + Council MVP + Final Judge (RFC-0005 Phase 1)

- Status: Merged
- Owner: Runtime Agent (Opus) under Orchestrator (Opus 4.8)
- PR: #49
- Plane: AOS-19 (Done — RFC-0005 Phase 1; the dashboard AOS-COUNCIL-002 is Phase 2)
- Spec: `.archetype/work/AOS-COUNCIL-001.md`; RFC: `docs/rfc/RFC-0005-Intelligence-Layer-Agent-Council-Final-Judge.md` (Accepted)
- Verification Status: Verified
- Notes: Level 4 — CI run 28757387442 all 6 jobs green on head `8dd2fb7` (compose-smoke applied migration `0003` on fresh Postgres + booted all services; api-tests ran the 15 new council tests; worker-tests ran the dispatch test) plus Orchestrator's independent 3.12-venv run (api 92 / worker 7; `run_council` branch checks — 4 outputs, disagreement surfaced, abstention on evidence-less project, 404, determinism, `get_provider` mapping; alembic no-drift after `0003` → 24 tables, 0 ops). Merge commit `a56d317`. **The Intelligence Layer + Agent Council + Final Judge is live (backend); advisory/draft-only.** A real council run is validated on an authed node via `llm_provider=claude_code`.
- Required Next Verifier: None.

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