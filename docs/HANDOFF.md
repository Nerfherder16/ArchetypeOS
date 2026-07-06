# Handoff

## Purpose

This file records the latest durable handoff for ArchetypeOS work.

Every engineering session should end by updating this file or creating a dated handoff artifact.

## Latest Handoff

### Date

2026-07-06

### Agent

Runtime Agent (Opus) under Orchestrator (Opus 4.8)

### Task

The Control Tower decision-approval view + worker-driven e2e (AOS-COUNCIL-PHASEC2B, Phase C Part 2b) — **completes Phase C**. (Prior: AOS-COUNCIL-PHASEC2A PR #56 / `973d532` — ADR export; AOS-COUNCIL-PHASEC PR #55 — the decision loop; AOS-COUNCIL-PHASEA PR #54 — first real Council run; AOS-COUNCIL-001 PR #49 / AOS-19.)

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `78709e3` after the PR #57 merge; env-pinned — see branch note above)

### PR

#57 — **Merged** as `78709e3` (merge commit). CI run 28788348725 all 6 jobs green on head `2406ecd` (incl. the worker-driven web-e2e).

### Status

Merged — **Phase C is COMPLETE end to end.** The Intelligence decision loop is drivable from the Control Tower: Council reasons (real Claude via `claude_code`) → drafts a governed `Decision` → a named human approves/rejects (with an `ApprovalRecord`; abstention blocks approval — LES-019) → an approved decision exports to an ADR in the source-of-truth vault (`knowledge/wiki/decisions/`) → surfaces on the Knowledge dashboard. The "Decision Loop" UI extends the existing Decisions section (enqueue review → draft → approve/reject → export, with 409s as readable inline errors). A **full worker-driven Playwright e2e** proves both branches deterministically (`serve-api.sh` runs `python -m app.worker` against a throwaway vault copy; `database.py` sqlite WAL/busy_timeout for file DBs). No backend/API/schema change. Built by an Opus builder subagent, Orchestrator-verified independently. Branch restarted from `main` at `78709e3`. **Next: operator's direction — Phase B (architecture semantics / language weighting), the Council dashboard (AOS-COUNCIL-002), or scanner precision (LES-016/017). Recommendation: Phase B.**

### Note — GitHub connector expired mid-session

The GitHub MCP OAuth token expired during PR #53 (long session). git push/CI were unaffected (separate proxy auth); only PR comments/reads were blocked. Operator re-authorized; the gate was posted late. If it recurs: reconnect GitHub via `/mcp` or claude.ai connector settings — git operations keep working regardless.

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- **Branch name is env-pinned, not stale-by-neglect:** `claude/aos-runtime-002-scanner-1egyjw` is fixed by the session config; each package restarts it from `main` (one PR = one package, clean history). A per-package scheme (`opus/aos-<pkg>`) is adopted only if the operator reconfigures the env / grants explicit permission. See the Role-contract note in `docs/ORCHESTRATOR_PLAYBOOK.md` (Lead-Architect critique 2026-07-05, operator Decision 2a).
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- **The Control Tower decision-approval view (Phase C Part 2b — completes Phase C).** `apps/web/src/api.ts`: `CouncilReview` type; `status`/`approved_by`/`approved_at` on `Decision`; `fetchCouncilReviews`/`enqueueCouncilReview`/`draftDecisionFromReview`/`approveDecision`/`rejectDecision`/`exportDecisionAdr`; `request<T>` now surfaces the FastAPI `detail` (for inline 409s).
- `apps/web/src/main.tsx`: a **Decision Loop** block in the Decisions section — enqueue council review + reviews list (verdict/confidence + Draft-decision) + Refresh; per-decision status badge + approver input + Approve/Reject + Export-ADR on approved; inline per-action errors; per-section error isolation.
- `apps/web/e2e/serve-api.sh`: runs `python -m app.worker` alongside uvicorn (own PYTHONPATH so `app.worker` resolves ahead of `app.main`) draining the queue; `KNOWLEDGE_ROOT` → a throwaway **copy** of the vault (ADR writes never touch the committed tree).
- `packages/aos_core/aos_core/database.py`: sqlite **WAL + busy_timeout** via a `connect` listener, guarded to **file-based sqlite only** (`_is_file_sqlite`) so API+worker share one file. `apps/api/tests/test_database_pragma.py` pins the guard (added after a `missing-core-tests` guardian BLOCK — LES-020).
- `apps/web/e2e/decision-loop.spec.ts` (new): happy path (scan → cleared-floor review conf 0.4 → draft → approve → export ADR) + blocked path (no scan → abstain → `needs_evidence` → approve 409, decision unchanged). `scheduling.spec.ts` made worker-tolerant (assert `project_digest — (queued|running|completed)`; Orchestrator dropped `failed`).
- Lesson `LES-020.md` (closed) + index row. Spec `.archetype/work/AOS-COUNCIL-PHASEC2B.md`. State files.

### Files changed

- `apps/web/src/api.ts`, `apps/web/src/main.tsx`
- `apps/web/e2e/serve-api.sh`, `apps/web/e2e/decision-loop.spec.ts` (new), `apps/web/e2e/scheduling.spec.ts`
- `packages/aos_core/aos_core/database.py`, `apps/api/tests/test_database_pragma.py` (new)
- `knowledge/wiki/lessons/LES-020.md` (new), `knowledge/wiki/lessons/index.md`, `.archetype/work/AOS-COUNCIL-PHASEC2B.md`
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- **Full Playwright suite 7/7 headless** (`PW_LOCAL_CHROMIUM`) incl. both `decision-loop.spec.ts` tests + the tightened `scheduling.spec.ts`; ran twice (once after the vault gained LES-020) — stable. Worker logs confirm it drains the queue (`job completed: …`).
- `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests -q` → **126 passed** (+3 pragma); `apps/worker/tests` → **7 passed**; strict `tsc` + `vite build` exit 0; `ruff` full CI scope + `compileall` clean.
- Independently confirmed (builder ≠ verifier): the approve path and the abstention-409 path both assert real state; `_is_file_sqlite` excludes `:memory:`/Postgres; `build_digest` succeeds on a repo-less project (basis for tightening the scheduling assertion); vault stays clean; no `apps/api`/schema/migration change.

### Known Risks

- The e2e now runs a worker in-harness (sqlite WAL/busy_timeout) — a legitimate harness evolution; the deterministic provider drives reproducible reviews. If web-e2e ever flakes, check worker startup / redis 9999 / the WAL PRAGMA first.
- ADR export remains local-first (compose `:ro` → 409, by design — 2a).

### Blockers

- None.

### Verification Status

Verified (PR #57 merged as `78709e3`; AOS-COUNCIL-PHASEC2B Done; **Phase C complete**)

### Verification Level

Level 4

### Verification Method

CI run 28788348725 all 6 jobs green on head `2406ecd` (incl. the worker-driven **web-e2e** — first CI run of the worker-in-harness); built by an Opus builder subagent, then Orchestrator-verified independently (builder ≠ verifier): **full Playwright 7/7 headless**; `pytest apps/api/tests` → **126 passed**; `apps/worker/tests` → **7 passed**; strict `tsc` + `vite build` exit 0; `ruff` full CI scope + `compileall` clean; `git status` confirmed no `apps/api`/schema/migration change and a clean vault; guardian PASS (after a `missing-core-tests` BLOCK fixed with a real test — LES-020). Branch restarted from `main` at `78709e3`.

### Evidence

- The decision loop is drivable end to end from the UI; deterministic e2e proves the approve path (scan → review → draft → approve → export ADR) and the abstention-409 path; api 126 / worker 7; full Playwright 7/7 headless; no backend/API/schema change.

### Limitations

Uses the existing project-scoped Decisions section (a standalone cross-project Council dashboard is AOS-COUNCIL-002, separate). ADR export remains local-first (compose `:ro` → 409, by design). The e2e runs a worker in-harness with sqlite WAL — a deliberate, deterministic harness evolution.

### Required Next Verifier

None — PR #57 merged as `78709e3` and reconciled. Phase C complete.

### Next Recommended Step

**Operator's direction — Phase C is complete.** Recommended: **Phase B — architecture semantics** (dependency/compose-derived architecture edges, LES-014, with `example-voting-app`'s compose file as a ready test; + language weighting, LES-013), because richer scan evidence directly improves the Council's inputs (the loop it now feeds). Alternatives: the standalone **Council dashboard** (AOS-COUNCIL-002); **scanner precision** (LES-016 manifest/ecosystem coverage, LES-017 secret-signal precision); AOS-20 (doc-staleness), AOS-22 (backups).

## Handoff Template

```text
Date:
Agent:
Task:
Branch:
PR:
Status:
Completed:
Files changed:
Tests run:
Docs updated:
Worktree or connector fallback used:
Base ref:
Head SHA:
Backup head, if any:
Freshness check:
Verification Status:
Verification Level:
Verification Method:
Evidence:
Limitations:
Required Next Verifier:
Risks:
Blockers:
Next recommended step:
Required reader context:
```

## Rule

A task is not complete until the handoff is durable and verification metadata is recorded.