# Connector Policy (AOS-CONNECTOR-001)

## Purpose

Connectors define **where data goes**. Connector sprawl (keys and URLs scattered
across `config.py`, `docker-compose.yml`, env vars, and frontend `VITE_*` values)
is a common failure mode in AI platforms, and it was flagged as Finding 9 of the
2026-07-08 system evaluation. This policy makes every external connection a
first-class, governed asset with a single source of truth.

The registry is the governance choke point: adding a new external connection means
adding a row to `CONNECTOR_CATALOG` in
`packages/aos_core/aos_core/services/connectors.py`. Nothing reaches the network
without appearing in the registry first.

## The registry

The catalog is declarative. Each connector carries:

| Field | Meaning |
| --- | --- |
| `name` | Stable identifier (e.g. `sotto_stt`). |
| `connector_type` | `llm` / `tts` / `stt` / `research` / `integration`. |
| `tier` | `claude` / `local` / `free` / `external`. |
| `enabled` | Operator toggle (default from the catalog). |
| `configured` | **Derived from settings on every sync** — never hand-maintained, so it cannot drift. True iff the connector's required config (key/URL/flag) is present. |
| `privacy_class` | `private_ok` (may receive private data) or `public_only` (must not). |
| `egress_allowed` | Whether data leaves the local/tailnet network. |
| `browser_exposed` | Whether a credential/URL for this connector ships to the browser. |
| `quota_policy` | Short label: `subscription` / `free-tier` / `self-hosted` / `metered` / `rate-limited` / `unmetered`. |
| `last_health_status` / `last_error` / `last_checked_at` | Recorded by a health probe (`POST /connectors/{name}/health`). |

`GET /connectors` reconciles the catalog into the registry on read, so the list is
never empty or stale and `configured` always reflects current settings. Disabled and
unconfigured connectors remain visible without erroring.

## Governance rules

1. **A `public_only` connector must never receive private or sensitive data.** The
   free hosted LLM pool, Groq TTS, Exa, SearXNG, crawl4ai, and Firecrawl are all
   `public_only`. Route private work only to `private_ok` connectors (Claude,
   local LLM, Sotto STT — the last is tailnet-only).
2. **Browser-exposed credentials are treated as public/client tokens.**
   `VITE_SOTTO_TOKEN` ships to the browser by design; `sotto_stt` is therefore
   flagged `browser_exposed=true`. Never place a secret that must stay server-side
   behind a `VITE_*` var. If Sotto ever needs a sensitive token, proxy it through
   the API instead of exposing it to the browser.
3. **Egress is explicit.** `egress_allowed=false` connectors (local LLM, Sotto,
   SearXNG, crawl4ai) stay on the tailnet. `egress_allowed=true` connectors send
   data off-network and must be `public_only` unless the tier is Claude
   (subscription, private-ok by contract).
4. **Provider exception strings are not surfaced raw.** Avoid returning upstream
   error bodies to the operator or the browser; they may echo request data. Health
   probes record a short, curated `last_error` string only.
5. **Off by default stays off.** Research web services are profile-gated and
   unconfigured by default; the registry surfaces their health/policy without
   turning them on.

## Health

Health is recorded, not inferred. A prober (worker job or deploy check) calls
`POST /connectors/{name}/health` with `{status, error?}`; the registry rolls the
result onto the connector (`last_health_status`, `last_error`, `last_checked_at`).
Unconfigured connectors report `unknown` until first probed.

## Dashboard

The operator surface is **Operations -> Providers & Model Routing -> Connectors**
(UI follow-up). It shows every connector's privacy class, whether it can receive
private data, browser-exposed labeling, configured/enabled state, and last health.

## Acceptance criteria (Finding 9)

- All external connectors are visible in one panel. ✔ (`GET /connectors`)
- Each connector shows privacy class and whether it can receive private data. ✔
- Browser-exposed tokens are explicitly labeled. ✔ (`browser_exposed`)
- Disabled/unconfigured connectors are visible without causing errors. ✔
- Health checks exist for configured connectors. ✔ (`POST /connectors/{name}/health`)
