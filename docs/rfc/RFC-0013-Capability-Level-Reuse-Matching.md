# RFC-0013 — Capability-Level Reuse Matching

- Status: **Proposed**
- Date: 2026-07-10
- Author: Chief Architect / Orchestrator (laptop session)
- Evidence: `docs/reviews/2026-07-10-recall-shakedown.md`; task #51
- Depends on: RFC-0008 (distillation), RFC-0010 (embedding tier), #50 (bounded prompt — merged)

## 1. Summary

Make ArchetypeOS's headline capability — accurate **cross-project reuse
recommendations** — actually work, by matching reuse needs against **named,
embedded, reuse-oriented capabilities extracted per repository**, instead of
against the one-sentence product purpose. This is a *granularity* fix, not a
lexical-vs-semantic fix.

## 2. Motivation / Evidence (the shakedown)

A 5-repo portfolio reality test (Recall, ArchetypeOS, AiGentOS, insta-ntly,
tali-api) proved:
- Distillation quality is **good** — accurate one-sentence purposes on all five.
- Reuse recommendations are **near-useless**, and it is NOT a distillation-quality
  or a lexical-vs-semantic problem:
  - Lexical: `"LLM provider abstraction and model routing"` → no matches; `"agent
    framework with tool calling"` → no matches.
  - Semantic (fastembed cosine over the purpose): `"LLM provider abstraction"` ranked
    the generic web app **instantly** over ArchetypeOS; `"agent framework"` was ~0.24
    noise across all five, with AiGentOS (the actual agent system) not in the top 3.
  - Semantic over the **full distillation page** (components + key points + tech):
    still wrong — AiGentOS absent for "agent framework", ArchetypeOS absent for "LLM
    routing".
- **Root cause — a granularity mismatch.** The distilled purpose describes what a
  repo *is* (product-level: "an engineering intelligence platform"); a reuse need
  asks what *capabilities* are inside it to borrow (component-level: "does it have an
  LLM router?"). Product-level evidence cannot answer component-level questions —
  lexically or semantically. The reuse engine is asking a question the distillation
  does not answer in a matchable form.

The reusable-capability evidence is **partially there already**: `reason_over_source`
emits a `reusable: [str]` array in its narrative — but it is thin (bare strings, no
per-capability provenance), and `recommend_reuse` never matches against it (it scores
need-coverage over `DNA.purpose` + technologies, and RFC-0010's semantic path embeds
only `title + DNA.purpose`).

## 3. Recommendation

Three changes, one per pipeline stage:

### 3.1 Extract named capabilities (distillation)
Promote the existing `reusable` slot to a first-class **capability list**. Each
capability is `{name, description, provenance}`:
- `name` — a short, reuse-oriented noun phrase ("LLM provider-routing abstraction",
  "adversarial output verifier", "approval queue", "agent tool-calling loop").
- `description` — one clause on what it does / how to borrow it.
- `provenance` — the file(s) it lives in (already cited in the narrative).
Update `_SOURCE_SYSTEM_PROMPT` to ask explicitly for "the concrete, reusable
capabilities or components a DIFFERENT project could borrow, each named and tied to
its file(s)." Reasoned tier only (the deterministic floor fabricates nothing → empty
capabilities → lexical-only fallback, unchanged/hermetic).

### 3.2 Store + embed at capability granularity (RFC-0010 extension)
New `RepositoryCapability` rows (one per capability): `repository_id`, `name`,
`description`, `provenance` (JSON), `embedding` (the RFC-0010 dialect-variant
`Vector(384)`/JSON column). Embed `name + " " + description` with the fastembed
embedder at distill time. Per-capability embeddings are the point: a need matches a
*single capability's* vector (high cosine), not a whole-product blob (noise).

### 3.3 Match needs against capabilities (transfer engine)
`recommend_reuse` gains a capability path: on postgres + a real embedder, order
capabilities by `embedding <=> need_vec`, aggregate to the repo of the best-matching
capability, and **cite the specific capability + its file** in the recommendation
("reuse ArchetypeOS's *LLM provider-routing abstraction* — `services/llm_router.py`").
Confidence is the RFC-0010 calibrated blend (never a raw cosine, LES-023). Lexical
fallback: coverage over the capability `name`/`description` text (sqlite / no embedder).
This makes recommendations **actionable** (names the unit + where it is), not just a
repo pointer.

## 4. Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| Match the one-sentence purpose semantically (RFC-0010 as-is) | ❌ tested in the shakedown — wrong granularity, noise/wrong answers |
| Match the full distillation page (purpose + components + tech) | ❌ tested — still wrong; product/structural text, not named capabilities |
| Enrich the lexical matched-text with `technologies`/`key_points` | ~ partial; frameworks are libraries not capabilities; doesn't name the reusable unit |
| **Extract + embed + match named capabilities (this RFC)** | ✅ addresses the root granularity mismatch; makes recs actionable |

## 5. Risks & mitigations
- **Reasoned-tier dependency**: capabilities only extract on a real tier (free/Claude).
  Mitigation: #50 (bounded prompt) is merged; on the deterministic floor the capability
  list is empty and the engine falls back to today's lexical behavior (no regression).
- **Extraction quality**: a weak prompt yields vague capabilities. Mitigation: the
  built-in acceptance test (below) gates prompt quality on real repos.
- **Schema/migration + pgvector index** for `RepositoryCapability`. Standard (mirror the
  RFC-0010 `embedding` column + ivfflat index; sqlite degrades to JSON, hermetic).
- **Cost**: one extra reasoned call per repo (or fold capabilities into the existing
  `reason_over_source` call — preferred, no new call). Fold in.

## 6. Effort & slices
- **Slice 1** — extraction: evolve `reason_over_source` to emit `capabilities:
  [{name, description, provenance}]` (extend the existing `reusable` output); render in
  the vault page; tests (hermetic: deterministic → empty; fake reasoned → populated).
- **Slice 2** — storage + embedding: `RepositoryCapability` model + migration + embed at
  distill time; tests (pgvector-gated + sqlite-hermetic).
- **Slice 3** — matching: `recommend_reuse` capability path (semantic + lexical), recs
  cite capability + file; tests.
- **Slice 4** — acceptance: wire the portfolio reality test as the regression gate.
- Estimate: medium-large (2–4 slices/PRs), each independently shippable.

## 7. Dependencies
- #50 bounded reasoned prompt (merged).
- RFC-0010 embedding tier (fastembed + pgvector) — reuse its column type + calibration.
- pg + fastembed for the semantic path (deterministic/sqlite path stays lexical/hermetic).

## 8. Acceptance criteria (built-in regression test)
Re-run the shakedown portfolio (Recall, ArchetypeOS, AiGentOS, insta-ntly, tali-api)
through capability extraction + the capability-matching reuse engine (pg + fastembed):
- `"agent framework with tool calling"` → **AiGentOS ranks #1**.
- `"LLM provider abstraction and model routing"` → **ArchetypeOS ranks #1** (AiGentOS acceptable #2).
- `"HTTP routing and middleware for a web API"` → a FastAPI web service ranks #1.
- Each recommendation **cites the specific reusable capability + its file** (provenance),
  not just a repo.
- The deterministic/sqlite path is unchanged (empty capabilities → today's lexical behavior).

## 9. Next steps
1. Land this RFC (review).
2. Build Slice 1 (extraction) — smallest, unblocks the rest; verify capabilities extract
   sensibly on the portfolio before touching storage/matching.
3. Final Judge escalation (Engineering Constitution) if capability extraction quality is
   contested on real repos — the acceptance test is the arbiter.
