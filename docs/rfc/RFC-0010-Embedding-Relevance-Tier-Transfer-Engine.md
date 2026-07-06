# RFC-0010 — Embedding Relevance Tier for the Knowledge Transfer Engine

## Status

Proposed (operator-directed 2026-07-06: "lets kick off rfc-0009" → the embeddings increment). Builds on RFC-0009 (the Transfer Engine, whose `score_relevance` seam this extends) and RFC-0008 (the distilled knowledge being embedded). Operator decisions locked (see Design): **sentence-transformers (torch)** for the embedder, **pgvector** for storage.

## Summary

RFC-0009 shipped the Transfer Engine with a **deterministic lexical** relevance floor (need coverage — LES-023): the correct repo ranks #1 on every tested query, but the score is purely lexical, so it misses **paraphrase and synonymy**. Today "message queue" does not match `example-voting-app` even though its reasoned purpose says "Redis **queue**"; "pub/sub" would not match "message broker"; "container scheduling" only partially matches "orchestration". This RFC adds a **semantic relevance tier** — sentence embeddings + vector similarity — behind the same `score_relevance` seam, so the engine retrieves on meaning, not just shared tokens.

This is the **mature-state target** for transfer relevance chosen deliberately over a lighter MVP (fastembed/in-Python cosine) per the operator "design to the mature-state target — why build things twice?" rule: build the durable architecture (torch + pgvector) once rather than ship a lightweight version and migrate later.

## Problem

- The lexical floor scores by token overlap. Real reuse questions are semantic ("I need a background job runner" should surface a repo whose purpose says "Redis queue / worker"). Lexical retrieval cannot bridge vocabulary gaps.
- The distilled corpus (reasoned `DNA.purpose` + technologies) is exactly the kind of short, meaning-dense text embeddings excel at — but nothing embeds it or searches it semantically.

## Mature-state target (transfer relevance, in layers)

- **Layer 0 — lexical need-coverage** (shipped, PR #66). The hermetic/offline floor: no deps, CI-safe, calibrated confidence. Permanent fallback.
- **Layer 1 — semantic relevance via embeddings** (this RFC). A local-first embedding of each repo's distilled knowledge + vector similarity search, blended with Layer 0, reported as a calibrated (not raw-cosine) confidence.
- Both layers sit behind `score_relevance` / `recommend_reuse`; callers and the public API/schema are unchanged.

## Goals

- A **two-tier `EmbeddingProvider` seam** (the pattern already ratified for the LLM provider and the distillation reasoned tier):
  - `DeterministicEmbedder` — the default. Returns no embedding (or a zero/None sentinel) → the engine falls back to Layer-0 lexical coverage. **torch is never imported on this path.** CI and offline/no-model nodes use this; fully hermetic.
  - `SentenceTransformerEmbedder` — the real tier. `sentence-transformers` + `all-MiniLM-L6-v2` (384-dim), local and offline after the first model fetch. Activates only when explicitly configured on a capable node.
- **pgvector storage**: a `vector(384)` column on the repository `KnowledgePage` (or a dedicated `repository_embedding` table), populated during `distill_repository`, with a cosine index (HNSW or ivfflat). Retrieval uses pgvector's `<=>` operator.
- **Semantic `recommend_reuse`**: when embeddings + pgvector are available, rank candidates by vector similarity to the embedded `need`; **blend** with the lexical layer and report a **calibrated, coverage-like confidence** (never a raw cosine — LES-023), keeping the lexical matched terms as provenance. When unavailable (deterministic embedder, or a non-pgvector DB), degrade transparently to Layer-0 coverage. Same public API (`POST /projects/{id}/transfer`) and read schema.

## Non-goals (deferred)

- Embedding anything beyond repository distillations (lessons/decisions/code-chunks) — later.
- Re-ranking with a cross-encoder, query expansion, or an isolated-`claude_code` adaptation-plan pass (RFC-0009 next-steps).
- Approximate-index tuning beyond a sane default; multi-model / dimension configurability.
- A target-*repo* query and the Control Tower "Reuse" view (separate RFC-0009 increments).

## Design

- **`packages/aos_core/aos_core/embeddings/`** (new) — an `EmbeddingProvider` protocol + `get_embedder(settings)` resolver (mirroring `llm/`): `DeterministicEmbedder` (name `"deterministic"`, returns `None`) and `SentenceTransformerEmbedder` (lazy-imports torch/sentence-transformers so the module is importable without them). `settings.embedding_provider` (default `"deterministic"`) + model name.
- **Storage / migration** — Postgres image → `pgvector/pgvector:pg16` (or install the extension); an Alembic migration: `CREATE EXTENSION IF NOT EXISTS vector`, add `embedding vector(384)` + a cosine index, on the repository knowledge row. The column is **nullable** (sqlite/CI and un-embedded repos have `NULL`).
- **Generation** — `distill_repository` computes the embedding of the distilled text (title + reasoned/floor `purpose` + technologies) via the resolved embedder and stores it; `None` (deterministic/CI) leaves the column `NULL`. Re-syncable (a re-distill re-embeds).
- **Retrieval** — `recommend_reuse` embeds the `need`; if the embedder is real AND the DB supports vector search AND candidates have embeddings, order by `embedding <=> need_vec` and compute a calibrated confidence = a coverage-like blend of semantic similarity and lexical coverage; else Layer-0. A capability probe (dialect == postgresql + extension present) picks the path; **no hard dependency on Postgres at import time**.
- **Confidence calibration** — map cosine similarity into a bounded, interpretable score and combine with lexical coverage (e.g. `max(coverage, calibrated_semantic)` or a weighted blend) so the reported number stays honest (LES-023). Exact blend fixed in the build spec + validated on the real portfolio.

## Hermetic strategy & verification (important — a consequence of the pgvector choice)

- CI unit tests run on **sqlite**, which has no `vector` type / `<=>`. So the sqlite suite exercises the **deterministic embedder → Layer-0 lexical fallback** (hermetic, torch never imported). The **real torch + pgvector path is not reachable from the sqlite suite.**
- To avoid a live-only untested critical path, the build package **adds a Postgres-backed test** for the vector path — a pytest module gated on a Postgres service (a GitHub Actions `postgres`/`pgvector` service container, or the existing compose Postgres) that migrates, stores a couple of vectors, and asserts the `<=>` ordering + fallback. This is the operator-open question below; the recommendation is to add it (mature target ⇒ no live-only path).
- The Orchestrator additionally **live-validates** the real path end-to-end (the `--provider`-style reality test with a real embedder over the 6-repo portfolio), showing a paraphrase match the lexical floor misses (e.g. "message queue" → `example-voting-app`, "pub/sub" / "background job runner" → a queue/worker repo).

## Operator-open question

The pgvector path cannot run in the sqlite unit suite. Recommendation: **add a Postgres-service CI test** so the vector path is gated in CI (not live-validation only) — consistent with choosing the mature target. Alternative: live-validation only (lighter CI, but a CI-untested critical path). To be confirmed before the build package is speced.

## Alternatives considered

- **fastembed (ONNX) + in-Python cosine (rejected by the operator for the MVP):** lighter (no torch, no DB extension) and hermetic-testable on sqlite, but a smaller, less flexible model path and an in-Python store that would be migrated to pgvector at scale — i.e. "building twice." The operator chose the mature target directly.
- **Cloud embeddings API (rejected):** lightest local footprint but breaks the local-first principle (network + API key per scan).
- **Raw cosine as the reported confidence (rejected):** uninterpretable in a UI; LES-023 requires a calibrated, coverage-like number.

## Acceptance criteria (for the build package, AOS-EMBED-001)

- The `EmbeddingProvider` seam ships with a hermetic `DeterministicEmbedder` default (torch never imported on the CI path); `recommend_reuse` degrades transparently to Layer-0 when embeddings/pgvector are absent — proven on the sqlite suite (unchanged lexical behaviour + calibrated confidence).
- On a real Postgres+pgvector node with the real embedder, semantic retrieval surfaces a **paraphrase match the lexical floor misses** on the real 6-repo portfolio, with a calibrated (non-raw-cosine) confidence and lexical matched-term provenance intact.
- Migration applies cleanly (extension + nullable vector column + index); the compose Postgres image includes pgvector; api + worker sqlite suites green; ruff + compileall clean; guardian PASS.

## Dependencies

- RFC-0009 (the Transfer Engine + the `score_relevance` seam) — landed (PRs #63/#66).
- RFC-0008 (the distilled knowledge being embedded) — landed.
- Alembic (AOS-ALEMBIC-001) for the migration; the compose Postgres image gains pgvector.
- New runtime deps on capable nodes: `sentence-transformers` (torch) — lazy-imported, deterministic default keeps CI/lightweight nodes free of it.

## Next steps

1. Resolve the operator-open verification question (Postgres CI test vs live-only).
2. `AOS-EMBED-001` — the vertical slice: seam + migration/image + generate-on-distill + semantic `recommend_reuse` with lexical fallback + calibrated confidence; hermetic seam/fallback tests + (recommended) a Postgres vector-path test; Orchestrator live validation on the portfolio.
3. Follow-ups: embed lessons/decisions; the Control Tower "Reuse" view (now unblocked); a target-repo query.
