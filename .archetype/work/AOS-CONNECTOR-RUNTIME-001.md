# AOS-CONNECTOR-RUNTIME-001 — Unified Connector Config, Real Probes, No Mutate-on-GET

## Status

Proposed

## Origin

Closes AOS-REVIEW-002 finding P0-4 (connector configuration truth split between API and worker), verified in [[LES-033]]. Wave 2.

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `packages/aos_core/aos_core/services/connectors.py:77` — `free_llm_pool.configured_when = lambda s: bool(s.llm_free_api_key)`.
- `packages/aos_core/aos_core/services/llm_pool.py:38-49,112-116` — the real rotating pool keys on `GROQ_API_KEY`/`CEREBRAS_API_KEY`/`GEMINI_API_KEY`/`MISTRAL_API_KEY` from `os.environ`, never `llm_free_api_key`.
- `docker-compose.yml:94-97` — those four keys forwarded to the `worker` service only; the `api` block (`:33-73`) receives none (its only Groq ref is `TTS_API_KEY` at :57). So the API-hosted catalog and the worker-hosted pool disagree.
- `connectors.py:59-67` — `local_llm.configured_when = bool(s.llm_base_url)`; `config.py:29` defaults `llm_base_url="http://localhost:11434/v1"` → "configured" with nothing listening; no reachability probe in `sync_connectors`.
- `apps/api/app/routes/connectors.py:25-29` — `GET /connectors` calls `sync_connectors`, which INSERT/UPDATE + `db.commit()` on every read (`connectors.py:163-181`) — a mutating GET; settings frozen at import via `@lru_cache` (`connectors.py:22`).

## In-Scope Files

- `packages/aos_core/aos_core/services/connectors.py` — the catalog becomes the sole config schema; represent pool members individually; split status into `declared` / `credential_present` / `reachable` / `healthy` / `quota_available`; add active probes; stop mutating on read.
- `packages/aos_core/aos_core/services/llm_pool.py` — pool membership sourced from the same schema, loaded identically in every process.
- `packages/aos_core/aos_core/config.py` — reconcile `llm_free_api_key` vs per-provider keys into one representation; document that a default base_url ≠ reachable.
- `apps/api/app/routes/connectors.py` — `GET /connectors` is read-only; reconciliation via startup sync or an explicit `POST /connectors/reconcile`.
- `docker-compose.yml` — forward connector config consistently to api/worker/scheduler.
- `apps/api/alembic/versions/0020_connector_status.py` (new) — split status columns.
- Tests: `apps/api/tests/test_connectors.py` (GET performs no writes; api and worker agree on free-pool config for the same env; `local_llm` reachable=false when nothing listens). Route inventory updated if a route is added (LES-L05).

## Out-of-Scope

- Per-node connector aggregation UI (feeds AOS-NODE-AGENT-001; the by-node report is produced here but consumed there).
- Egress *enforcement* by connector policy (that is the connector half of Track D governance / AOS-AUTHORITY-ENVELOPE-001).

## Acceptance Criteria

- API and worker report the same free-pool configuration for the same environment — evidence: `test_free_pool_config_agrees_across_processes` (same env → same `configured`/member set).
- `GET /connectors` performs no writes — evidence: `test_get_connectors_readonly` (no INSERT/UPDATE/commit; a `POST /connectors/reconcile` does the sync).
- `local_llm` reports unreachable when nothing listens on :11434 — evidence: `test_local_llm_reachability_probe`.
- Status is decomposed (declared/credential/reachable/healthy/quota) — evidence: schema + `test_connector_status_dimensions`.
- Schema migrates cleanly — evidence: `alembic upgrade head`; autogenerate → 0 ops.

## Verification Plan

Level 2 + full API suite; probes tested with a stub server (reachable/unreachable). Level 3: CI + compose-smoke (api/worker forwarded config parity). One PR, Manual Merge Gate. Builder ≠ verifier.

## Suggested Delegation

Sonnet builder (schema + config unification are mechanical; the probe is a small HTTP check). Orchestrator: review the single-schema seam so no process reads config a different way again (the exact defect class in LES-033 lesson 3), lesson, PR, gate.

## Board Linkage

- Plane: unassigned (Sprint "Make distributed runtime real")
- Branch: TBD, cut off latest main per `aos-ship-pr`
