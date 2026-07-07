# AOS-USAGE-001 — LLM usage ledger + provider instrumentation (backend)

> **Status: GO — window clear.** Backend substrate for the "real Claude usage" surface the
> operator asked for. Touches the `aos_core/llm/` provider seam. Prerequisite coordination is
> met: AOS-UI-009 (#97) is merged and the tandem laptop session's in-flight llm-seam PRs (#92,
> #96, #98) have all landed — **no open PRs at start**. Keep every edit to shared `llm/` files
> ADDITIVE (optional fields + a new wrapper + new modules) to minimize conflict if the laptop
> opens a new seam PR mid-build. Frontend surface is a separate package (AOS-USAGE-002).

## Summary

Give ArchetypeOS a **local-first usage ledger** that records token/cost usage for every reasoned
LLM call, per **tier** (claude / local / free / deterministic), so the operator can see all three
tiers they use — the Claude subscription **and** local (RTX 3070) **and** free hosted APIs — in
one place. Each provider reports its **own real numbers**:

- **Claude subscription** → from Claude Code itself: run the `ClaudeCodeProvider` with
  `claude -p --output-format json` and read the returned `usage` (input/output tokens) and, when
  present, `total_cost_usd`. **Not** the Anthropic billing API (the operator uses the
  subscription, not metered API keys). *(Build-time verification required: confirm this
  Claude Code version emits `usage` in `--output-format json`; if not, fall back to a
  length-based estimate flagged `estimated: true`.)*
- **Local + free hosted** → from the `OpenAICompatibleProvider` response `usage`
  (`prompt_tokens` / `completion_tokens`), which the endpoint already returns.
- **Deterministic (CI floor)** → records nothing (no model, no tokens).

## Design

### ProviderResult extension (additive, low-conflict)

Add optional, nullable fields to `ProviderResult` — existing callers untouched:

```python
input_tokens: int | None = None
output_tokens: int | None = None
cost_usd: float | None = None
usage_estimated: bool = False   # True when tokens are length-derived, not reported
```

Each provider populates them where it can (Claude JSON usage; OpenAI-compatible `usage`;
deterministic leaves them None).

### Central instrumentation (a wrapping provider — no per-call-site edits)

Add `InstrumentedProvider` that wraps the resolved provider and, on each `generate()`, records a
`UsageEvent` via the usage service, then returns the inner result unchanged. `get_provider()`
returns the wrapped provider when a ledger sink is configured; otherwise returns the bare provider
(so CI/hermetic paths and callers with no DB stay unchanged). The sink is injected (a session
factory / callable), so the `llm/` package does not hard-depend on the DB.

### Model + migration

New `UsageEvent` (Alembic migration): `id, ts, provider, tier, model, input_tokens,
output_tokens, cost_usd, estimated, agent (nullable), session (nullable), context (nullable —
e.g. 'council'|'distillation'|'review')`. `tier` derives from provider name + config
(claude / local / free / deterministic).

### Usage service + API

- `aos_core/services/usage.py`: `record_usage(...)` (insert) + `summarize_usage(db, *, since=…)`
  → totals + per-tier + per-model breakdown (tokens in/out, est. cost).
- `apps/api/app/routes/usage.py`: `GET /usage/summary?window=today|7d|30d` returning the shape
  the frontend module renders (total tokens, cost, per-tier bars, in/out split).

### Cost estimation

Per-tier rate table (config-overridable): local/free ≈ $0 (self-hosted / free), Claude uses the
Claude Code-reported `total_cost_usd` when available, else a documented per-Mtoken estimate.
Never present an estimate as exact — carry the `estimated` flag through to the UI.

## Non-goals

- The frontend usage surface (AOS-USAGE-002 — the "Providers & Model Routing" Operations view,
  currently a "soon" stub, reads `GET /usage/summary`).
- Historical backfill; the ledger starts recording from deploy.
- Any change to routing/model-selection logic (that's the laptop's AOS-LLM-EVAL track).

## Tests

- Core: `record_usage`/`summarize_usage` (hermetic, sqlite) — insert + per-tier aggregation +
  window filter; `InstrumentedProvider` records exactly one event per `generate()` and returns
  the inner result unchanged; deterministic provider records nothing.
- Provider parsing: OpenAI-compatible `usage` → fields; Claude JSON `usage` → fields (mock the
  subprocess/response); estimate fallback flagged.
- API: `GET /usage/summary` shape + window param (`apps/api/tests`).
- Migration applies (`alembic upgrade head`) on the pgvector CI service.

## Acceptance criteria

1. Every non-deterministic `generate()` records one `UsageEvent` with the provider's real
   (or explicitly `estimated`) tokens; deterministic records none; CI stays hermetic/green.
2. `GET /usage/summary` returns total + per-tier (claude/local/free) tokens, in/out split, and
   est. cost for the window.
3. No change to existing council/distillation/review behavior or outputs; existing suites green.
4. Migration applies cleanly; Guardian PASS (api + core tests present).

## Risk / effort

- **Risk**: moderate — **coordination** is the main risk (shared `llm/` seam with the laptop
  session); mitigated by sequencing after their PRs land + keeping edits additive. Verifying the
  Claude Code `--output-format json` usage signal is a small build-time spike with a defined
  fallback.
- **Effort**: ~1–1.5 build cycles (model + migration + service + instrumentation + API + tests).
  One PR. The frontend surface (AOS-USAGE-002) follows.
