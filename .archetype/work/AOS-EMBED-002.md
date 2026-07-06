# AOS-EMBED-002 — Embedding Relevance Tier, Part 2: the real embedder (fastembed / ONNX)

## Status

In Progress

## Origin

RFC-0010 (merged, PR #69), Part 2. Part 1 (AOS-EMBED-001, PR #70) shipped the whole vector-store + semantic-retrieval infra **without a real embedder**: the `EmbeddingProvider` seam (deterministic default → lexical fallback), the pgvector column + migration + `pgvector/pgvector` image, semantic `recommend_reuse` (calibrated, lexical fallback), and a Postgres-service CI job. This package fills the seam with the **real embedder** so genuine vectors flow.

**Design change from the RFC's initial embedder choice (operator-approved 2026-07-06):** use **fastembed (ONNX runtime)** instead of `sentence-transformers` (torch). Same model (`all-MiniLM-L6-v2`, 384-dim, drop-in for the existing pgvector column), same semantic quality, but ~50 MB (onnxruntime) instead of GBs (torch) — the right footprint for a local-first box. torch buys training/GPU we don't do; we do inference on short text. fastembed being light also **enables a real (non-mocked) embedder CI test**, closing the gap torch would have forced us to wave away. The `EmbeddingProvider` seam is embedder-agnostic, so nothing else changes. pgvector storage (shipped in Part 1) stays.

## Verified Baseline (confirmed by inspection)

- `packages/aos_core/aos_core/embeddings/__init__.py` — `EmbeddingProvider` Protocol (`name`, `dim`, `embed(text)->list[float]|None`), `DeterministicEmbedder`, `get_embedder(settings)` which raises on unknown names with a seam comment for the real tier. **No heavy import at module top — keep it that way** (the fastembed import lives lazily in the new submodule).
- `packages/aos_core/aos_core/config.py` — `EMBEDDING_DIM = 384`, `embedding_provider: str = "deterministic"`, `embedding_model: str = "all-MiniLM-L6-v2"`.
- `distill_repository` already calls `embedder.embed(text)` and stores a non-None vector on `KnowledgePage.embedding`; `recommend_reuse` already runs the semantic path when the embedder returns a non-None `need` vector on Postgres. **Wiring the real embedder is the only new behaviour** — distillation/transfer logic is untouched.

## In-Scope Files

- **`packages/aos_core/aos_core/embeddings/_fastembed.py`** (new) — `FastEmbedEmbedder`:
  - `name = "fastembed"`, `dim = EMBEDDING_DIM`.
  - **Lazy import**: `from fastembed import TextEmbedding` happens inside the load path, never at package import. A module-level **singleton** caches the loaded `TextEmbedding(model_name)` (loading/model init is expensive; do it once).
  - `embed(text) -> list[float] | None`: empty/whitespace → `None`; else `list(model.embed([text]))[0]` → a plain `list[float]` of length `dim`, **L2-normalized** (unit vector, so cosine is clean and matches pgvector `vector_cosine_ops`). A per-call embed failure is caught → `None` (one bad input never breaks distillation); a **load/import failure raises** a clear, actionable error (a node set to the real tier without fastembed installed is a misconfiguration, not a silent degrade).
  - Constructor takes `model_name` (default `settings.embedding_model`); use a fastembed-supported 384-dim identifier for `all-MiniLM-L6-v2` (e.g. `"sentence-transformers/all-MiniLM-L6-v2"`; if that id isn't in fastembed's supported set, use fastembed's equivalent 384-dim MiniLM/BGE-small id and set `embedding_model` to match — keep `dim = 384`).
- **`packages/aos_core/aos_core/embeddings/__init__.py`** — wire the seam: in `get_embedder`, `if name == "fastembed": from ._fastembed import FastEmbedEmbedder; return FastEmbedEmbedder(settings)`. Keep the top-of-module import-light (no fastembed at module top). Note the lazy re-export in `__all__`/docstring; do NOT import `_fastembed` eagerly.
- **`apps/api/requirements-embeddings.txt`** + **`apps/worker/requirements-embeddings.txt`** (new) — pin `fastembed` (pulls onnxruntime, light). **NOT added to `requirements.txt`** — the unit CI jobs stay dependency-minimal and the deterministic default stays genuinely dependency-free.
- **`apps/api/Dockerfile`** + **`apps/worker/Dockerfile`** — install `requirements-embeddings.txt` (fastembed is light enough to install unconditionally — no build-arg gymnastics). Optionally **pre-download the model** during build (a `RUN python -c "from fastembed import TextEmbedding; TextEmbedding('<model>')"`) so runtime is offline; gate the pre-download behind a build ARG `PREDOWNLOAD_EMBEDDING_MODEL` (default `false`) so **compose-smoke build stays fast** (no model fetch), while a real offline node builds with it `true`. Enabling the real tier at runtime = set `EMBEDDING_PROVIDER=fastembed`.
- **`docker-compose.yml`** — keep `EMBEDDING_PROVIDER` default `deterministic` (so compose-smoke exercises the light, torch-free, model-free path). Document (comment / env example) enabling the real tier: `EMBEDDING_PROVIDER=fastembed` on api+worker (+ the pre-download build arg for offline). Do NOT flip the default. Confirm `docker compose config` validates.
- **Tests:**
  - **`apps/api/tests/test_embeddings.py`** (extend, hermetic, no fastembed needed): monkeypatch a **fake fastembed** (`TextEmbedding` whose `.embed` yields a canned 384-vector) → assert `FastEmbedEmbedder.embed` returns the normalized list, `None` on empty, loads the model once (singleton); `get_embedder(settings with embedding_provider="fastembed")` returns it; and **importing `aos_core.embeddings` imports no fastembed/onnxruntime** (assert not in `sys.modules`). Torch-free, fastembed-free CI unit path.
  - **`apps/api/tests/test_fastembed_real.py`** (new, `pytest.mark.embedder`, skipped unless fastembed is importable): with **real fastembed**, assert `embed("...")` returns a 384-length unit vector, and that two paraphrase texts are closer (higher cosine) than an unrelated pair — a real semantic sanity check. Register the `embedder` marker.
- **`.github/workflows/ci.yml`** — a new light job **"Embedder tests"**: install api deps + `requirements-embeddings.txt` (fastembed — no torch), run `pytest -m embedder`. Cache the fastembed model dir (`actions/cache` on the HF/fastembed cache path) so the ~90 MB model isn't re-downloaded every run (nice-to-have; acceptable to download if caching is awkward). This gives a **real embedder CI gate** (affordable because fastembed is light).
- **`docs/CAPABILITY_MAP.md`** — the embedding tier is complete: real fastembed (ONNX) embedder behind the seam; deterministic default keeps CI/light nodes dependency-free; pgvector storage from Part 1. Do NOT touch state docs (Orchestrator owns them).
- **Lessons** — only if a defect is self-found.

## Out-of-Scope (later)

- Embedding lessons/decisions/code-chunks; a Control Tower "Reuse" view; a target-repo query; ANN/model tuning; any torch dependency (explicitly avoided).

## Acceptance Criteria

- `aos_core.embeddings` imports with **no fastembed/onnxruntime/torch** loaded (asserted); the deterministic default path + reality-harness lexical gate are unchanged; unit CI jobs stay dependency-minimal. `get_embedder("fastembed")` resolves `FastEmbedEmbedder`; `embed` (mocked model) returns a `dim`-length normalized list, `None` on empty, loads once.
- The new **"Embedder tests"** CI job passes with real fastembed: `embed` returns a 384-unit vector and paraphrases are closer than unrelated text.
- Dockerfiles build (fastembed installed; model pre-download gated off by default so compose-smoke stays fast); `docker compose config` validates; no frontend change; api + worker sqlite suites green; ruff full CI scope + compileall clean; guardian PASS.

## Verification (Orchestrator, independent — builder ≠ verifier)

- Hermetic: run the suites; confirm the mocked-embedder wiring + the "no heavy import on package import" assertion; confirm the deterministic reality-harness gate is unchanged (kubernetes #1 "container orchestration", gin #1 "HTTP routing"); ruff + compileall; `docker compose config`; guardian. Babysit the new "Embedder tests" CI job (real fastembed).
- **Live embedder-quality validation (the point of Part 2):** install `fastembed` in the venv, embed the 6 distilled repos' text + a set of **paraphrase** needs, compute cosine in Python (numpy — no Postgres needed; the pgvector `<=>` path is already CI-proven in Part 1), and show the semantic tier surfaces a match the lexical floor **misses** — e.g. "message queue" / "background job runner" → `example-voting-app` (purpose says "Redis queue"); "deploy containers across machines" → `kubernetes`. Report the ranking vs the lexical-only result.
