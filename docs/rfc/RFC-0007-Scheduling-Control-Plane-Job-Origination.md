# RFC-0007 — Scheduling & Control-Plane Job Origination

## Status

Accepted (operator-directed 2026-07-05, after weighing the mature-state architecture). Governs RFC-0006 Phase 3 (AOS-SCHED-001+).

## Problem

RFC-0006 Phase 3 needs the nightly digest to run automatically. The naive option (a scheduling loop inside the worker) is a local optimum that becomes an anti-pattern against ArchetypeOS's own documented end state:

- **Distributed Runtime (roadmap Phase 5):** *"The control plane decides and stores. Nodes execute declared capabilities."* Multiple heterogeneous executors (`research_worker`, RTX 3090 LLM node, WSL workstation node) will pull jobs. A per-worker scheduling loop would fire every recurring task once **per node** → duplicate work, no single authority.
- **Continuous Research Engine + Evolution (Phase 7):** many recurring tasks at many cadences (release/CVE polling, nightly digests, monthly decision re-evaluation). A hardcoded "once a day" loop cannot express this.
- **Constitution:** "every significant decision needs memory." *When* recurring work runs is a decision; it should be a durable, inspectable artifact, not code.

The two foundations merged this sprint make the correct approach cheap: **AOS-17 (Alembic)** makes adding a `schedule` table a clean migration (its first real use), and **AOS-CORE-001 (`aos_core`)** lets a scheduler be a thin shared-core consumer like the worker.

## Decision

**Scheduling is a control-plane concern backed by schedules-as-data, decoupled from execution.**

1. **`Schedule` model** (new table, Alembic migration `0002`): a first-class row per recurring task — `{id, project_id?, name, job_type, payload, interval_seconds, enabled, last_run_at, next_run_at}` + AuditMixin. Schedules live in the control-plane Postgres; they are the durable record of "what runs when."
2. **Shared enqueue path** `aos_core.services.jobs.enqueue_job(db, client, *, job_type, project_id, repository_id, payload, priority)`: creates a `Job` row (status `queued`) and `client.lpush(QUEUE, job.id)`. One code path for job origination, used by both the API's `POST /jobs` and the scheduler. `QUEUE = "archetypeos:jobs"` moves to an `aos_core` constant (redis client stays the caller's — aos_core does not depend on redis).
3. **Scheduler service** `apps/scheduler` (new, thin, imports `aos_core`): a single-instance control-plane process. Loop: find enabled schedules with `next_run_at <= now`; for each, `enqueue_job(...)`, set `last_run_at = now`, `next_run_at = now + interval_seconds`. It DECIDES + WRITES (control plane); it never executes jobs (that's the worker/nodes). Single-instance in compose for v0.2 — HA via DB-lock/leader-election is a documented future step, not built now.
4. **Schedule CRUD API** (in `apps/api`, using `aos_core`): create/list/read/patch(enable-disable)/delete + `POST /schedules/{id}/run` (enqueue immediately). Bootstraps a nightly `project_digest` schedule per project.
5. **Dashboard** (later phase): schedules section (list, create, enable/disable, run-now), "run scan/digest as job" buttons, and job history.

### Why a dedicated `apps/scheduler` (not a worker mode)

The vision's line is decisive: the control plane **decides and stores**, nodes **execute**. The scheduler decides (materializes schedules into jobs) and writes; the worker executes. Keeping them separate processes means executors scale horizontally (and heterogeneously, per Phase 5) without any of them duplicating schedules, and the single-authority invariant is structural, not a guard bolted onto a scaled component.

## Phasing

- **AOS-SCHED-001 (backend seed, this RFC's first package):** `Schedule` model + migration `0002`; `enqueue_job` service + `QUEUE` constant in `aos_core`; Schedule CRUD API + `run` endpoint; `apps/scheduler` service + compose service; API tests (CRUD, enqueue) + a scheduler unit test (a due schedule enqueues a job and advances `next_run_at`). No dashboard.
- **AOS-SCHED-002 (dashboard):** schedules UI + enqueue buttons + job history + Playwright e2e. Closes AOS-18.
- **Later (grows on this foundation, own packages/RFCs):** per-source continuous-research schedules (Phase 5 research_worker), job routing to node types (Phase 5), monthly decision re-evaluation (Phase 7), scheduler HA (leader election).

## Alternatives considered

- **In-worker scheduling loop (Option A):** minimal now, but duplicates every recurring task once the second executor/node exists; contradicts the "control plane decides, nodes execute" split. Rejected for the mature path.
- **APScheduler in the worker:** richer cron primitives but a new dependency and still couples scheduling to an executor. Its cron-expression power can be added to `Schedule` later (a `cron` column) without changing the architecture. Deferred.
- **External/host cron on teevee-1:** not self-contained in compose, not inspectable as data, no memory. Rejected.

## Risks

- **First non-baseline migration** (`0002` adds `schedule`): validated by the AOS-17 no-drift check re-run + compose-smoke applying it on fresh Postgres; pre-existing DBs (teevee-1) upgrade cleanly (they were `stamp head`ed at `0001`).
- **New compose service** (scheduler): compose-smoke must build + boot it. Kept thin (imports aos_core, a loop) to limit blast radius.
- **Single-instance assumption:** documented; enforced operationally (one scheduler replica) until leader election lands. A duplicate scheduler would double-enqueue — noted as the reason HA is explicitly deferred, not accidental.

## Acceptance criteria (this RFC)

- Operator approved (done). AOS-SCHED-001 delivers the backend seed; AOS-SCHED-002 the dashboard, closing AOS-18.
- Schedules are DB rows; the scheduler is a separate control-plane process; job origination flows through one `aos_core` path.

## Dependencies

- AOS-17 (Alembic) — migration `0002` is the first real use.
- AOS-CORE-001 (`aos_core`) — the scheduler and shared enqueue path live here.
- Feeds RFC-0005 council (scheduled council runs), Continuous Research, Phase 7 re-evaluation — all become schedule rows.
