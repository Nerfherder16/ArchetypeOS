# AOS-EMBED-001 — Embedding Relevance Tier, Part 1: vector store + semantic retrieval infra (no torch)

## Status

In Progress

## Origin

RFC-0010 (merged, PR #69) — the RFC-0009 embeddings increment. Operator-chosen mature target: sentence-transformers (torch) + pgvector. Per the "design to the mature-state target" rule this is delivered as two permanent subsets: **Part 1 (this) = the vector-store + retrieval infra, fully hermetic/CI-gated, NO torch**; Part 2 (AOS-EMBED-002) = the real `SentenceTransformerEmbedder` torch tier + live validation. Splitting keeps torch entirely off the CI path while still CI-gating the whole pgvector SQL/retrieval/calibration path (via synthetic vectors + a fake embedder).

## Verified Baseline (confirmed by inspection)

- `packages/aos_core/aos_core/llm/__init__.py` is the provider-seam pattern to mirror (Protocol + `get_provider(settings)` + `DeterministicProvider`/`ClaudeCodeProvider`, `.name` gating).
- `packages/aos_core/aos_core/services/transfer.py`: `score_relevance` = need coverage (LES-023); `recommend_reuse(db, *, need, exclude_project_id=None, limit=5)` sorts by coverage; `_candidate(db, page)` yields the candidate text/tech.
- `packages/aos_core/aos_core/services/distillation.py`: `distill_repository` computes the distilled text (title + `purpose` + technologies) and upserts the repository `KnowledgePage`.
- `packages/aos_core/aos_core/models.py:184` `KnowledgePage` (AuditMixin, Base) — where the embedding column goes.
- Alembic head = `apps/api/alembic/versions/0004_knowledge_page_nullable_project.py`; migrations are Postgres-path; CI/dev sqlite uses `Base.metadata.create_all`.
- `docker-compose.yml` postgres = `postgres:16-alpine`. `apps/api/requirements.txt` + `apps/worker/requirements.txt` pin deps (psycopg[binary] already present). `.github/workflows/ci.yml` jobs: PR Guardian / API tests / Worker tests / Web build / Web e2e / Docker Compose smoke.

## In-Scope Files

- **`packages/aos_core/aos_core/embeddings/__init__.py`** (new) — the seam, mirroring `llm/`:
  - `EmbeddingProvider` Protocol: `name: str`, `dim: int`, `embed(text: str) -> list[float] | None`.
  - `DeterministicEmbedder` (`name="deterministic"`, `dim=384`): `embed()` returns `None` (no embedding → lexical fallback). NO torch, no model. This is the only concrete embedder in Part 1.
  - `get_embedder(settings) -> EmbeddingProvider` resolving `settings.embedding_provider` (default `"deterministic"`). Real `sentence-transformers` tier is AOS-EMBED-002 — leave a clear seam + a `raise`/deterministic-fallback for unknown names, do NOT import torch anywhere here.
- **`packages/aos_core/aos_core/config.py`** — add `embedding_provider: str = "deterministic"` and `embedding_model: str = "all-MiniLM-L6-v2"` (used by Part 2). `EMBEDDING_DIM = 384` constant somewhere shared.
- **`packages/aos_core/aos_core/models.py`** — add a **nullable, dialect-variant** `embedding` column on `KnowledgePage`: a pgvector `Vector(384)` on postgresql, degrading on sqlite so `create_all` works and the column is simply unused there. Use `pgvector.sqlalchemy.Vector(384).with_variant(sa.JSON(), "sqlite")` (or an equivalent variant) — the model MUST import + `create_all` cleanly on sqlite. Nullable; default NULL.
- **`apps/api/requirements.txt` + `apps/worker/requirements.txt`** — add the lightweight **`pgvector`** python package (the SQLAlchemy type + psycopg adapter; NOT torch/sentence-transformers). Pin a version.
- **`apps/api/alembic/versions/0005_repository_embedding.py`** (new, down_revision `0004`) — `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`; add the `embedding vector(384)` column to the repository knowledge table (nullable); create a cosine index (ivfflat or hnsw, `vector_cosine_ops`). Downgrade drops index+column (leave the extension). Guard so it is a no-op / skipped on sqlite if the test harness ever runs it there (Postgres-only DDL).
- **`docker-compose.yml`** — postgres image `postgres:16-alpine` → `pgvector/pgvector:pg16` (same env/volumes; the extension ships in the image). Verify compose config still validates.
- **`packages/aos_core/aos_core/services/distillation.py`** — in `distill_repository`, after the distilled text is known, call `get_embedder(get_settings()).embed(text)`; when non-None, store it on the `KnowledgePage.embedding` (both insert + update branches). Deterministic → None → column stays NULL (hermetic; unchanged behaviour). Re-syncable. Accept an optional `embedder=None` param (defaults to the resolver) for test injection, mirroring `provider=None`.
- **`packages/aos_core/aos_core/services/transfer.py`** — add the semantic path to `recommend_reuse`:
  - Add an optional `embedder=None` param (defaults to `get_embedder(get_settings())`).
  - Semantic path is taken only when: the embedder returns a non-None vector for the `need` AND the DB dialect is `postgresql` AND the extension/column is usable. Then order candidates by `embedding <=> need_vec` (cosine distance) for those with a non-NULL embedding, and compute a **calibrated, coverage-like confidence** = a blend of the (1 - cosine_distance) semantic similarity and the existing lexical need-coverage (e.g. `max(coverage, calibrated_semantic)` or a documented weighted blend), keeping the lexical `matched_terms` as provenance. Candidates without an embedding fall back to their lexical coverage. Never emit a raw cosine as confidence (LES-023).
  - Otherwise (deterministic embedder / sqlite / no vectors) → **exactly today's lexical Layer-0** behaviour, unchanged.
  - Keep the public return shape + schema identical; keep zero-score drop, `exclude_project_id`, `limit`, tolerant `[]`.
- **Tests:**
  - **`apps/api/tests/test_embeddings.py`** (new, hermetic sqlite): the seam (deterministic embedder → `embed()` is None, `name`/`dim`); `distill_repository` with the deterministic embedder leaves `embedding` NULL and behaves exactly as before; `recommend_reuse` with the deterministic embedder is byte-identical to the lexical path; a fake embedder returning a vector but on sqlite still falls back to lexical (dialect gate). No torch, no Postgres.
  - **`apps/api/tests/test_pgvector_store.py`** (new, **Postgres-gated** — `pytest.mark.pgvector`, skipped unless `AOS_TEST_DATABASE_URL`/postgres dialect): create the schema (run the migration or create_all-then-DDL), seed 2–3 repository `KnowledgePage`s with **synthetic** embeddings + a **fake embedder** (deterministic synthetic vectors — NO torch), and assert: the `<=>` ordering ranks the semantically-closest repo first; a **lexical-miss / semantic-hit** case surfaces a repo the lexical floor would drop; the reported confidence is calibrated (0..1, not a raw cosine) with lexical `matched_terms` intact.
- **`.github/workflows/ci.yml`** — a new job **"Vector store tests"**: `services: postgres: image: pgvector/pgvector:pg16` (health-checked), install api deps + `pgvector` (NOT torch), set `AOS_TEST_DATABASE_URL` to the service, run `pytest -m pgvector`. This gates the pgvector path in CI without torch.
- **Docs/lessons**: `docs/CAPABILITY_MAP.md` (transfer entry → embedding infra shipped, real embedder pending Part 2), `.archetype/work/AOS-EMBED-001.md`. Record a lesson only if a defect is self-found. Do NOT touch state docs (Orchestrator owns them).

## Out-of-Scope (Part 2 / later)

- `SentenceTransformerEmbedder` + torch/sentence-transformers dependency (optional extras, lazy import) + generate-on-distill with real vectors + Orchestrator live validation — **AOS-EMBED-002**.
- Embedding lessons/decisions; a Control Tower "Reuse" view; a target-repo query; ANN index tuning.

## Acceptance Criteria

- Hermetic sqlite suite unchanged in behaviour: deterministic embedder → `embedding` NULL, `recommend_reuse` byte-identical to today's lexical coverage; the model imports + `create_all`s cleanly on sqlite (dialect-variant column). api + worker sqlite suites green; ruff full CI scope + compileall clean; guardian PASS. **No torch anywhere in the CI dependency install.**
- The new Postgres-gated CI job passes: with synthetic vectors + a fake embedder on real Postgres+pgvector, semantic `recommend_reuse` ranks by `<=>`, surfaces a lexical-miss/semantic-hit, and reports a calibrated (non-raw-cosine) confidence with lexical provenance.
- Migration applies on Postgres (extension + nullable vector column + cosine index); compose config validates with the pgvector image; no frontend change.

## Verification (Orchestrator, independent — builder ≠ verifier)

Run the hermetic sqlite suites + confirm `recommend_reuse` with the deterministic embedder is identical to the pre-change lexical behaviour (the reality-test gate: kubernetes #1 "container orchestration", gin #1 "HTTP routing" still hold, deterministic). Confirm no torch in the CI installs; ruff full CI scope + compileall; guardian. Babysit CI for the new Postgres-service job (it exercises the pgvector path). Note: the real-embedder quality (torch) is validated in Part 2 (AOS-EMBED-002).
