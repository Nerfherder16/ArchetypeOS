# LES-L20 — a delegating/wrapping provider must report its OWN identity on the result, not pass the delegate's through; the free rotation pool mis-tiered every call as "local"

## Aliases

- free-hosted models tagged tier=local in /usage
- gemini/llama-70b/mistral/120b showed up as local tier
- RotatingProvider returned the member's provider name
- usage ledger tier misclassification
- wrapper leaks the wrapped object's identity

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Real `/usage` on the deployed instance (pulled over tailscale): 4 reasoned events,
  models `gpt-oss-120b` / `gemini-2.5-flash` / `llama-3.3-70b-versatile` /
  `mistral-large-latest` — **exactly the `DEFAULT_FREE_POOL` members** — all recorded
  `tier="local"`, with 0 events under `free`.
- `derive_tier` already had the right rule (`"rotating"` → free; `"openai_compatible"`
  → free only when `base_url` matches a configured free endpoint, else local).
- Root cause: `RotatingProvider.generate` returned the **member** `OpenAICompatibleProvider`'s
  `ProviderResult` verbatim — `provider="openai_compatible"` — and the pool exposes no
  single `base_url`, so `InstrumentedProvider` forwarded `base_url=None`. `derive_tier`
  then hit the `openai_compatible` + no-base_url branch → `local`. The class was *named*
  `"rotating"` but its **results** never said so.
- Fix: `RotatingProvider.generate` sets `result.provider = "rotating"` before returning
  (model name preserved for the by-model breakdown). `derive_tier("rotating") → free`.

## Linked Decisions / Projects

- `packages/aos_core/aos_core/services/llm_pool.py` — `RotatingProvider.generate`
- `packages/aos_core/aos_core/services/usage.py` — `derive_tier` (the classifier that was correct all along)
- [[LES-L19]] — sibling routing/ledger lesson (preserve a function's contract when swapping it)

## Content

- Event: a wrapper (`RotatingProvider`) that delegates to a rotating member leaked the
  **member's** identity onto the result, so a downstream classifier keyed on
  `result.provider` mis-classified every free-pool call. The bug was invisible to unit
  tests (they assert selection/fallthrough, not the emitted identity) and only surfaced
  from **real production telemetry**.
- Rules:
  1. A provider/adapter that stands in for another must stamp its **own** identity on
     what it emits (`result.provider`), not pass the delegate's through — anything
     downstream keying on that field (tiering, cost, routing) depends on it.
  2. When a classifier looks correct but real data is wrong, suspect the **inputs to the
     classifier** (what identity/fields reach it), not the classifier's logic.
  3. Test the emitted identity, not just the control flow: a wrapper test should assert
     `result.provider` is the wrapper's, and that pass-through fields (model) survive.
  4. Real telemetry is a test surface — pull `/usage` (or equivalent) after a provider
     change; hermetic tests can't see an identity that only matters at aggregation time.
