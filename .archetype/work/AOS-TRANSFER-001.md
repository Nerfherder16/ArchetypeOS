# AOS-TRANSFER-001 — RFC-0009 MVP: Knowledge Transfer Engine (portfolio reuse recommendations)

## Status

In Progress

## Origin

Operator direction: "lets do the knowledge transfer engine." RFC-0009 (`docs/rfc/RFC-0009-...`) is the design. This is the founding vision's other half: *"output what's useful **for** the repo you're searching against."* RFC-0008 (PRs #61/#62) produced the distilled portfolio knowledge; this engine **retrieves** the relevant, reusable parts of it for a target **need** and returns ranked, provenance-tagged reuse recommendations (advisory — feeds the Decision loop).

## Verified Baseline (the corpus — read carefully)

- The distilled content is **not** stored as `KnowledgePage` columns. `KnowledgePage` (`page_type="repository"`) has only `title`/`vault_path`/`source_refs`/`checksum`. The distillation (AOS-DISTILL-001) put the **summary into `RepositoryDNA.purpose`**, and the technologies live in DNA (`language_mix` keys, `package_managers`, `frameworks`). The full distilled markdown (useful_for/components) lives in the **vault file** (`wiki/repositories/<slug>.md`).
- Therefore the **scorable corpus is DB-native and hermetic**: for each repository that has a distillation, score the target `need` against `KnowledgePage.title` + `RepositoryDNA.purpose` (the distilled summary) + DNA technologies (`language_mix` keys + `package_managers` + `frameworks`). Cite the `KnowledgePage.vault_path` + repo id as evidence. (Reading the vault file for `useful_for` is out-of-scope for the MVP — keep it DB-only.)
- `RepositoryDNA` joins to `Repository` via `repository_id`; `Repository.project_id` gives the owning project (for `exclude_project_id`). `KnowledgePage.source_refs` carries `{"type":"repository","id":...}` linking a repository page to its repo.
- `docs/KNOWLEDGE_TRANSFER_ENGINE.md` specifies the recommendation format (source repo, reusable asset, reason, evidence, required changes, risks, confidence). The `Recommendation` model exists but the MVP does **not** persist (compute-and-return).

## In-Scope Files

- **`packages/aos_core/aos_core/services/transfer.py`** (new):
  - `_STOPWORDS` (a small set) + `_tokenize(text) -> set[str]` (lowercase, split on non-alphanumeric, drop stopwords + length<3).
  - `_candidate_text_and_tech(db, repo_page) -> (text, tech_terms)` — assemble the candidate's scorable text (`page.title` + the repo's `RepositoryDNA.purpose`) and its technology term set (`language_mix` keys + `package_managers` + `frameworks`), resolving the repo via `source_refs`/`project_id`. Tolerant of a missing DNA.
  - `score_relevance(need_tokens, cand_tokens, tech_tokens) -> (score, matched_terms)` — normalized overlap: `|need ∩ cand| / |need ∪ cand|`-style Jaccard, plus a boost for `need ∩ tech` (technology matches count extra). Returns the score (0..1) and the sorted matched terms (provenance for `reason`). Deterministic.
  - `recommend_reuse(db, *, need, exclude_project_id=None, limit=5) -> list[dict]` — gather all `KnowledgePage` with `page_type="repository"`; for each, build candidate text/tech, score against `_tokenize(need)`; **drop zero-score and any whose repo belongs to `exclude_project_id`**; sort by score desc (stable tiebreak by title); take `limit`. Each result: `{"source_repository": <name>, "source_project_id": ..., "reusable_asset": <repo/distillation>, "reason": <matched terms joined>, "matched_terms": [...], "evidence": [{"type":"distillation","ref":vault_path}, {"type":"repository","id":repo_id}], "required_changes": <heuristic>, "risks": <heuristic>, "confidence": round(score,4)}`. Tolerant: empty portfolio / empty need / no matches → `[]`, never raises.
- **`apps/api/app/routes/`** — add `POST /projects/{project_id}/transfer` (in `repositories.py` or a small new `transfer.py` route module registered in `routes/__init__.py`'s include loop) → `list[TransferRecommendationRead]`. Body `TransferRequest{need: str}`. 404 the project; call `recommend_reuse(db, need=payload.need, exclude_project_id=project_id)`. Register the route in `test_route_inventory.py` (freeze +1).
- **`apps/api/app/schemas.py`** — `TransferRequest{need: str}` and `TransferRecommendationRead{source_repository, source_project_id: str|None, reusable_asset, reason, matched_terms: list, evidence: list, required_changes: str|None, risks: str|None, confidence: float}`.
- **`apps/api/tests/test_transfer.py`** (new): seed 2–3 projects/repos each with a distillation (`KnowledgePage` `page_type="repository"` + `RepositoryDNA.purpose`/technologies); a `need` mentioning one repo's tech/purpose ranks that repo first with matched-term provenance; the target project's own repo is excluded; empty portfolio / empty need → `[]`; zero-overlap need → `[]`. Hermetic (sqlite).
- **Docs**: `docs/CAPABILITY_MAP.md` (Layer 4 — Knowledge Transfer Engine now has an MVP), `docs/rfc/RFC-0009-...` (status → MVP landed), `.archetype/work/AOS-TRANSFER-001.md`, state docs.

## Out-of-Scope (per RFC-0009 non-goals)

- Embeddings/semantic relevance; provider-reasoned adaptation plans; benchmarks/module-catalog inputs; auto-persistence/auto-approval; a target *repo* as a first-class query; a UI. No new DB table / migration / frontend.

## Acceptance Criteria

- A target `need` returns **ranked** reuse recommendations from the portfolio's distilled repos, top entries sharing the need's technologies/purpose, each citing the **source distillation** (`vault_path`) — with the target project's own repos excluded.
- Deterministic + hermetic; tolerant of empty portfolio / empty need / no matches; no new table/migration/frontend.
- api + worker green (CI-scope venv); ruff full CI scope + compileall clean; guardian PASS.

## Verification (Orchestrator, independent — builder ≠ verifier)

Seed a small portfolio, query several needs, and assert ranking + matched-term provenance + own-repo exclusion + the empty/zero-overlap tolerances; confirm no new table/migration/frontend; ruff full CI scope + compileall; guardian. Bonus: with the real distilled `free-llm`/`pydantic-ai`/etc. from `repositories/`, query "LLM provider abstraction" and eyeball a sensible ranking.
