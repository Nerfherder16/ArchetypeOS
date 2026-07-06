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

RFC-0008 Phase 2 — code-aware distillation (AOS-DISTILL-002). (Prior arc, all merged: AOS-DISTILL-001 PR #61 — distillation MVP/pipe; AOS-LLM-ISOLATION-001 PR #60 — LES-021 provider isolation; AOS-ARCH-SEMANTICS-001 PR #59 — Phase B compose edges + language weighting; RFC-0008 PR #58; Phase C PRs #54–#57.)

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `8c4a400` after the PR #62 merge; env-pinned — see branch note above)

### PR

#62 — **Merged** as `8c4a400` (merge commit).

### Status

Merged — **the Knowledge Distillation Engine now reads the codebase, not just the README** (the operator's key request). `distill_repository` selects a bounded, meaningful set of source (entry points + largest source-classified files + primary manifest, via `safe_repo_path`, capped + tolerant), then produces two code-derived layers: a **deterministic** `## Components (from source)` section (pure stdlib `ast`+regex, per-file-cited, hermetic/CI-tested) and — only for a real **LES-021-isolated** `claude_code` provider — a reasoned `## How it works / Built for` narrative citing files (the deterministic provider fabricates nothing, so CI never calls a live model). **Live-validated:** distilling real `free-llm-api-resources` selected `src/data.py` and produced a grounded, code-cited narrative naming the actual `MODEL_TO_NAME_MAPPING` mechanism the README omits, with zero ArchetypeOS contamination. No migration/frontend. This completes the founding "feed a repo → extract what's useful → Obsidian for reuse" *extraction* arc (Phase B → LES-021 → MVP → code-aware). Branch restarted from `main` at `8c4a400`. **Next: operator's direction. Recommendation: the Knowledge Transfer Engine (RFC-0008's deferred "useful *for* a target repo" half — relevance/retrieval + embeddings).**

### Note — GitHub connector expired mid-session

The GitHub MCP OAuth token expired during PR #53 (long session). git push/CI were unaffected (separate proxy auth); only PR comments/reads were blocked. Operator re-authorized; the gate was posted late. If it recurs: reconnect GitHub via `/mcp` or claude.ai connector settings — git operations keep working regardless.

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- **Branch name is env-pinned, not stale-by-neglect:** `claude/aos-runtime-002-scanner-1egyjw` is fixed by the session config; each package restarts it from `main` (one PR = one package, clean history). A per-package scheme (`opus/aos-<pkg>`) is adopted only if the operator reconfigures the env / grants explicit permission. See the Role-contract note in `docs/ORCHESTRATOR_PLAYBOOK.md` (Lead-Architect critique 2026-07-05, operator Decision 2a).
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- **Phase B — compose-derived architecture edges + source-classified language weighting.** `packages/aos_core/aos_core/repository_scanner.py`: parse detected compose files (`yaml.safe_load`, tolerant try/except) into `service` nodes + `depends_on` edges (list form `[db, redis]` and map form `{db: {condition: ...}}`), capped at `MAX_COMPOSE_SERVICES`; add `LANGUAGE_CLASS` (source/config/markup/docs) → `primary_language` (top source language, fallback overall) + source-first `primary_language_hints` + `language_classes` in the summary; raw `language_mix` unchanged; the scanner reads no file bodies except compose files.
- `packages/aos_core/aos_core/services/scan.py`: populate `RepositoryDNA.runtime_services` from compose services; **generalize edge persistence** — register the root node under `scan["root_name"]`, resolve each edge's real `from` via `item["from"]`, dedup by `item["type"]` (was: repo-rooted `from`, `type=="directory"` dedup) — so `depends_on` edges render service→dep and services dedup on rescan.
- `apps/api/requirements.txt` + `apps/worker/requirements.txt`: `PyYAML==6.0.2` (the scanner's only new dep).
- `apps/api/tests/test_scanner.py` (+6 tests) + `apps/api/tests/fixtures/compose-repo/` (new fixture: `docker-compose.yml` with list+map `depends_on`, plus `.py`/`.md`/`.yml`/`.toml` for language classification).
- Lessons: `LES-013.md` → **closed**; `LES-014.md` → compose half delivered, **stays open** for manifest/dependency + import-graph edges; `index.md` both rows. `docs/CAPABILITY_MAP.md` (Layer 3). Spec `.archetype/work/AOS-ARCH-SEMANTICS-001.md`.

### Files changed

- `packages/aos_core/aos_core/repository_scanner.py`, `packages/aos_core/aos_core/services/scan.py`
- `apps/api/requirements.txt`, `apps/worker/requirements.txt`
- `apps/api/tests/test_scanner.py`, `apps/api/tests/fixtures/compose-repo/*` (new)
- `knowledge/wiki/lessons/LES-013.md`, `LES-014.md`, `index.md`, `docs/CAPABILITY_MAP.md`, `.archetype/work/AOS-ARCH-SEMANTICS-001.md`
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests -q` → **132 passed** (+6 scanner); `apps/worker/tests` → **7 passed**; `ruff` full CI scope + `compileall` clean.
- Independently confirmed (builder ≠ verifier): scanned the compose fixture → `service` nodes `{db,redis,web,worker}`, `depends_on` edges `{web→db, web→redis, worker→db}`, `runtime_services` populated, `primary_language=Python`; **rescan idempotent** (nodes 5→5, edges 3→3 — validates the `scan.py` generalization); malformed compose → note, no raise; no-compose repo → no service nodes; no `apps/api/alembic`/`apps/web` change.

### Known Risks

- Adds a **PyYAML** runtime dependency for the scanner (api+worker). compose-smoke covers the container build; if a scan ever fails on `import yaml`, check the image requirements first.
- LES-014's manifest/dependency + import-graph edges remain unbuilt (the non-compose half).

### Blockers

- None.

### Verification Status

Verified (PR #59 merged as `8296cfc`; AOS-ARCH-SEMANTICS-001 Done — Phase B)

### Verification Level

Level 3

### Verification Method

Built by an Opus builder subagent, then Orchestrator-verified independently (builder ≠ verifier): scanned the `compose-repo` fixture and confirmed the `service`/`depends_on` graph + `primary_language` + `runtime_services`; confirmed **rescan idempotency** (nodes 5→5, edges 3→3) and malformed-compose tolerance; `pytest apps/api/tests` → **132 passed**; `apps/worker/tests` → **7 passed**; `ruff` full CI scope + `compileall` clean; `git status` confirms no Alembic migration and no `apps/web` change; guardian **PASS_WITH_WARNINGS** (the `scanner-new-ecosystem` WARN is the test-fixture files tripping the self-scan — acknowledged in the PR body). Branch restarted from `main` at `8296cfc`.

### Evidence

- Compose files now yield real `service`/`depends_on` architecture (`{web→db, web→redis, worker→db}` on the fixture) + `RepositoryDNA.runtime_services`; config/docs-heavy repos report a source-classified `primary_language` (`Python`, not YAML/Markdown); api 132 / worker 7; rescan idempotent; no migration/frontend.

### Limitations

LES-014's manifest/dependency + import-graph edges are a follow-up (LES-014 stays open). Language weighting is source-vs-config classification, not lines-of-code (the scanner reads no non-compose file bodies). Adds a PyYAML runtime dependency (compose-smoke covers the build).

### Required Next Verifier

None — PR #59 merged as `8296cfc` and reconciled. Phase B complete.

### Next Recommended Step

**Operator's direction — Phase C complete, Phase B merged.** Recommended: **LES-021 (isolate the `claude_code` provider — a small tactical prerequisite) → RFC-0008 (repository content extraction)**, the operator's founding "feed a repo → extract what's useful → Obsidian for reuse" capability; Phase B just made its structural counterpart richer. Alternatives: **scanner precision** (LES-016 manifest/ecosystem coverage, LES-017 secret-signal precision); **LES-014 manifest/import architecture edges**; the standalone **Council dashboard** (AOS-COUNCIL-002); AOS-20 (doc-staleness), AOS-22 (backups).

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