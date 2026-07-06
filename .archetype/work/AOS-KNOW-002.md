# AOS-KNOW-002 — Knowledge read path: vault→DB sync + KnowledgePage read API + digest open-lessons rule (RFC-0002 / RFC-0004 read path)

## Status

In Progress

## Origin

Plane **AOS-23** ("Knowledge read path: KnowledgePage API + lessons visible to the digest"). Closes two deliberate deferrals: (1) the KnowledgePage API read path (deferred in AOS-KNOW-001 "until a distillation or ingestion path exists") and (2) digest visibility of open lessons (deferred in RFC-0004 "until a package gives lessons a read path — candidate pairing: the deferred KnowledgePage API"). Operator-directed (2026-07-05, "do aos-23, then aos-21, then reevaluate the roadmap"). **This is the backend phase (23a)**; the dashboard Knowledge view is AOS-KNOW-003 (23b). Prompted by the Lead-Architect critique #4 ("knowledge is stored-but-not-operational").

## Governing design decision (read this first)

**The repo vault stays the source of truth; the DB (`KnowledgePage`) is a derived read projection.** RFC-0004 (`docs/rfc/RFC-0004-Learning-Feedback-Loop.md:50`) rejected *DB-as-primary-store* for lessons because "process lessons must survive database resets and travel with the repo." AOS-23 does not violate that: lessons remain authoritative in `knowledge/wiki/lessons/` (the `index.md` table wins on conflict); a **sync** parses the vault and **upserts** `KnowledgePage` rows so lessons gain an API/DB read surface. A DB reset loses nothing — re-run the sync from the repo. This is precisely the read path RFC-0004 pointed at, honoring repo-as-truth.

**Runtime reachability:** the api/worker Docker images do **not** ship `knowledge/` and there is no `knowledge_root` setting (Explore-confirmed). This package adds `knowledge_root` config (default `./knowledge`) and runs the sync where the repo tree is present (api-tests, local, a repo-root/authed invocation). It does **not** change the Dockerfiles or compose this package — making the sync self-contained in the shipped compose (a `./knowledge:ro` mount) is a documented follow-up (23b or its own micro-PR), kept out to avoid a compose-smoke-touching Docker change here.

## Verified Baseline

Confirmed by inspection:

- `KnowledgePage` (`packages/aos_core/aos_core/models.py:184`): `project_id` (GUID FK, **NOT NULL**), `title` (String255), `vault_path` (Text), `page_type` (String128), `validation_state` (String128, default `"raw"`), `source_refs` (JSONField list), `checksum` (String128). **Nothing writes it** (grep: only the class def). Lessons are global (not project-scoped) → `project_id` must become nullable.
- Lessons: `knowledge/wiki/lessons/index.md` — a markdown table `| ID | Date | Category | Lesson (short) | Source | Status | Consumed by |` (LES-001..011; **LES-007 is the only `open`**). The table is authoritative ("this table wins"). Pages `LES-*.md` follow `knowledge/templates/page-template.md` (headings: Aliases/Status/Owner/Evidence/Linked/Content).
- `build_digest` (`packages/aos_core/aos_core/services/digest.py`): DB-only, draft rules 1–4, **no lessons rule**, runs in the worker (no vault). Returns a `NightlyDigest` (`summary`, `changes`, `recommendations`, `repeated_tasks`).
- Alembic head is `0003_council` (`revision='0003'`). A nullability change to `knowledge_pages.project_id` is migration `0004` (`down_revision='0003'`); on sqlite this needs `op.batch_alter_table`. The no-drift autogenerate probe is the gate.
- `config.py` roots: `database_url`, `redis_url`, `artifact_root`, `repository_root`, `cors_origins`, `llm_provider` — **no `knowledge_root`**.
- API is now modular (`apps/api/app/routes/*.py`, AOS-APIROUTES-001). New routes go in a new `routes/knowledge.py` included in `main.py`. Schemas in `apps/api/app/schemas.py`. Core-service tests live in `apps/api/tests/`.

## In-Scope Files

- `packages/aos_core/aos_core/config.py` (add `knowledge_root: Path = Path("./knowledge")`)
- `packages/aos_core/aos_core/models.py` (`KnowledgePage.project_id` → nullable)
- `apps/api/alembic/versions/0004_knowledge_page_nullable_project.py` (new; `down_revision='0003'`; `op.batch_alter_table` for sqlite; `import aos_core.models`)
- `packages/aos_core/aos_core/services/knowledge.py` (new: lessons-index parser + `sync_knowledge(db, knowledge_root) -> dict` upsert)
- `apps/api/app/routes/knowledge.py` (new: `POST /knowledge/sync`, `GET /knowledge/pages`, `GET /knowledge/pages/{page_id}`), `apps/api/app/main.py` (include the router), `apps/api/app/schemas.py` (`KnowledgePageRead`, `KnowledgeSyncResult`)
- `packages/aos_core/aos_core/services/digest.py` (add rule 5: surface open lessons)
- `apps/api/tests/test_knowledge.py` (new: parser + sync + read API), `apps/api/tests/test_digests_api.py` or `test_scheduler.py`-style unit for the digest lessons rule (extend the existing digest test)
- `docs/CAPABILITY_MAP.md`, `docs/KNOWLEDGE_VAULT_STRUCTURE.md` (note the read path + sync), state docs + this spec

## Out-of-Scope

- Dashboard Knowledge view (AOS-KNOW-003 / 23b). Ingesting non-lesson vault domains (all empty scaffolding today) — the parser handles lessons; a generic page ingest is a later extension (the API is generic over `KnowledgePage`, so no API change needed later). Dockerfile/compose changes to ship/mount the vault (documented follow-up). Graph/embeddings. Changing the lessons markdown format. No new RFC (this implements RFC-0002's read surface + RFC-0004's deferred lesson path).

## Design

- **`knowledge_root` setting** (default `./knowledge`): where the sync reads the vault.
- **Migration `0004`**: `KnowledgePage.project_id` nullable (lessons are global). `op.batch_alter_table("knowledge_pages")` → `alter_column("project_id", nullable=True)`. Post-migration no-drift probe MUST be 0 ops.
- **`aos_core.services.knowledge`**:
  - `parse_lessons_index(text) -> list[dict]`: stdlib-only parse of the `index.md` markdown table → rows `{lesson_id, date, category, short, source, status, consumed_by}`. Tolerant: ignores non-data lines; only rows whose ID cell matches `[[LES-\d+]]`.
  - `sync_knowledge(db, knowledge_root) -> dict`: read `knowledge_root/wiki/lessons/index.md`; for each lesson **upsert** a `KnowledgePage` (idempotent key = `vault_path` `wiki/lessons/<LES-id>.md`): `project_id=None`, `title=short`, `page_type="lesson"`, `validation_state=status` (`open`/`closed`/`validated`→ store the status verbatim; `open`/`closed` are the queue states), `source_refs=[{"type":"pr_or_run","ref":source}]`, `checksum` = a stable hash of the row. Update-in-place if the `vault_path` row exists (no dupes on re-sync). Return `{"synced": n, "created": c, "updated": u, "open_lessons": k}`. Missing vault dir → return zeros (do not raise).
- **Read API** (`routes/knowledge.py`, global — not project-scoped):
  - `POST /knowledge/sync` → runs `sync_knowledge(db, settings.knowledge_root)`, returns the counts. (Works where the vault is reachable — api-tests point `knowledge_root` at the repo `./knowledge`; in the shipped compose it needs the vault mount, a documented follow-up.)
  - `GET /knowledge/pages?page_type=&validation_state=` → list `KnowledgePage` (desc by updated_at, cap 100), optional filters.
  - `GET /knowledge/pages/{page_id}` → one page; 404 if missing.
- **Digest rule 5** (`build_digest`): query `KnowledgePage` where `page_type=="lesson"` and `validation_state=="open"`; add an `open_lessons` list to the digest (id/title) **and** a draft recommendation per RFC-0004 ("open lessons are the improvement queue") — e.g. `{"title": f"Consume open lesson: {title}", "reason": "open lesson in the learning queue", "status": "draft"}`. Since lessons are global, they surface in every project's digest. Preserve the existing `NightlyDigest` shape; add `open_lessons` to `changes` or as its own field via the model's existing JSON columns (do not add a column — reuse `changes` with `type: "open_lesson"` to avoid a second migration).

## Acceptance Criteria

- **Lessons sync from the vault into KnowledgePage** — evidence: `test_sync_knowledge` — `sync_knowledge(db, <repo>/knowledge)` creates 11 lesson `KnowledgePage` rows (page_type="lesson"); re-running is idempotent (no dupes; `updated` on second run); `open_lessons == 1` (LES-007).
- **Parser is correct + tolerant** — evidence: `test_parse_lessons_index` — parses the real `index.md` → 11 rows with the right ids/status; a malformed/empty table → `[]` (no raise).
- **KnowledgePage read API** — evidence: `test_knowledge_api` — `POST /knowledge/sync` returns counts; `GET /knowledge/pages?page_type=lesson` lists them; `?validation_state=open` → just LES-007; `GET /knowledge/pages/{id}` returns it (404 on missing).
- **project_id nullable, no drift** — evidence: `alembic upgrade head` (0001→…→0004); `knowledge_pages.project_id` nullable; autogenerate no-drift probe → 0 ops; the 24-table count is unchanged (0004 alters, adds no table).
- **Digest surfaces open lessons** — evidence: extend the digest test — after `sync_knowledge`, `build_digest(project_id)` includes an `open_lesson` entry / draft recommendation for LES-007; with no open lessons, none.
- **Nothing broken** — evidence: api suite (94 + new) green; worker suite green; ruff/compile clean.

## Verification Plan

Level 2: 3.12 venv — ruff/compile; `pytest apps/api/tests` (incl. the new knowledge + digest tests). Level 4 (Orchestrator): independently run `sync_knowledge` against the real `./knowledge` (assert 11 lessons, LES-007 open, idempotent re-sync), hit the read API via TestClient, run `build_digest` and confirm the open-lesson surfaces, and re-run the alembic no-drift probe after `0004`. Level 3: CI (api-tests + compose-smoke applies `0004` on Postgres). Merge under the Manual Merge Gate.

## Learning / Feedback Loop

This package **consumes LES-007** indirectly (it builds the machine surface for open lessons) but does not close it (LES-007 is doc-staleness, AOS-20). Record a lesson only on a guardian BLOCK / CI failure / self-found defect. Candidate if it holds: "a derived DB read-projection of a repo-authoritative artifact must be re-syncable and never the source of truth (RFC-0004 repo-travels constraint)."

## Suggested Delegation

Runtime Agent (Opus): config + migration `0004` (sqlite batch alter) + `knowledge.py` parser/sync + read API + digest rule 5 + tests. Orchestrator (Opus 4.8): this spec; independent `sync_knowledge` + read-API + digest + no-drift re-verification; guardian; PR; Manual Merge Gate.

## Board Linkage

- Plane: **AOS-23** (In Progress — 23a backend; 23b dashboard = AOS-KNOW-003).
- Branch: `claude/aos-runtime-002-scanner-1egyjw` (env-pinned). RFCs implemented: RFC-0002 (read surface), RFC-0004 (lesson read path).
