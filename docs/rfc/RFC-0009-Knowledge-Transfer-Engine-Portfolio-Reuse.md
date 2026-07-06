# RFC-0009 — Knowledge Transfer Engine: portfolio reuse recommendations (MVP)

## Status

MVP landed (AOS-TRANSFER-001) — operator-directed 2026-07-06: "lets do the knowledge transfer engine". Builds directly on RFC-0008 (the distilled knowledge this engine searches). The MVP described here shipped (`aos_core.services.transfer.recommend_reuse` + `POST /projects/{project_id}/transfer`); the richer relevance layers (embeddings, provider-reasoned adaptation plans) remain explicit non-goals, deferred behind the `score_relevance` seam.

## Summary

RFC-0008 answered *"feed a repo → extract what's useful → durable knowledge in the vault."* This RFC answers the **other half of the founding intent** the operator named: *"output what's useful **for** the intended repo you're searching against."* The **Knowledge Transfer Engine** (`docs/KNOWLEDGE_TRANSFER_ENGINE.md`) takes a **target need** and searches the **portfolio** of distilled knowledge for **relevant, reusable assets**, producing ranked, provenance-tagged **reuse recommendations** — *"AiGentOS already implemented a provider abstraction; before building one in CPA Connector, evaluate reusing it."* It is advisory (it recommends; a human decides — it feeds the Decision loop).

This is fundamentally a **relevance/retrieval** problem, distinct from the Council (judgment) and the Distillation Engine (extraction): given a target, *find* the portfolio knowledge that matters.

## Problem

The pieces now exist but nothing connects them for reuse:
- The scanner + Phase-B graph produce structural DNA; RFC-0008 produces **distilled repository knowledge** (`KnowledgePage` `page_type="repository"` — title/summary/technologies/useful_for/components, provenance-tagged) across the portfolio.
- But there is **no notion of a target need**, and **no retrieval** that answers "which of my prior repos is relevant to what I'm about to build?" The distilled knowledge sits inert; reuse is manual.

## Goals (MVP scope)

- A **`recommend_reuse(db, *, need, exclude_project_id=None, limit=5)`** service that, given a **free-text target need**, scores every repository distillation in the portfolio (its `KnowledgePage` + the repo's `RepositoryDNA` technologies) for **relevance** and returns ranked reuse recommendations.
- **Deterministic lexical relevance (the hermetic floor):** tokenize the need + each candidate's `title`/`summary`/`technologies`/`useful_for`; score by normalized term overlap (Jaccard-ish, with a light technology-match boost). No model, no network — CI-runnable and reproducible. (Embeddings are the deferred enhancement, same seam pattern as the Council/Distillation deterministic-vs-real split.)
- **Each recommendation carries the documented Decision Format** (`docs/KNOWLEDGE_TRANSFER_ENGINE.md`): source repository, reusable asset (the repo / its distilled components), reason (the **matched terms** — provenance), evidence (the source distillation's `vault_path` + repo id), risks / required changes (heuristic for the MVP), and a confidence = the relevance score.
- **Advisory + provenance-first:** the engine computes and returns recommendations (no auto-persist, no auto-action); every recommendation cites the source distillation. A human can turn a chosen one into a `Recommendation`/`Decision` (the existing loop). No claim without a source.
- **Exposed:** `POST /projects/{project_id}/transfer` (body `{need}`) → ranked reuse recommendations, excluding the target project's own repos.

## Non-goals (explicitly deferred)

- **Embeddings / semantic index** — the richer relevance layer (a local-first embedding store) is a follow-up; the MVP is lexical.
- **Provider-reasoned adaptation plans / estimated savings narrative** — an isolated-`claude_code` pass (RFC-0008/LES-021 seam) that writes the "required changes / migration risks / time saved" prose is deferred; the MVP emits structured heuristics.
- **Benchmarks / module-catalog / experiment inputs** — the MVP matches on repository distillations + DNA only.
- **Auto-persistence / auto-approval / duplicate-implementation detection at scale** — advisory compute-and-return only; no new DB table, no migration.
- **A target *repo* (vs. a text need) as the query** — the MVP takes a `need` string (which a caller can seed from a target repo's distilled summary); a first-class repo-to-repo target is a follow-up.

## Design

- New service `packages/aos_core/aos_core/services/transfer.py`:
  - `_tokenize(text) -> set[str]` (lowercase, stopword-stripped, alphanumeric).
  - `score_relevance(need_tokens, candidate) -> (score, matched_terms)` — normalized token overlap over the candidate's title/summary/useful_for + a boost when `need` terms hit the candidate's `technologies`. Deterministic.
  - `recommend_reuse(db, *, need, exclude_project_id=None, limit=5) -> list[dict]` — gather repository `KnowledgePage`s (+ join their repo DNA for technologies), score each, drop zero-score, sort desc, take `limit`; each result `{source_repository, source_project_id, reusable_asset, reason(matched terms), evidence:[{vault_path},{repo id}], required_changes, risks, confidence}`. Tolerant: empty portfolio / empty need → `[]`.
- `apps/api/app/routes/*`: `POST /projects/{project_id}/transfer` → a `TransferRecommendationRead` list (a Pydantic read model; **no DB table**). 404 the project; exclude its own repos by default.
- Hermetic tests: seed 2–3 distilled repos with differing technologies/summaries, query a need, assert the relevant one(s) rank first with matched-term provenance and the target's own repo is excluded.

## Alternatives considered

- **Embeddings-first (rejected for MVP):** better recall, but non-hermetic and heavier; the lexical floor is reproducible and ships now, with embeddings as a clean follow-up behind the same scoring seam.
- **LLM-judge relevance (rejected for MVP):** non-deterministic, and it's the Council's job to *judge* — Transfer's job is to *retrieve*; keep retrieval deterministic and auditable, let a human/Council judge the shortlist.
- **Auto-persist every match as a Recommendation (rejected):** clutter + implies action; compute-and-return keeps it advisory and side-effect-free.

## Acceptance criteria

- Given a portfolio of distilled repos and a target `need`, the engine returns **ranked** reuse recommendations whose top entries share the need's technologies/purpose, each citing the **source distillation** (provenance), excluding the target project's own repos.
- Deterministic + hermetic (no model/network); tolerant of an empty portfolio / empty need; no new table/migration; no frontend.
- api + worker green; ruff full CI scope + compileall clean; guardian PASS.

## Dependencies

- RFC-0008 (the repository distillations this searches) — landed (PRs #61/#62).
- `docs/KNOWLEDGE_TRANSFER_ENGINE.md` (the design + recommendation format this implements).
- The `Recommendation`/Decision loop (a human can promote a reuse recommendation) — landed (PR #55).

## Next steps (beyond the MVP)

1. Embeddings/semantic relevance (local-first) behind the `score_relevance` seam.
2. An isolated-`claude_code` adaptation-plan pass (required changes / estimated savings / risks prose, cited to source files).
3. A target *repo* as a first-class query (repo-to-repo transfer) + duplicate-implementation detection.
4. A Control Tower "Reuse" view surfacing recommendations for the selected project.
