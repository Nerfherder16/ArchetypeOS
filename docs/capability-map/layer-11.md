## Layer 11: Runtime and Infrastructure

Owns deployment and execution environment.

Capabilities:

- Windows 11 host runtime
- WSL 2 Ubuntu runtime target
- WSL filesystem layout
- WSL Docker runtime verification
- CasaOS or Portainer deployment
- Docker Compose
- Postgres
- Redis
- API
- worker
- per-type job-handler registry (AOS-WORKER-HANDLERS-001, finding P1-1: one module per job type under `apps/worker/app/handlers/`, each exporting an immutable `HandlerSpec` with capability/sensitivity/timeout/retry/idempotency-strategy/result-schema — adding a job type adds a module, never edits a shared `worker.py` block)
- durable job execution (AOS-JOBS-RELIABILITY-001, RFC-0014: transactional outbox for atomic origination, leased claims + reaper for crash recovery, handler idempotency via unique origin job_id, dead-letter after retry budget, reconciliation sweep — at-least-once delivery with exactly-once effect)
- fenced job leases (AOS-JOB-FENCING-001: a monotonic per-claim `claim_token` fences every worker-side transition — renew/complete/fail/retry are compare-and-swaps on the token, so a stale worker that lost its lease can no longer overwrite a job another worker reclaimed; a `LeaseRenewer` thread renews long-running handlers and stops in a `finally`; `HandlerSpec.timeout_seconds` is enforced at runtime via SIGALRM, `max_attempts` drives fenced retry/dead-letter through the durable outbox, and `result_schema` is validated before completion — closing the gap LES-033 named where the lease existed but was not a fence and the handler metadata was inert; two-worker race + stale-completion rejection are proven against PostgreSQL, not only SQLite)
- reliable scheduling (AOS-SCHEDULER-RELIABILITY-001, finding P0-2: ScheduleFire unique on (schedule_id, nominal_fire_at) fires each occurrence exactly once across replicas/retries; FOR UPDATE SKIP LOCKED single-firer on Postgres; nominal cadence with coalesced catch-up so ticks never drift or replay a backlog)
- mandatory authority envelope (AOS-AUTHORITY-ENVELOPE-001, finding P0-6: a high-impact action (write/deploy/destructive/sensitive egress) must carry an authorized ActionRequest; the job-origination chokepoint refuses an ungated high-impact action, so the authority evaluator is a structural gate rather than advisory; low-impact read_only jobs auto-authorize and are unchanged)
- web dashboard
- GPU node
- WSL node
- concurrency-safe node registry (AOS-NODE-CONSTRAINTS-001, finding P1-3: unique node name, unique (node_id, capability), and a partial unique index for one global (routine, NULL) audit heartbeat — the uniqueness the query-then-insert services relied on)
- per-node service identity (AOS-NODE-IDENTITY-001, finding P0-5: operator-approved enrollment issues a hashed bearer credential; heartbeat requires the node token (X-Node-Token) so a client can no longer report false health; self-register is non-escalating — only enrollment grants write_access / a higher max_sensitivity; credentials rotate and revoke)
- operator authentication boundary (AOS-AUTH-BOUNDARY-001: a single reusable `require_operator` dependency gates every operator-owned control-plane mutation — node enrollment, credential rotation (`POST /nodes/{id}/rotate-credential`), revocation (`POST /nodes/{id}/revoke-credential`), and authority approve/reject — with a constant-time `X-Operator-Token` and the approver's `X-Operator-Id` recorded as the actor; `auth_dev_mode` defaults open for the local/tailnet box but the shipped docker-compose sets `AUTH_DEV_MODE=false`, so a DEPLOYED profile with no operator secret FAILS CLOSED (503) instead of silently running open; an already-enrolled node can only be re-registered with its own node token, so an anonymous client can no longer replace an enrolled node's capabilities; the connector-write and audit-heartbeat soft gates are now constant-time too — closing the LES-033 gap that node enrollment and authority approval were unauthenticated)
- capability-aware node routing (AOS-NODE-AGENT-001, finding P1-2: the worker registers itself as a node with its handler capabilities and heartbeats; route_job / GET /nodes/route choose an eligible node by capability ∈ node capabilities, job sensitivity ≤ node ceiling, write requirement ≤ node policy, and fresh health — with a deterministic Control-Tower explanation of why a job routes to a given node. Remote HTTPS execution across machines is a follow-up)
- node-enforced job execution (AOS-NODE-EXECUTION-001: routing is now on the execution path, not advisory. A job persists its server-derived requirements (`required_capability`/`sensitivity`/`requires_write`, from the `job_requirements` registry — never the client) and its routing decision (`assigned_node_id`/`routing_status`/`routing_explanation`/`routed_at`), computed at origination in `enqueue_job`. The worker claims through `claim_job_for_node`, whose compare-and-swap is gated on `assigned_node_id ∈ (NULL, this node)` AND re-validates capability/sensitivity/write/health at claim time — so a job routed to another node cannot be claimed even if its id is delivered to a different worker (the global-queue bypass is closed at the claim), and all the WP1 `claim_token` fencing still holds. Unknown sensitivity FAILS CLOSED via a shared `Sensitivity` enum (`sensitivity_rank` ranks an unknown value above every ceiling; `/nodes/route` 422s it) instead of the old fail-open `_rank`→0=public. A job with no eligible node stays visibly `queued`/`no_eligible_node` — never lost — and the reconciler's `reroute_waiting_jobs` sweep assigns it once a node becomes eligible and re-routes jobs whose assigned node went stale; node-failure mid-execution is recovered by the WP1 lease reaper. Proven with multi-node PostgreSQL concurrency tests; per-node delivery queues remain a follow-up (the claim is the enforcement point))
- GitHub integration
- database schema migrations (Alembic)
- unified connector runtime (AOS-CONNECTOR-RUNTIME-001, finding P0-4: the free-LLM-pool "configured" bit reads the same per-provider env keys the worker's pool is built from, so API and worker agree; GET /connectors is read-only; reachability is an active TCP probe separate from credential-present; sync moved to POST /connectors/reconcile)
- static web deployment (AOS-WEB-DEPLOY-001, finding P1-5: a multi-stage image builds the Vite SPA to static assets served by Caddy behind a single-origin /api reverse proxy — replacing the Vite dev server; relative baked API base fixes the tailnet base-URL fragility of LES-L04; immutable-asset + no-cache-index cache policy + a /healthz check)
- reproducible web build (AOS-WEB-LOCK-001: the build stage runs `npm ci` from the committed `package-lock.json` on the glibc `node:22-slim` image, NOT alpine/musl — npm records only the host platform's Rollup native in the lockfile (`@rollup/rollup-linux-x64-gnu`), so a musl `npm ci` hit npm/cli#4828 ("Cannot find module @rollup/rollup-linux-x64-musl"), which the old build worked around by deleting the lockfile + `npm install` — making every build resolve dependencies afresh; building on glibc matches the locked gnu binary and the CI ubuntu runner, so two builds from one commit resolve the same graph; CI web jobs use `npm ci`; a `scripts/check-lockfile.mjs` guard asserts lockfileVersion ≥ 3, name/version sync, and the required Rollup native so the regression cannot silently return; the Caddy serve stage, /api proxy, SPA fallback, and /healthz are unchanged)

Primary artifacts:

- docs/WSL_WIN11_RUNTIME_TARGET.md
- docs/DISTRIBUTED_RUNTIME.md
- docs/LOCAL_LLM_GPU_NODE.md
- docs/CLAUDE_CODE_BRIDGE.md
- docs/CONNECTOR_POLICY.md (AOS-CONNECTOR-001: connector registry governance — privacy class, egress, browser-exposed, health)
- docs/DATABASE_MIGRATIONS.md
- docker-compose.yml
- .env.example
- apps/web
- apps/api
- apps/api/alembic/ (Alembic migrations; baseline schema)
- apps/api/docker-entrypoint.sh (runs migrations before serving)
- apps/worker
- apps/scheduler (control-plane scheduler: materializes due schedules into jobs; RFC-0007)
- packages/aos_core (shared domain library: config/database/models/scanner + scan/digest/jobs/scheduler services; RFC-0006)
- docs/rfc/RFC-0006-Shared-Core-Domain-Library.md
- docs/rfc/RFC-0007-Scheduling-Control-Plane-Job-Origination.md (schedules-as-data; control plane decides + stores, nodes execute)
- docs/rfc/RFC-0014-Durable-Job-Execution-Outbox-Leases-Idempotency.md (AOS-JOBS-RELIABILITY-001: durable jobs — outbox, leases, idempotency, dead-letter, reconciliation)

