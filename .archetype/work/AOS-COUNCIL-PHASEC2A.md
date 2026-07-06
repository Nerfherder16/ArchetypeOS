# AOS-COUNCIL-PHASEC2A — Decision → Knowledge: render approved decisions into repo-vault ADRs

## Status

In Progress

## Origin

Operator direction: "let's do 1" (Phase C Part 2). Phase C Part 1 (PR #55) built the decision loop up to human approve/reject with DB memory; it deferred the **Decision → Knowledge** handoff into the source-of-truth vault. This package closes it: an **approved** `Decision` is rendered into an ADR markdown file under `knowledge/wiki/decisions/` (the vault is the source of truth) and projected as a re-syncable `KnowledgePage` so it also surfaces on the Knowledge dashboard. This is Part 2**a** (backend); Part 2**b** (the Control Tower decision-approval view) follows as a separate PR.

## Governing constraints

- **Repo vault is the source of truth; `KnowledgePage` is a re-syncable derived projection** (RFC-0002 / RFC-0004). Therefore the ADR must be written to the vault file AND `sync_knowledge` must be able to re-derive the decision page from that file — a DB reset must lose nothing.
- **Local-first write** — the ADR write targets `settings.knowledge_root` (writable on the primary WSL target). The compose stack mounts the vault **`:ro`**, so in that deployment the write is unavailable; the endpoint must fail **gracefully and explicitly** (not 500) and must never corrupt the approval state.
- **Approval stays a pure DB act** — ADR export is a **separate, explicit step** (its own endpoint), decoupled from `approve_decision`, so a non-writable vault can never make approval fail. Only an `approved` decision can be exported.
- **Additive, human-visible memory** — an ADR records a governance action; writing it under `knowledge/wiki/decisions/` matches `docs/DECISION_LIFECYCLE.md` ("a recorded ADR or decision card").

## Verified Baseline

- `settings.knowledge_root = Path("./knowledge")` (`packages/aos_core/aos_core/config.py:11`). `knowledge/wiki/decisions/` exists (only `.gitkeep`). `templates/adr.md` is the ADR skeleton (Status / Date / Context / Decision / Alternatives Considered / Evidence / Consequences / Migration Plan / Acceptance Criteria / Reviewers).
- `sync_knowledge(db, knowledge_root)` (`services/knowledge.py`) currently parses **only** `wiki/lessons/index.md` → `LES-*` rows → `KnowledgePage` upserts. It does not scan decisions.
- `KnowledgePage` (`models.py:184`): `project_id` (nullable), `title`, `vault_path`, `page_type`, `validation_state` (default `"raw"`), `source_refs` (JSON), `checksum`. Upserts key on `vault_path` (see the lessons sync).
- `Decision` (`models.py:122`) has `status` (loop states from Part 1: `draft`/`needs_evidence`/`approved`/`rejected`), `approved_by`, `approved_at`, `meta` (JSON; already carries `council_review_id`), and the content fields (`context`/`decision`/`alternatives`/`tradeoffs`/`consequences`/`evidence`/`confidence`).
- Part 1 service: `packages/aos_core/aos_core/services/decisions.py` (`DECISION_APPROVED` etc.). Routes in `apps/api/app/routes/decisions.py`. `now_utc`/`new_id` live in `models.py`.

## In-Scope Files

- **`packages/aos_core/aos_core/services/adr.py`** (new):
  - `render_adr_markdown(decision, review=None) -> str` — pure, testable. Emits an ADR shaped like `templates/adr.md`: `# ADR — {title}`, Status `Accepted`, Date from `decision.approved_at` (fallback `created_at`), Context = `decision.context`, Decision = `decision.decision`, Alternatives from `decision.alternatives`, Evidence from `decision.evidence` (+ the linked council review id/verdict if `review` given), Consequences from `decision.consequences`/`tradeoffs`, Acceptance Criteria (from `decision.meta` if present else "TBD"), Reviewers list. No I/O.
  - `_adr_slug(decision) -> str` and filename `ADR-{slug}-{decision.id[:8]}.md` (stable per decision → idempotent overwrite; unique across similarly-titled decisions).
  - `export_decision_adr(db, *, decision_id, knowledge_root) -> KnowledgePage`: 404 if missing; **409 if status != `approved`**; render markdown; write to `Path(knowledge_root)/"wiki"/"decisions"/<filename>` (create dirs; on `OSError`/read-only → raise `HTTPException(status_code=409, ...)` naming the local-first-checkout requirement); **upsert** a `KnowledgePage` keyed on `vault_path` (relative to `knowledge_root`) with `page_type="decision"`, `validation_state="approved"`, `source_refs=[{"type":"decision","id":...},{"type":"council_review","id":...}]`, `checksum` = sha256 of the markdown; store `decision.meta["adr_path"]` = vault_path. Idempotent (re-export overwrites the file and updates the one page).
- **`packages/aos_core/aos_core/services/knowledge.py`**: extend `sync_knowledge` to also scan `wiki/decisions/*.md` and upsert a `KnowledgePage` per ADR file (`page_type="decision"`, `validation_state` parsed from the `## Status` line → `approved`/`raw`, `title` from the first `# ` heading, `checksum`), so decision pages are **re-derivable from the vault** (the invariant). Keep it stdlib-only and tolerant (a malformed/empty file is skipped, never raises). The sync result count includes decisions.
- **`apps/api/app/routes/decisions.py`**: `POST /decisions/{decision_id}/adr` → `KnowledgePageRead` (or a small `AdrExportRead{vault_path, page_id}`) — calls `export_decision_adr(db, decision_id=..., knowledge_root=settings.knowledge_root)`; propagate the service's 404/409.
- **`apps/api/app/schemas.py`**: response schema for the export (reuse `KnowledgePageRead` if it exists; else add `AdrExportRead`).
- **`apps/api/tests/test_adr_export.py`** (new): `render_adr_markdown` contains the decision's title/decision/context + an Evidence entry for the council review; export writes a file under `tmp_path/wiki/decisions/` and creates a `KnowledgePage` (`page_type="decision"`); **draft/needs_evidence decision → 409**; idempotent re-export overwrites and keeps exactly one page; a read-only/again-nonexistent root path → 409 (not 500). **Use `tmp_path` as `knowledge_root` — never write into the real repo vault.**
- **`apps/api/tests/test_knowledge.py`**: a count-agnostic assertion that after writing an ADR file into a temp `wiki/decisions/`, `sync_knowledge` derives a `decision` page (derive counts from live state — LES-012).
- **`apps/api/tests/test_route_inventory.py`**: register `POST /decisions/{decision_id}/adr` (freeze 45→46).
- **Docs**: `docs/DECISION_LIFECYCLE.md` (Decision → Knowledge: ADR export into the vault, local-first, `:ro` in compose), `docs/CAPABILITY_MAP.md` (Layer 1 Knowledge + Layer 4 decision loop), `.archetype/work/AOS-COUNCIL-PHASEC2A.md` (this spec), state docs.

## Out-of-Scope

- **Part 2b — the Control Tower decision-approval view** (frontend `apps/web` + e2e). Separate PR.
- Auto-exporting on approve (kept a separate explicit step by design).
- Changing the compose mount to `:rw` (would let the container mutate the developer's vault — an operator decision, not taken here; local-first write only).
- New tables/migration (reuse `Decision`/`KnowledgePage`).

## Acceptance Criteria

- An approved `Decision` can be exported to an ADR markdown under `knowledge/wiki/decisions/`, linking back to the decision + its council review, and projected as a `KnowledgePage` (`page_type="decision"`) — idempotent (re-export overwrites, one page).
- Only an `approved` decision is exportable (draft/needs_evidence/rejected → 409); a non-writable vault root → 409 with a local-first message, never a 500, and never mutates the decision's approval state.
- `sync_knowledge` re-derives decision pages from `wiki/decisions/*.md` — a DB reset loses nothing (the invariant holds).
- api + worker suites green on the CI-scope venv; ruff full CI scope + compileall clean; guardian PASS. No migration; no `apps/web` change.

## Verification (Orchestrator, independent — builder ≠ verifier)

Re-run api+worker; assert export is approved-only (409) and idempotent; confirm the ADR lands under a temp `wiki/decisions/` (never the real vault) and that `sync_knowledge` re-derives it; confirm the read-only-root path returns 409 not 500; confirm no migration and no `apps/web` change; ruff full CI scope + compileall; guardian.
