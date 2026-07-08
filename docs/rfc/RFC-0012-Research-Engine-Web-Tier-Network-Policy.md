# RFC-0012 — Research Engine web tier + network policy (slice-2)

## Status

Proposed — operator-directed 2026-07-08 (follow-on to RFC-0011 slice-1, which shipped the deterministic
`LocalCorpusSource` floor as PR #109). This RFC adds the **web tier** behind the RFC-0011
`ResearchSource` seam and defines the **network policy** for the first arbitrary-host egress in the
system. It is gated on operator infra provisioning (keys + self-hosted services on teevee). Design is
evidence-backed by a verified research pass (2026-07-08, 22 sources / 25 adversarially-verified claims;
see "Evidence" below).

## Summary

RFC-0011's Research Engine floor produces research-class evidence from the portfolio's **own**
knowledge (`LocalCorpusSource`) — deterministic, hermetic, no network. This RFC gives it **reach**: a
`WebResearchSource` that discovers and fetches real external evidence across the source-quality ladder,
turning the engine from "what does my portfolio already know" into "what does the *world* know,
ranked." It is the payoff of the whole engine.

The operator's constraint is explicit: **keep Exa, but don't get rate-limited.** The answer is
architectural and mirrors a pattern already proven in this codebase — the `RotatingProvider` free-LLM
pool (`services/llm_pool.py`), which fails through to the next backend on any 429/5xx/timeout and only
raises when every member fails. We apply the same shape as **two role-split failover pools**:

- **Discovery pool** (find URLs): **Exa** (primary — best semantic search) → self-hosted **SearXNG**
  (quota-free fallback on teevee).
- **Fetch pool** (URL → clean markdown): self-hosted **crawl4ai** (primary workhorse — free, no vendor
  quota, LLM-ready markdown) → self-hosted **Firecrawl** (hard-page fallback).

Because the self-hosted backends (crawl4ai, SearXNG) carry the *volume*, the metered hosted API (Exa)
is reserved for high-value discovery and is rarely exhausted — that is the rate-limit fix.

## Problem

- The RFC-0011 floor never leaves the box. To answer "should we adopt X?" with authoritative external
  evidence (official docs, standards, reference impls, benchmarks, security advisories) the engine must
  fetch from the web — which nothing in the system does today (the only outbound HTTP is the LLM seam's
  stdlib `urllib` calls; `docker-compose.yml`'s worker has no egress config or search keys).
- A naive single-API web tier gets **rate-limited**: hosted search/scrape APIs (Exa, Tavily, Firecrawl
  cloud) meter by credits/quota and eventually 429. (Verified: Exa ~$5–15/1k req; Tavily 1k
  credits/mo free; Firecrawl cloud ~$16–333/mo.)
- Web egress is **net-new attack/policy surface** — the first time the system reaches arbitrary hosts.
  It needs an explicit, auditable policy (allowlist, timeouts, rate limits, key handling) before any
  fetch code ships.

## Goals (slice-2 scope)

- A **`WebResearchSource`** implementing the RFC-0011 `ResearchSource` protocol
  (`gather(db, *, project_id, question, sensitivity, limit) -> list[SourceDoc]`), composed of the two
  pools above. It returns the same `SourceDoc` shape the deterministic floor already ranks — so
  `score_source` / `synthesize_dossier` / `research()` are **unchanged** (the seam pays off).
- A **`RotatingResearchSource`** (generalizes `RotatingProvider`): holds an ordered list of backends,
  round-robins a start cursor, **fails through on transient errors only** (429/502/503/timeout), honors
  `Retry-After`, applies **jittered exponential backoff**, trips a **circuit breaker** after N
  consecutive failures per backend, and enforces a **retry budget** (abort if 429s exceed ~15% of
  attempts). Raises only when every backend is exhausted; the engine then degrades to `LocalCorpusSource`.
- **Backend adapters** (each a thin `ResearchSource`): `ExaSource` (discovery), `SearxngSource`
  (discovery), `Crawl4aiSource` (fetch), `FirecrawlSource` (fetch). Each speaks its HTTP API via
  **stdlib `urllib`** (no new Python dependency — same discipline as `OpenAICompatibleProvider`) and is
  **fully mockable** (constructor-injected, like the pool's pre-built providers).
- **Network policy** (the core of this RFC): a config-driven **egress allowlist** (only the four hosts:
  the Exa API host, and the teevee-local `crawl4ai`/`searxng`/`firecrawl` service URLs), per-request
  **timeouts**, per-host **rate limits**, `robots`/politeness for direct fetches, and **no secret ever
  logged** (verify keys by name/count only). Backends whose host/key is not configured are simply
  absent from the pool (like `build_free_pool`).
- **Privacy rule (minimal, per the operator's call):** research defaults to `PUBLIC` (research is about
  public technology) → the web pools run freely. `sensitivity=PRIVATE` **skips the web tier entirely**
  and falls back to `LocalCorpusSource` — because a query sent to a third-party search API (Exa/Tavily)
  or an arbitrary target host leaks its text; a proprietary-context question must not egress. One flag,
  defaulting to public. No elaborate privacy machinery.
- **Compose additions:** `crawl4ai` and `searxng` (both no-GPU; crawl4ai ~2 GB image / Playwright,
  SearXNG light) as new services in the tracked `docker-compose.yml`, reached by the worker over the
  Docker network. Firecrawl self-host (heavier: Redis+Playwright+Postgres, 4–8 GB) is an **optional**
  second fetch stage the operator can enable later.
- **CI hermeticity preserved:** no backend is configured in CI → `WebResearchSource` contributes no
  members → the engine uses `LocalCorpusSource` → the deterministic, no-network path is unchanged. All
  adapters are mocked in tests; no network fires under pytest; no new dependency executes in CI.

## Non-goals (explicitly deferred)

- **Reasoned LLM synthesis of the dossier** (`route("research", …)`) — slice-3. This slice still uses
  the deterministic `synthesize_dossier`; it just feeds it real web `SourceDoc`s.
- **browser-use** and **Maxun** as pool backends — *rejected* (Evidence): browser-use is an
  interactive browser-*automation agent* (~869 MB/session, needs its own LLM, doesn't parallelize) —
  wrong tool for bulk fetch; Maxun is no-code/point-and-click — not a programmatic per-query fit. A
  future "hard interactive page" escape hatch could revisit browser-use, but not here.
- **ScrapeGraphAI** — deferred; it needs an LLM per extraction (heavier), overlapping slice-3.
- **Tavily** as a second hosted discovery tier — deferred (a second hosted key to manage); SearXNG is
  the quota-free fallback. Easy to add later as another discovery-pool member (no code change beyond a
  key, per the pool pattern).
- **Continuous Research Engine** (`docs/CONTINUOUS_RESEARCH_ENGINE.md`) — ecosystem watch; later.
- **Frontend** — the Research Inbox (#107) already renders the notes; a per-dossier source-ladder view
  is a later UI package.

## Design

- **New** `packages/aos_core/aos_core/services/research_web.py`:
  - `RotatingResearchSource(ResearchSource)` — the failover pool (see Goals). Constructor takes an
    ordered `list[ResearchSource]` + labels (trivially testable with fakes, like `RotatingProvider`).
  - `ExaSource`, `SearxngSource` (discovery: query → candidate URLs + snippets → `SourceDoc`s tagged to
    ladder tiers), `Crawl4aiSource`, `FirecrawlSource` (fetch: URL → clean markdown → `SourceDoc.text`).
    Each via stdlib `urllib`, timeouts, `Retry-After` aware.
  - `build_web_source(settings) -> ResearchSource | None` — assembles the discovery pool + fetch pool
    from whichever hosts/keys are configured (env: `EXA_API_KEY`, `CRAWL4AI_URL`, `SEARXNG_URL`,
    `FIRECRAWL_URL`); returns `None` when nothing is configured (→ engine uses `LocalCorpusSource`).
    Discovery-then-fetch: gather URLs from the discovery pool, fetch each through the fetch pool,
    emit ranked `SourceDoc`s.
- **`research()` wiring** (`services/research.py`, minimal): default `source` becomes
  `build_web_source(get_settings()) or LocalCorpusSource()` for `PUBLIC`; `PRIVATE` forces
  `LocalCorpusSource()`. Everything downstream (score/synthesize/persist) is unchanged.
- **Config** (`config.py`): additive `exa_api_key`, `crawl4ai_url`, `searxng_url`, `firecrawl_url`,
  `research_web_enabled` (default False → hermetic), plus timeout/rate-limit knobs. Egress allowlist is
  derived from the configured host URLs (no free-form fetch).
- **Compose** (`docker-compose.yml`): `crawl4ai` + `searxng` services (no-GPU), worker gains their URLs
  + `EXA_API_KEY` in its env (via the tracked compose env from #108). Compose smoke stays green (new
  services must be in the smoke path — LES-011).
- **Tests** (`apps/api/tests/test_research_web.py`): the pool fails through a 429 backend to the next;
  honors `Retry-After`; trips the circuit breaker; `PRIVATE` never constructs a web source; an
  all-failed pool degrades to `LocalCorpusSource` (engine still returns a note); adapters parse their
  API shapes from fixtures. All mocked — no network.

## Alternatives considered

- **Single hosted API (Exa or Firecrawl-cloud) for the whole web tier — rejected.** Simplest, but the
  operator's explicit constraint is rate-limiting; a single metered API is exactly what 429s. The pool
  with self-hosted workhorses is the point.
- **browser-use / Maxun as fetch backends — rejected** (see Non-goals + Evidence): wrong class of tool
  (interactive agent / no-code) for programmatic bulk fetch; heavyweight and non-parallel.
- **"Self-hosting removes all limits" assumption — rejected as false.** Verified: self-hosting removes
  the *vendor account quota*, but not (a) your hardware ceiling (self-hosted Firecrawl even rejects jobs
  past 80% CPU/RAM) nor (b) the **target site's own** anti-bot/rate-limiting (self-host lacks Firecrawl
  cloud's Fire-engine). So the fetch pool still needs backoff + politeness + a hosted last resort for
  hard pages — the design reflects this, it does not assume infinite self-hosted throughput.
- **Reimplement failover from scratch — rejected.** `RotatingProvider` already encodes the exact shape;
  `RotatingResearchSource` generalizes it (adds Retry-After/circuit-breaker/retry-budget the research
  surfaced). One pattern, two uses.
- **Open egress (fetch any URL) — rejected.** The web tier fetches *only* URLs surfaced by the
  discovery pool and reaches *only* allowlisted hosts; no free-form SSRF surface.

## Acceptance criteria

- With `EXA_API_KEY` + `CRAWL4AI_URL` + `SEARXNG_URL` configured, `research(question)` returns a
  `ResearchNote` whose sources are **real web results** ranked by the existing source-quality × relevance
  scorer, each provenance-tagged; the pool **fails through** an unavailable/429 backend to the next
  (tested with fakes) and honors `Retry-After`.
- **CI hermeticity intact:** with nothing configured, `build_web_source` returns `None`, the engine
  uses `LocalCorpusSource`, and the full deterministic/no-network path passes exactly as in RFC-0011.
- **Privacy:** a `PRIVATE` research call never constructs a web source (no query egress) — tested.
- **Network policy enforced:** only allowlisted hosts are reached; timeouts + retry budget + circuit
  breaker exercised in tests; **no secret is logged** (name/count only).
- **Compose:** `crawl4ai` + `searxng` in `docker-compose.yml`; `docker compose config` valid; compose
  smoke green; the deploy poller rebuilds clean on teevee.
- api + worker + core green; ruff + compileall clean; **Guardian PASS**; a `LES-*` for any BLOCK/CI
  failure. Backend/cross-layer → explicit operator merge approval (not auto-merge).

## Dependencies

- **RFC-0011 (#109)** — the `ResearchSource` seam + `SourceDoc`/`score_source`/`synthesize_dossier`
  this drops into. Landed.
- **`RotatingProvider`** (`services/llm_pool.py`) — the failover pattern generalized here (read-only
  reference; not edited — laptop-session seam).
- **Operator provisioning (the gate):** an `EXA_API_KEY`; `crawl4ai` + `searxng` running on teevee
  (added to tracked compose, per the #108/AOS-OPS-DEPLOY-001 env pattern); operator approval of the
  egress allowlist (the four hosts). Optionally a self-hosted Firecrawl for the hard-page fetch stage.
- **Network-policy sign-off** — this RFC *is* that policy; merging it is the approval.

## Evidence

Verified research pass 2026-07-08 (22 sources, 25 adversarially-verified claims). Load-bearing,
confirmed: **crawl4ai** — Apache-2.0, self-host only, free/no-keys, LLM-ready markdown + deep-crawl
discovery, Playwright/no-GPU (~2 GB image, ~300 MB idle), ~71k★, v0.9, very active. **SearXNG** —
AGPL-3.0 self-hosted meta-search (200+ engines), discovery-only, no hosted fee, Python HTTP API,
~34k★. **Exa** — cloud-only semantic discovery, ~$5–15/1k req. **Firecrawl** — cloud+self-host
(AGPL-3.0 server / MIT SDK), discovery+fetch, self-host heavy (Redis+Playwright+Postgres, 4–8 GB) and
**lacks the cloud anti-bot**. **browser-use** — MIT browser-automation agent, ~869 MB/session, needs an
LLM — excluded. Killed/over-stated claims corrected in "Alternatives" (notably "self-host = zero
limits"). Resilience patterns (retry only 429/502/503, honor Retry-After, jittered backoff, circuit
breaker, retry budget) are drawn from the verified sources and encoded in `RotatingResearchSource`.

## Next steps (beyond slice-2)

1. **Slice-3 — the multi-phase research loop on the local/free tiers (operator-directed 2026-07-08:
   "teach the local LLMs to do that research run").** Encode the proven deep-research methodology —
   **scope → search → fetch → adversarial-verify (N-vote, kill on majority refute) → cited
   synthesis** — as the engine's own harness: versioned per-phase prompts + the verification contract,
   executed with each phase's LLM calls routed through `route("research", …)` to **LOCAL (on-node
   Ollama) / FREE (rotation pool)** models, reserving **Claude for the final judge/synthesis only**
   (escalated when quality demands it — the AOS-LLM-EVAL-001 council pattern applied to research). The
   value is that the *methodology* — not a model fine-tune — carries the capability, so a 70B
   local/free model runs deep-research-quality dossiers at ~zero Claude cost; multi-model diversity +
   the adversarial-verify pass compensate for any single model being weaker than Claude. To be drafted
   as **RFC-0013** once slice-2 lands. This is the Research Engine's endgame and what makes local-first
   research valuable.
2. Add **Tavily** and/or a self-hosted **Firecrawl** stage as pool members (key/URL only).
3. **Per-dossier Control Tower view** (source ladder + conflicting-evidence panel).
4. **Continuous Research Engine** feeding Recommendation Intelligence.
