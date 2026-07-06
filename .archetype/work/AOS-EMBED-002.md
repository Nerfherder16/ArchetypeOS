# AOS-EMBED-002 — Embedding Relevance Tier, Part 2: the real sentence-transformers (torch) embedder

## Status

In Progress

## Origin

RFC-0010 (merged, PR #69), Part 2. Part 1 (AOS-EMBED-001, PR #70) shipped the whole vector-store + semantic-retrieval infra **without torch**: the `EmbeddingProvider` seam (deterministic default → lexical fallback), the pgvector column + migration + `pgvector/pgvector` image, semantic `recommend_reuse` (calibrated, lexical fallback), and a Postgres-service CI job that proved the `<=>` path with synthetic vectors. This package fills the seam with the **real embedder** so genuine vectors flow — the piece that actually lands torch in the runtime. Per "design to the mature-state target", torch is confined to this package and kept **off the CI unit path** (Part 1's whole point): CI tests the wiring with a mocked model; real embedder quality is Orchestrator-live-validated.

## Verified Baseline (confirmed by inspection)

- `packages/aos_core/aos_core/embeddings/__init__.py` — `EmbeddingProvider` Protocol (`name`, `dim`, `embed(text)->list[float]|None`), `DeterministicEmbedder`, and `get_embedder(settings)` which raises on unknown names with an explicit seam comment: *"if name == 'sentence_transformers': from ._sentence_transformers import SentenceTransformerEmbedder (lazy torch)"*. **No torch is imported here — must stay that way** (lazy import lives in the new submodule).
- `packages/aos_core/aos_core/config.py` — `EMBEDDING_DIM = 384`, `embedding_provider: str = "deterministic"`, `embedding_model: str = "all-MiniLM-L6-v2"`.
- `distill_repository` already calls `embedder.embed(text)` and stores a non-None vector on `KnowledgePage.embedding`; `recommend_reuse` already takes the semantic path when the embedder returns a non-None `need` vector on Postgres. So **wiring the real embedder is the only new behaviour needed** — no changes to distillation/transfer logic.
- `docker-compose.yml` postgres = `pgvector/pgvector:pg16`; api/worker services build from their Dockerfiles. CI keeps torch out of the api/worker dependency installs (Part 1 invariant).

## In-Scope Files

- **`packages/aos_core/aos_core/embeddings/_sentence_transformers.py`** (new) — `SentenceTransformerEmbedder`:
  - `name = "sentence_transformers"`, `dim = EMBEDDING_DIM`.
  - **Lazy torch**: `import sentence_transformers` happens inside the module's load path, not at package import. A module-level **singleton** caches the loaded `SentenceTransformer(settings.embedding_model)` so it loads once (loading is expensive).
  - `embed(text) -> list[float] | None`: `None`/empty text → `None`; else `model.encode(text, normalize_embeddings=True)` → a plain `list[float]` of length `dim`. Normalized (unit-length) so cosine is clean. A per-call encode failure is caught → `None` (one bad input never breaks distillation); a **load/import failure raises** a clear error (a node configured for the real tier but missing the dep is a misconfiguration, not a silent degrade).
  - Accept the model name via the passed settings (constructor takes `model_name`), defaulting to `settings.embedding_model`.
- **`packages/aos_core/aos_core/embeddings/__init__.py`** — wire the seam: in `get_embedder`, `if name == "sentence_transformers": from ._sentence_transformers import SentenceTransformerEmbedder; return SentenceTransformerEmbedder(settings)`. Keep the top-of-module torch-free (the import stays inside the branch). Add `SentenceTransformerEmbedder` to `__all__` via a lazy re-export note (do NOT import it at module top).
- **`apps/api/requirements-embeddings.txt`** + **`apps/worker/requirements-embeddings.txt`** (new) — pin `sentence-transformers` (and let it pull torch). **NOT added to `requirements.txt`** — CI unit jobs must stay torch-free.
- **`apps/api/Dockerfile`** + **`apps/worker/Dockerfile`** — a build ARG `INSTALL_EMBEDDINGS` (default `false`). When `true`: `pip install -r requirements-embeddings.txt` **and pre-download the model** during build (`RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`) so runtime is offline. When `false` (default): unchanged, torch-free — so **compose-smoke CI stays fast/light** (it builds the default). Document enabling the real tier (build with `--build-arg INSTALL_EMBEDDINGS=true` + set `EMBEDDING_PROVIDER=sentence_transformers`).
- **`docker-compose.yml`** — leave the default build torch-free (deterministic). Add a commented/documented path (build arg + `EMBEDDING_PROVIDER=sentence_transformers` env on api+worker) for enabling the real tier on a capable node. Do NOT flip the default (keeps compose-smoke light). Confirm `docker compose config` still validates.
- **`apps/api/tests/test_embeddings.py`** — extend (hermetic, NO real torch): monkeypatch a **fake `sentence_transformers` module** (a fake `SentenceTransformer` whose `.encode` returns a canned 384-length normalized array) → assert `SentenceTransformerEmbedder.embed` returns that list, returns `None` on empty text, loads the model once (singleton), and that `get_embedder(settings with embedding_provider="sentence_transformers")` returns it. Assert importing `aos_core.embeddings` does NOT import torch/sentence_transformers (the top-level stays lazy). No torch in CI.
- **`docs/CAPABILITY_MAP.md`** — the embedding tier is now complete: real `sentence-transformers` embedder wired behind the seam; deterministic default keeps CI/light nodes torch-free. Do NOT touch state docs (Orchestrator owns them).
- **Lessons** — record one only if a defect is self-found during build/verification.

## Out-of-Scope (later)

- Embedding lessons/decisions/code-chunks; a Control Tower "Reuse" view; a target-repo query; ANN index/model tuning; a torch-in-CI job (deliberately omitted — the mocked wiring test + Orchestrator live validation cover it while keeping CI fast).

## Acceptance Criteria

- `aos_core.embeddings` still imports **without torch** (verified by a test asserting `sentence_transformers` is not in `sys.modules` after import); the deterministic default path is unchanged; CI unit jobs remain torch-free. `get_embedder` resolves the real embedder for `embedding_provider="sentence_transformers"`; `SentenceTransformerEmbedder.embed` (mocked model) returns a `dim`-length list, `None` on empty, loads once.
- Dockerfiles build torch-free by default (`INSTALL_EMBEDDINGS=false`) and install + pre-download the model when `true`; `docker compose config` validates; compose-smoke unaffected.
- api + worker sqlite suites green; ruff full CI scope + compileall clean; guardian PASS.

## Verification (Orchestrator, independent — builder ≠ verifier)

- Hermetic: run the suites; confirm the mocked-embedder wiring tests + the "no torch on import" assertion; confirm the deterministic reality-harness gate is unchanged (kubernetes #1 "container orchestration", gin #1 "HTTP routing"); ruff + compileall; `docker compose config`; guardian.
- **Live embedder-quality validation (the point of Part 2):** install `sentence-transformers` in the venv, embed the 6 distilled repos' text + a set of **paraphrase** needs, compute cosine in Python (numpy — no Postgres needed; the pgvector `<=>` path is already CI-proven in Part 1), and show the semantic tier surfaces a match the lexical floor **misses** — e.g. "message queue" / "background job runner" → `example-voting-app` (whose purpose says "Redis queue"), "deploy containers across machines" → `kubernetes`. Report the ranking + that it beats the lexical-only result.
