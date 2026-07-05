# AOS-RUNTIME-004 — /health Graceful Degradation (Alpha Finding #1)

## Status

In Progress

## Origin — the loop this closes

First package under the operator's feedback principle: every PR, learning moment, and failure ties back into the loops. This defect was found live by the system evaluating itself (Alpha Review, PR #37), recorded as a decision with typed research evidence (`.archetype/alpha/self-decisions.json`, decision "Fix /health Redis degradation as first post-v0.1 runtime task"), ranked #1 in `docs/ALPHA_REVIEW_V0_1.md` Next Development Guidance, and approved by the operator. failure → decision → fix → verified.

## Verified Baseline

Confirmed by inspection (`apps/api/app/main.py:39-48`):

- `health()` probes the DB (`select 1`) and Redis (`ping()`, 1s timeouts) with **no exception handling on either probe**. A Redis `ConnectionError` propagates → HTTP 500 (observed live in the alpha run, traceback captured); a DB failure would do the same.
- On teevee-1 with all services healthy it returns `{"status": "ok", "api": true, "database": true, "redis": true}` (`.archetype/alpha/self-health.json`).
- `apps/api/tests/` has no test for `/health` (52 tests, none touch it). `conftest.py` already pins `REDIS_URL=redis://localhost:9999/0` (unreachable) — the degraded-Redis state is the test fixture's natural condition.
- The dashboard does not call `/health`; compose healthchecks hit it (`docker-compose.yml`) — response-shape compatibility matters: `status`/`api`/`database`/`redis` keys must remain.

## In-Scope Files

- `apps/api/app/main.py` — `health()` only
- `apps/api/tests/test_health.py` (new)
- state docs + this spec

## Out-of-Scope

- worker changes (its Redis loop reconnects by design; separate concern)
- new health probes (artifact root, worker liveness) — candidates for later, not this fix
- any other endpoint; any schema/model change

## Design

- Wrap each probe independently in `try/except Exception`: probe failure → that flag `False`, never an unhandled exception.
- `status`: `"ok"` when both probes pass, `"degraded"` otherwise. Always HTTP 200 — the endpoint reports health, it doesn't have to be unhealthy itself. Callers (compose healthcheck uses HTTP success + can inspect body) keep working in the all-healthy case unchanged.
- Keys unchanged: `{"status", "api", "database", "redis"}` — strict superset behavior, no consumer breakage.

## Acceptance Criteria

- Redis down → 200 with `redis: false`, `database: true`, `status: "degraded"` — evidence: `test_health_degraded_redis` (uses the conftest env where Redis is unreachable).
- All healthy → 200 with all-true and `status: "ok"` — evidence: `test_health_all_ok` (Redis ping monkeypatched/faked to succeed).
- DB down → 200 with `database: false`, `status: "degraded"` — evidence: `test_health_degraded_database` (engine connect patched to raise).
- No unhandled exception path remains in `health()` — evidence: code review + the three tests above never observe a 500.
- Existing suite stays green (52 + new) — evidence: pytest exit 0.
- Loop closure recorded — evidence: state docs cite Alpha finding #1 as closed by this package.

## Verification Plan

Level 2: ruff/compileall/pytest. Level 4 (local): Orchestrator boots uvicorn without Redis and curls `/health` live (the exact reproduction from the alpha run must now return 200/degraded); optionally re-run with local redis-server to confirm all-true unchanged. Level 3: GitHub CI; merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): fix + tests. Orchestrator (Fable): spec, independent live re-verification (same probe as the alpha run), PR, merge gate.

## Board Linkage

- Plane: AOS-13 (In Progress, high), Sprint 4 cycle `b0547f2d-1d11-4fc4-a21b-a0169fd9d92b`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
