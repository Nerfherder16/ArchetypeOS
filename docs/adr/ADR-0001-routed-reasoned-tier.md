# ADR-0001 - Routed reasoned tier (local + free-hosted + Claude)

## Status

Accepted

## Date

2026-07-07

## Context

ArchetypeOS is a deterministic-floor + reasoned-tier system. Until now the
reasoned tier meant **Claude** — capable but metered, rate-limited, and
on-demand. The operator hit a weekly Claude-token ceiling, which surfaced a
structural gap: the platform could not run its own reasoning (code review,
distillation, research, council) without spending the same budget it exists to
conserve. The Engineering Constitution is local-first and requires human approval
for destructive actions and IP protection; the vision docs already anticipate
non-Claude execution (Engine Catalog: Build Intelligence "hands work to Claude
Code, **local LLMs**, or other builders"; Agent Catalog: Builder Agent runs
"through Claude Code, **local tools**, or other coding agents").

Hardware: ArchetypeOS runs on `teevee-1` with a dedicated **RTX 3070 (8GB)**,
kept isolated from the RTX 3090 that serves the operator's Recall system (no GPU
contention). `AOS-LLM-LOCAL-001` added an OpenAI-compatible provider that reaches
any `/chat/completions` endpoint — local Ollama or a free hosted API — by config.

## Decision

Adopt a **four-tier routed reasoned tier**. The reasoned tier is no longer "call
Claude"; it is a routed pool:

- **Tier 0 — Deterministic** (in-process): the hermetic CI floor. Unchanged, and
  remains the default so CI never calls a model.
- **Tier 1 — Local** (teevee 3070, Ollama): free, private, fast, high-volume,
  bounded tasks. First app: the local **code reviewer** (`AOS-LLM-REVIEW-001`).
- **Tier 2 — Free hosted** (Gemini / Groq / Cerebras / DeepSeek / Mistral, from
  the `cheahjs/free-llm-api-resources` catalog): capable reasoning on
  **non-sensitive** input only.
- **Tier 3 — Claude**: highest-stakes reasoning, Final Judge, and any private +
  critical work.

**Privacy tiering is a hard guardrail:** private/proprietary code never leaves
for Tier 2 (most free tiers train on submitted data); it stays Tier 1 or Tier 3.
Routing is **eval-driven** (`AOS-LLM-EVAL-001`) — the task→tier table is measured,
not guessed.

## Alternatives Considered

- **Claude-only (status quo):** simplest, highest quality per call. Rejected — it
  is the cost/scarcity problem itself and blocks always-on work.
- **Local-only:** free, fully private. Rejected as sole tier — an 8GB 7B is a
  weak generalist; some reasoning genuinely needs a bigger model.
- **Free-API-first:** cheap, capable. Rejected as sole tier — rate-limited,
  external, and unsafe for private code (privacy tiering exists for exactly this).
- **Four-tier routed (accepted):** captures each tier's strength, keeps private
  work local/Claude, and lets free frontier models do the heavy non-private
  reasoning. The provider seam makes the choice per-task and reversible.

## Evidence

- `packages/aos_core/aos_core/llm/__init__.py` — `OpenAICompatibleProvider`
  (AOS-LLM-LOCAL-001, PR #92).
- `packages/aos_core/aos_core/services/code_review.py` + `tools/pr_reviewer.py` —
  the Tier-1 reviewer (AOS-LLM-REVIEW-001).
- **Eval (teevee 3070, `qwen2.5-coder-reviewer`):** `num_ctx` (Ollama's 4096
  default) was silently truncating large diffs — the real cause of the
  rambling-on-big-diffs failure; raising it to 8192 fixed it. Structured JSON +
  rubric eliminated prose rambling and false positives. **Per-category
  ("pointwise") passes tripled recall** (1/3 → 3/3 on a planted-bug diff: div-by-
  zero, error-handling, resource leak) while precision held (near-silent on real
  merged PRs). Latency ~2–10s/diff. Log: `.archetype/eval/review_spike.jsonl`.
- **Deep research** (`w2lo9w8tr`, 26 sources, 21 confirmed / 4 refuted) — the
  reviewer setup (params, structured output, rubric, few-shot, sliced context).
- **LLM Council** verdict (2026-07-07) — measure before building; the reversible
  provider is the real asset.
- `docs/reviews/2026-07-07-local-and-free-llm-opportunity-map.md` — the full
  surface→tier map.

## Consequences

Positive:
- ArchetypeOS runs its own reasoning off Claude — recurring token savings.
- Unlocks **always-on** work (idle 3070 + free tiers): overnight review,
  distillation, drift detection, research corpus.
- Unlocks a **genuine multi-model Council** (each agent a different free frontier
  model; Claude as Final Judge) — real model diversity at ~zero cost (RFC-0005).

Negative:
- More moving parts: a router + a free-API rotation pool (rate-limit handling).
- Free tiers are rate-limited and external — usable only under privacy tiering.
- Local 7B is high-precision but moderate-recall; it is a first-pass filter, not
  a replacement for a Claude deep-review.

Tradeoffs:
- Per-category review is ~5× the calls (~10s vs 2s) for materially higher recall
  — acceptable for advisory/nightly use.
- Complexity is bounded by keeping Tier 0 the default and every tier behind one
  provider seam.

## Migration Plan

1. Land the provider seam (PR #92) and the Tier-1 reviewer (this ADR's scope).
2. Build the **eval-driven router + free-API rotation pool** (`AOS-LLM-EVAL-001`)
   — the substrate every Tier-2 route depends on.
3. **Multi-model Council** on the router (non-private questions).
4. Point the **nightly routines** (reconcile narrative, conflict-learn, digest)
   at Tier 1/2.
5. Distillation + Research → Tier 2 for public inputs; Design → Gemini multimodal.

## Acceptance Criteria

- The reasoned tier is selectable per task via config, callers unchanged. ✅ (#92)
- Deterministic remains the CI default; no tier reaches CI. ✅
- The local reviewer is advisory, fail-open, and never blocks a merge. ✅
- Private code is never routed to Tier 2 (enforced by the router's sensitivity
  class). — pending the router (`AOS-LLM-EVAL-001`).
- Each new tier route is validated on the eval harness before it is trusted.

## Reviewers

- Research — deep-research `w2lo9w8tr` + opportunity map
- Architecture — provider seam + service, layered on the deterministic Guardian
- Security — privacy tiering guardrail (private code stays Tier 1/3)
- Compliance — data-training exposure on free tiers addressed by §privacy tiering
- Final Judge — pending (operator to ratify on merge of #92)
