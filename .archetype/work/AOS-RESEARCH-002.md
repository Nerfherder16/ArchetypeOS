# AOS-RESEARCH-002 — Research Engine web tier + failover pools (RFC-0012 slice-2)

## Status

Ready — RFC-0012 slice-2, operator-approved 2026-07-08. Backend/cross-layer + compose change; explicit
operator merge approval (not auto-merge). crawl4ai + SearXNG are **profile-gated** in compose (defined,
start only when the operator enables the profile + sets env).

## Verified Baseline (confirmed by inspection 2026-07-08)

- `services/research.py` — the RFC-0011 seam is live: `SourceDoc` (dataclass; `ref/title/text/tier`,
  `tier_rank`/`label`/`quality` derived from `SOURCE_TIERS`), `@runtime_checkable ResearchSource`
  Protocol (`gather(db, *, project_id, question, sensitivity, limit) -> list[SourceDoc]`),
  `LocalCorpusSource`, `_rank`, `synthesize_dossier`, and `research(db, *, project_id, question,
  sensitivity=PUBLIC, source=None, limit=8, as_of=None)`. `research()` currently defaults
  `source = LocalCorpusSource()` and calls `route("research", sensitivity, get_settings())` (result
  unconsumed). Downstream (score/rank/synthesize/persist) is source-agnostic — a new source drops in
  with zero downstream change.
- `services/llm_pool.py` — `RotatingProvider` is the failover pattern to generalize: pre-built member
  list, round-robin cursor, fall through on ANY per-call exception, raise only when all fail;
  `build_free_pool` assembles from env keys ("adding a member is exporting a key"). **Read-only
  reference — do not edit (laptop-session seam.)**
- `config.py` — `Settings(BaseSettings)`, fields default-valued, env by field name (`EXA_API_KEY` →
  `exa_api_key`), `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`. Existing
  `llm_*`/`llm_free_*` fields are the pattern to mirror.
- `docker-compose.yml` — `worker` service env (lines ~81–97) already forwards `GROQ/CEREBRAS/GEMINI/
  MISTRAL_API_KEY` + `COUNCIL_MULTI_MODEL` (post-#108 tracked env). New services follow the `api`/
  `worker` `build:`+`environment:` shape. Compose smoke gates new services (LES-011).
- `apps/api/tests/test_route_inventory.py` — **no new route** in this slice (`POST /projects/{id}/
  research` already exists); inventory unchanged.

## In-Scope Files

- **New** `packages/aos_core/aos_core/services/research_web.py` — `RotatingResearchSource`, the backend
  adapters (`ExaSource`, `SearxngSource`, `Crawl4aiSource`, `FirecrawlSource`), the composite
  `WebResearchSource` (discovery→fetch), and `build_web_source(settings) -> ResearchSource | None`.
- **Edit** `packages/aos_core/aos_core/services/research.py` — source resolution ONLY: for `PUBLIC`,
  default `source = build_web_source(get_settings()) or LocalCorpusSource()`; for `PRIVATE`, force
  `LocalCorpusSource()` (never construct a web source — no query egress). No other change.
- **Edit** `packages/aos_core/aos_core/config.py` — additive: `research_web_enabled: bool = False`,
  `exa_api_key: str = ""`, `crawl4ai_url: str = ""`, `searxng_url: str = ""`, `firecrawl_url: str = ""`,
  and timeout/limit knobs (`research_http_timeout: float = 10.0`, `research_max_fetch: int = 8`,
  `research_retry_budget: float = 0.15`).
- **New** `apps/api/tests/test_research_web.py` — hermetic tests (all mocked; no network).
- **Edit** `docker-compose.yml` — add `crawl4ai` + `searxng` services **under a `research` profile**
  (`profiles: ["research"]` so they don't start by default); add `EXA_API_KEY`, `CRAWL4AI_URL`,
  `SEARXNG_URL`, `FIRECRAWL_URL`, `RESEARCH_WEB_ENABLED` to the `worker` env block.
- **Edit** `.env.example` — document the new env (names only, no values).
- Docs/state: `docs/rfc/RFC-0012-...md` (drafted — leave), `.archetype/work/AOS-RESEARCH-002.md`,
  `docs/RECENT_CHANGES.md`.

## Out-of-Scope

- Any edit to `llm_pool.py`, `llm_router.py`, `council.py`, `usage.py` (contended). Generalize the
  pattern in the NEW `research_web.py`; consume `route()` read-only.
- Reasoned LLM synthesis / the multi-phase research loop on local-free tiers — **slice-3 (RFC-0013)**.
- `browser-use`, `Maxun`, `ScrapeGraphAI`, `Tavily` backends — deferred (RFC-0012 Non-goals).
- New Python dependency — all HTTP via **stdlib `urllib`** (mirror `OpenAICompatibleProvider`).
- New DB table/migration; any frontend change; any new API route.

## Acceptance Criteria

- `RotatingResearchSource` fails through a 429/5xx/timeout backend to the next, round-robins its start
  cursor, honors a `Retry-After` header (with jittered backoff), trips a circuit breaker after N
  consecutive per-backend failures, enforces the retry budget, and raises only when all members fail —
  evidence: `test_research_web.py::test_pool_fails_through_and_honors_retry_after`,
  `::test_circuit_breaker_and_retry_budget` (backends are injected fakes; no network).
- `build_web_source(settings)` returns `None` when `research_web_enabled` is False OR no backend
  host/key is configured; otherwise a `WebResearchSource` composed of the configured discovery pool
  (Exa→SearXNG) + fetch pool (crawl4ai→Firecrawl) — evidence: `::test_build_web_source_absent_when_unconfigured`, `::test_build_web_source_assembles_configured_pools`.
- **CI hermeticity intact:** with nothing configured (CI default), `research()` uses `LocalCorpusSource`
  and every RFC-0011 test still passes unchanged — evidence: full `apps/api/tests` green + a
  `::test_research_defaults_to_local_when_web_absent`.
- **Privacy:** `research(..., sensitivity=Sensitivity.PRIVATE)` never constructs a web source even when
  fully configured — evidence: `::test_private_skips_web_tier` (patch `build_web_source` to assert
  not-called, or assert the source used is `LocalCorpusSource`).
- **Degradation:** an all-failed web pool makes `research()` still return a graceful note (falls back to
  local / empty) without raising — evidence: `::test_web_all_failed_degrades_gracefully`.
- Adapters parse their API response shapes from fixtures into `SourceDoc`s (discovery: url+snippet+tier;
  fetch: fills `text`) and reach only their configured host — evidence: `::test_adapters_parse_fixtures`.
- **No secret logged** — any diagnostic logs backends by name/label, never key values — evidence: code
  review + a `::test_no_key_in_logs` asserting the key string never appears in captured logs.
- `docker compose config` valid with the new profile-gated services; api + worker + core green; ruff +
  compileall clean; compose smoke green; **Guardian PASS**; a `LES-*` for any BLOCK/CI failure.

## Verification Plan

- Level 3 (independent, builder ≠ verifier): Orchestrator re-runs `PYTHONPATH=apps/api pytest
  apps/api/tests` + worker suite in the py3.12 CI-parity venv; ruff + compileall; `docker compose
  config`; local Guardian. Confirm CI-hermetic default path unchanged and no contended-seam edits
  (`git status`). Confirm the profile gating (`docker compose config --profiles` shows crawl4ai/searxng
  only under `research`).

## Suggested Delegation

Generalize `RotatingProvider` into `RotatingResearchSource` in the NEW `research_web.py` (do not import
from `llm_pool` beyond reading its shape): a constructor-injected ordered `list[ResearchSource]` (+
labels), round-robin cursor, fall-through on transient errors (classify: retry 429/502/503/timeout;
never 400/401/404), honor `Retry-After` (+0.5–2s jitter), jittered exponential backoff, a per-backend
circuit breaker (open after N consecutive fails), and a retry budget (abort when 429s exceed
`research_retry_budget`). Fully testable with fake backends (no network). Then the adapters, each a thin
`ResearchSource` (discovery: `ExaSource`/`SearxngSource` → `SourceDoc`s with `ref=url`, `text=snippet`,
tier-classified; fetch: `Crawl4aiSource`/`FirecrawlSource` expose a `fetch(url) -> str` used by the
composite), all via **stdlib `urllib`** with the timeout, mockable via an injected opener/transport.
`WebResearchSource.gather` = discovery-pool `gather` → fetch each result's text through the fetch pool →
enriched ranked `SourceDoc`s; failover in both stages; tolerant (partial failures drop that source, all
failures → `[]`). `build_web_source(settings)` assembles pools from configured hosts/keys, returns
`None` if disabled/unconfigured. Wire the PUBLIC/PRIVATE source resolution in `research.py`. Add config
fields + compose services (profile `research`) + worker env + `.env.example`. Write the hermetic tests.
Do NOT commit/push. Run the suites + ruff + compileall + `docker compose config` yourself and report.

## Board Linkage

- Plane:
- Branch: claude/aos-research-002-webtier-rfc
