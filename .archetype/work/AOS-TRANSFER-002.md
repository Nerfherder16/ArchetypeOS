# AOS-TRANSFER-002 — Transfer scorer calibration: need-coverage confidence (Package 3)

## Status

In Review

## Origin

The full end-to-end reality test (Orchestrator, 2026-07-06) — run over the 6-repo portfolio with the reasoned distillation tier (AOS-DISTILL-004) — showed the Knowledge Transfer Engine now returns the **correct repo #1 on every query with honest matched-term provenance**, but its confidence numbers were tiny and uncalibrated (0.01–0.13) because the score was a **Jaccard over the candidate's whole vocabulary** (`|need ∩ cand| / |need ∪ cand|`): a repo whose distilled `purpose` tokenizes to many terms has a large union, collapsing the score toward zero even when it is the right match. Uncalibrated magnitudes are misleading — a UI showing "confidence 0.09" for the #1 recommendation reads as a *bad* match — and are a prerequisite blocker for surfacing transfer in the product.

The same reality test also refined this package's scope: the reasoned purposes now **absorb the architecture/service signal** (example-voting-app's reasoned purpose names its "Redis queue"), so the originally-planned "fold `runtime_services`/architecture into the candidate text" half is **largely redundant** and is dropped (per the operator "design to the mature-state target" rule — don't build what the reasoned tier already covers). This package is therefore lean: **calibration only.**

## Verified Baseline (confirmed by inspection)

- `packages/aos_core/aos_core/services/transfer.py` `score_relevance` computed `jaccard = |need ∩ cand| / |need ∪ cand|` + `_TECH_BOOST(0.15) * |need ∩ tech|`, capped at 1.0. `recommend_reuse` sorted by `(-confidence, name)`.
- Rankings were already correct; only the magnitude/calibration was weak (reality-test evidence).

## Design (what shipped)

- **`score_relevance` → need coverage.** The score is the fraction of the target need's meaningful terms the candidate covers, via text **or** technology:
  `covered = (need ∩ cand) ∪ (need ∩ tech)`; `score = |covered| / |need|`. Bounded `0..1`, intuitive ("how much of what you asked for does this repo cover?"), and a technology-only match still counts (preserving the tech signal). Returns `(round(score, 4), sorted(covered))`. `_TECH_BOOST` removed (coverage counts tech matches directly).
- **`recommend_reuse` tiebreak.** Sort by `(coverage desc, technology-match count desc, source-repository name)` — a strong-reuse-signal tiebreak on equal coverage; `_tech_hits` is a transient sort key stripped before return (not in the read schema).
- Behaviour otherwise unchanged: drop zero-score, exclude `exclude_project_id`, `limit`, tolerant `[]`.

## In-Scope Files (implemented directly by the Orchestrator; small surgical change)

- `packages/aos_core/aos_core/services/transfer.py` — `score_relevance` (need-coverage), `recommend_reuse` (tiebreak + strip transient key), module + function docstrings; removed `_TECH_BOOST`.
- `apps/api/tests/test_transfer.py` — updated the two pure `score_relevance` unit tests to the coverage contract (+ a tech-only-match coverage test); behavioural ranking/exclusion/tolerance tests unchanged (they assert *which* repo ranks, not magnitudes).
- `knowledge/wiki/lessons/LES-023.md` + index — the calibration design-insight.
- `docs/rfc/RFC-0009-...md` (next-steps: normalization done; embeddings is the remaining relevance leap), `docs/CAPABILITY_MAP.md`, state docs.

## Out-of-Scope (deferred)

- Folding `runtime_services`/architecture into the candidate text (now largely redundant — the reasoned purpose covers it; revisit only if a concrete gap appears).
- Embeddings / semantic relevance (RFC-0009's remaining target increment, behind the same `score_relevance` seam).
- A Control Tower "Reuse" view (surfacing transfer in the UI — now unblocked by calibrated confidence).

## Acceptance Criteria

- `score_relevance` returns calibrated need-coverage (`|covered| / |need|`), bounded `0..1`, tech-only matches counted; rankings unchanged in order but magnitudes meaningful.
- Reality-test gate holds with meaningful confidence: kubernetes #1 on "container orchestration" (conf 0.333), gin #1 on "HTTP routing" (conf 0.800); the correct repo is #1 on every gated need.
- api + worker green; ruff full CI scope + compileall clean; guardian PASS; lesson recorded.

## Verification (Orchestrator, independent — implemented directly, verified behaviourally on the real portfolio)

Ran the reality harness over the 6 real repos and confirmed the rankings hold with calibrated confidence (0.2–0.8 vs the old 0.01–0.13); the "agent framework with tool calling" ranking *improved* (pydantic-ai, an actual agent framework, now #1 over the SDK). Full api (172) + worker (7) suites, ruff full CI scope + compileall clean.
