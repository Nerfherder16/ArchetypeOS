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

The decision loop — Council review → draft decision → human approve/reject → durable memory (AOS-COUNCIL-PHASEC, RFC-0005 Phase 2). (Prior: AOS-COUNCIL-PHASEA merged PR #54 / `894e418` — first real Council run; AOS-PORTFOLIO-001 PR #53 / AOS-21; AOS-KNOW-003 PR #52 / AOS-23; AOS-APIROUTES-001 PR #50 / AOS-24; AOS-COUNCIL-001 PR #49 / AOS-19.)

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `1306138` after the PR #55 merge; env-pinned — see branch note above)

### PR

#55 — **Merged** as `1306138` (merge commit).

### Status

Merged — **the decision loop is live** (backend). The Council → Decision → memory arc of `DECISION_LIFECYCLE.md` runs end to end: a `CouncilReview` drafts a governed `Decision` (idempotent, evidence-linked back to the review and its per-agent outputs); a **named human approves/rejects** it, writing an `ApprovalRecord` (durable memory). **LES-019 operationalized:** a decision drafted from an *abstained* review is `needs_evidence` and **cannot be approved** (approve → 409 naming the re-draft path) until re-drafted from a cleared-floor review. Pending drafts surface in the digest (rule 6). No new tables/migration (reuses `Decision`+`ApprovalRecord`); backend only. Built by an Opus builder subagent, Orchestrator-verified independently. Branch restarted from `main` at `1306138`. **Next: operator picks the next build — Phase C Part 2 (approval UI + repo-vault ADR rendering), Phase B (architecture semantics / language weighting), or the Council dashboard (AOS-COUNCIL-002).**

### Note — GitHub connector expired mid-session

The GitHub MCP OAuth token expired during PR #53 (long session). git push/CI were unaffected (separate proxy auth); only PR comments/reads were blocked. Operator re-authorized; the gate was posted late. If it recurs: reconnect GitHub via `/mcp` or claude.ai connector settings — git operations keep working regardless.

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- **Branch name is env-pinned, not stale-by-neglect:** `claude/aos-runtime-002-scanner-1egyjw` is fixed by the session config; each package restarts it from `main` (one PR = one package, clean history). A per-package scheme (`opus/aos-<pkg>`) is adopted only if the operator reconfigures the env / grants explicit permission. See the Role-contract note in `docs/ORCHESTRATOR_PLAYBOOK.md` (Lead-Architect critique 2026-07-05, operator Decision 2a).
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- **The decision loop (Council → Decision → human approve/reject → memory).** New `packages/aos_core/aos_core/services/decisions.py`: `draft_decision_from_review(db, *, review_id)` (idempotent via `Decision.meta["council_review_id"]`; abstained review → `needs_evidence`), `approve_decision(db, *, decision_id, approver, rationale=None)` (draft-only; `needs_evidence` → 409 naming the re-draft path; writes `ApprovalRecord`), `reject_decision(...)` (draft/needs_evidence only; guards re-transition; writes `ApprovalRecord`). Status vocabulary rides `AuditMixin.status` — no new column.
- `apps/api/app/routes/decisions.py`: 3 endpoints (`POST /council-reviews/{review_id}/draft-decision`, `POST /decisions/{id}/approve`, `POST /decisions/{id}/reject`). `apps/api/app/schemas.py`: `DecisionApprove`/`DecisionReject` + `approved_by`/`approved_at` on `DecisionRead`.
- `packages/aos_core/aos_core/services/digest.py`: rule 6 — pending (`draft`/`needs_evidence`) decisions surface as `decision_pending` changes + an "approve or reject" nudge.
- `apps/api/tests/test_decisions_loop.py` (new): 9 hermetic, count-agnostic tests. `test_digests_api.py`: pending-decision assertion. `test_route_inventory.py`: route freeze 42→45.
- Docs: `docs/DECISION_LIFECYCLE.md` (Decision stage marked implemented + abstention-blocks-approval rule), `docs/CAPABILITY_MAP.md` (Layer 4 decision-loop entry + `services/decisions.py`), `.archetype/work/AOS-COUNCIL-PHASEC.md` (spec), state files.

### Files changed

- `packages/aos_core/aos_core/services/decisions.py` (new), `packages/aos_core/aos_core/services/digest.py`
- `apps/api/app/routes/decisions.py`, `apps/api/app/schemas.py`
- `apps/api/tests/test_decisions_loop.py` (new), `apps/api/tests/test_digests_api.py`, `apps/api/tests/test_route_inventory.py`
- `docs/DECISION_LIFECYCLE.md`, `docs/CAPABILITY_MAP.md`, `.archetype/work/AOS-COUNCIL-PHASEC.md`
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- On a 3.12 venv: `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests -q` → **116 passed** (+9 decision-loop, +1 digest); `apps/worker/tests` → **7 passed**; `ruff check apps/api packages/aos_core apps/worker tools` clean; `compileall` clean.
- Independently confirmed (builder ≠ verifier): the abstention-blocks-approval **409** (`test_approve_needs_evidence_is_409`), the `ApprovalRecord` writes on approve + reject, `approved_by`/`approved_at` set on approve, no new Alembic migration, no `apps/web` change.

### Known Risks

- Backend only — no approval UI yet (Control Tower decision-approval view is Phase C Part 2); an approved decision is durable in the DB (`Decision` + `ApprovalRecord`) but is **not yet rendered into a repo-vault ADR** (git I/O — Phase C Part 2). Until then the vault (source of truth) does not carry approved decisions.
- Manually created decisions keep status `active` and are outside this governance gate by design.

### Blockers

- None.

### Verification Status

Verified (PR #55 merged as `1306138`; AOS-COUNCIL-PHASEC Done)

### Verification Level

Level 3

### Verification Method

Built by an Opus builder subagent, then Orchestrator-verified independently (builder ≠ verifier): `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests` → **116 passed**; `apps/worker/tests` → **7 passed**; the abstention-blocks-approval 409 and the `ApprovalRecord` writes confirmed by reading the tests + service; `git status` confirmed no new Alembic migration and no `apps/web` change; `ruff check apps/api packages/aos_core apps/worker tools` clean; `compileall` clean; guardian PASS. Branch restarted from `main` at `1306138`.

### Evidence

- `CouncilReview` → idempotent draft `Decision`; approve sets `approved_by`/`approved_at` + writes `ApprovalRecord`; abstained-review draft is `needs_evidence` and approval returns 409; pending drafts surface in the digest; api 116 / worker 7 green; ruff full CI scope + compileall clean.

### Limitations

Backend only — no approval UI, and an approved decision is durable in the DB (`Decision` + `ApprovalRecord`) but not yet rendered into a repo-vault ADR (git I/O). Both are Phase C Part 2. Manually created decisions keep status `active` and are outside this governance gate by design.

### Required Next Verifier

None — PR #55 merged as `1306138` and reconciled.

### Next Recommended Step

**Operator's call.** The decision loop is live backend. Continuations: (1) **Phase C Part 2** — a Control Tower decision-approval view + render approved decisions into repo-vault ADRs (the file/git-I/O half deferred from Part 1), closing `DECISION_LIFECYCLE.md`'s Decision→Knowledge handoff into the source-of-truth vault; (2) **Phase B** — architecture semantics (LES-014 dependency/compose edges; `example-voting-app` ready test) + language weighting (LES-013); (3) the **Council dashboard** (AOS-COUNCIL-002). Scanner backlog also open: LES-016 (manifest/ecosystem coverage), LES-017 (secret-signal precision). Other open: AOS-20 (doc-staleness), AOS-22 (backups).

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