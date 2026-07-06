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

Decision → Knowledge: render approved decisions into repo-vault ADRs (AOS-COUNCIL-PHASEC2A, Phase C Part 2a). (Prior: AOS-COUNCIL-PHASEC merged PR #55 / `1306138` — the decision loop; AOS-COUNCIL-PHASEA PR #54 — first real Council run; AOS-PORTFOLIO-001 PR #53 / AOS-21; AOS-COUNCIL-001 PR #49 / AOS-19.)

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `973d532` after the PR #56 merge; env-pinned — see branch note above)

### PR

#56 — **Merged** as `973d532` (merge commit). CI run 28766562398 all 6 jobs green on head `a2ce32f`.

### Status

Merged — **the Decision → Knowledge handoff into the source-of-truth vault is live.** An **approved** `Decision` exports (via `POST /decisions/{id}/adr`) to an ADR markdown under `knowledge/wiki/decisions/` (shaped like `templates/adr.md`, linking the decision + its council review) and projects a re-syncable `KnowledgePage` (`page_type="decision"`) so it also surfaces on the Knowledge dashboard. **Local-first write:** the export targets `settings.knowledge_root` (writable on WSL); the compose stack mounts the vault `:ro`, so there the endpoint returns a clean **409** (never 500) and **never** mutates the approval state — export is decoupled from approve. **Invariant preserved:** `sync_knowledge` now re-derives decision pages from `wiki/decisions/*.md`, so a DB reset loses nothing. Approved-only + idempotent; no new tables/migration; backend only. Built by an Opus builder subagent, Orchestrator-verified independently. Branch restarted from `main` at `973d532`. **Next: Phase C Part 2b — the Control Tower decision-approval view (frontend + e2e), which finishes Phase C.**

### Note — GitHub connector expired mid-session

The GitHub MCP OAuth token expired during PR #53 (long session). git push/CI were unaffected (separate proxy auth); only PR comments/reads were blocked. Operator re-authorized; the gate was posted late. If it recurs: reconnect GitHub via `/mcp` or claude.ai connector settings — git operations keep working regardless.

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- **Branch name is env-pinned, not stale-by-neglect:** `claude/aos-runtime-002-scanner-1egyjw` is fixed by the session config; each package restarts it from `main` (one PR = one package, clean history). A per-package scheme (`opus/aos-<pkg>`) is adopted only if the operator reconfigures the env / grants explicit permission. See the Role-contract note in `docs/ORCHESTRATOR_PLAYBOOK.md` (Lead-Architect critique 2026-07-05, operator Decision 2a).
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- **Decision → Knowledge: repo-vault ADR export.** New `packages/aos_core/aos_core/services/adr.py`: `render_adr_markdown(decision, review=None)` (pure, ADR-shaped) + `export_decision_adr(db, *, decision_id, knowledge_root)` — 404 missing / **409** non-approved / **409** on `OSError` (read-only vault) without mutating the decision; upserts one `KnowledgePage` (`page_type="decision"`, `validation_state="approved"`, sha256 checksum, `source_refs` decision+council_review) keyed on `vault_path`; stamps `decision.meta["adr_path"]`; idempotent.
- `packages/aos_core/aos_core/services/knowledge.py`: `parse_adr` + `sync_knowledge` extended to scan `wiki/decisions/*.md` and re-derive decision pages (folds into `synced`/`created`/`updated`; `open_lessons` stays lessons-only) — the re-syncable invariant.
- `apps/api/app/routes/decisions.py`: `POST /decisions/{decision_id}/adr` → `KnowledgePageRead`.
- `apps/api/tests/test_adr_export.py` (new): 6 hermetic tests (all use `tmp_path`, never the real vault). `test_knowledge.py`: count-agnostic decision-derivation. `test_route_inventory.py`: route freeze 45→46.
- Docs: `docs/DECISION_LIFECYCLE.md` (Decision → Knowledge ADR export; local-first; `:ro` in compose), `docs/CAPABILITY_MAP.md` (Layer 1 + Layer 4), `.archetype/work/AOS-COUNCIL-PHASEC2A.md` (spec), state files.

### Files changed

- `packages/aos_core/aos_core/services/adr.py` (new), `packages/aos_core/aos_core/services/knowledge.py`
- `apps/api/app/routes/decisions.py`
- `apps/api/tests/test_adr_export.py` (new), `apps/api/tests/test_knowledge.py`, `apps/api/tests/test_route_inventory.py`
- `docs/DECISION_LIFECYCLE.md`, `docs/CAPABILITY_MAP.md`, `.archetype/work/AOS-COUNCIL-PHASEC2A.md`
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- On a 3.12 venv: `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests -q` → **123 passed** (+6 ADR-export, +1 sync decision-derivation); `apps/worker/tests` → **7 passed**; `ruff check apps/api packages/aos_core apps/worker tools` clean; `compileall` clean.
- Independently confirmed (builder ≠ verifier): export approved-only (**409**), read-only vault → **409** (not 500) with the decision unchanged, idempotent (one file, one page), `sync_knowledge` re-derives decision pages; a live render sanity check (tmp only) matched `templates/adr.md`; no migration, no `apps/web` change, no stray ADR in the real vault.

### Known Risks

- **Local-first write only** — the containerized (`:ro`) stack cannot export ADRs by design (returns 409); flipping the compose mount to `:rw` is a separate operator decision (not taken). Backend only — surfacing ADR export in the UI is Part 2b.
- After a DB reset, sync re-derives decision pages with a `vault_file` source_ref (the structured decision/council-review ids are repopulated on the next export).

### Blockers

- None.

### Verification Status

Verified (PR #56 merged as `973d532`; AOS-COUNCIL-PHASEC2A Done)

### Verification Level

Level 3

### Verification Method

CI run 28766562398 all 6 jobs green on head `a2ce32f`; built by an Opus builder subagent, then Orchestrator-verified independently (builder ≠ verifier): `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests` → **123 passed**; `apps/worker/tests` → **7 passed**; the approved-only 409, read-only-vault 409 (decision unchanged), and idempotency confirmed by reading the tests + service and a live render sanity check; `git status --porcelain apps/api/alembic apps/web knowledge` empty (no migration, no web change, no stray ADR); `ruff` full CI scope + `compileall` clean; guardian PASS. Branch restarted from `main` at `973d532`.

### Evidence

- Approved `Decision` → ADR under `wiki/decisions/` + a `KnowledgePage` (`page_type="decision"`) linking the council review; export approved-only + idempotent; read-only vault → 409 not 500; `sync_knowledge` re-derives decision pages (DB reset loses nothing); api 123 / worker 7 green; ruff full CI scope + compileall clean.

### Limitations

Local-first write only — the `:ro` compose stack cannot export ADRs (409 by design); flipping the mount to `:rw` is a separate operator decision (not taken). Backend only — the approval UI is Part 2b. After a DB reset, sync re-derives decision pages with a `vault_file` source_ref (structured ids repopulated on the next export).

### Required Next Verifier

None — PR #56 merged as `973d532` and reconciled.

### Next Recommended Step

**Phase C Part 2b — the Control Tower decision-approval view (recommended).** The decision loop is complete on the backend (Council → draft → approve/reject → ADR-in-vault, PRs #55/#56). Part 2b surfaces it in the UI: a Control Tower section listing council reviews + their drafted decisions with status badges, plus draft-from-review, approve/reject (with an approver), and export-ADR on approved — with Playwright e2e (extends the existing `apps/web/e2e/decisions.spec.ts`). That finishes Phase C. Alternatives: **Phase B** — architecture semantics (LES-014 dependency/compose edges; `example-voting-app` ready test) + language weighting (LES-013); the **Council dashboard** (AOS-COUNCIL-002). Scanner backlog also open: LES-016 (manifest/ecosystem coverage), LES-017 (secret-signal precision). Other open: AOS-20 (doc-staleness), AOS-22 (backups).

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