# AOS-SCHED-002 — Scheduler Dashboard: Schedules UI + Enqueue + Job History (RFC-0007 / RFC-0006 Phase 3b)

## Status

In Progress

## Origin

RFC-0007 second package; RFC-0006 Phase 3b — the dashboard surface for the scheduler seed (AOS-SCHED-001). **Closes AOS-18** and the worker pipeline: the operator can create/manage schedules, enqueue scans/digests as jobs on demand, and watch job history — all through the control tower. Sprint 5 package 6.

## Verified Baseline

Confirmed by inspection:

- Schedule CRUD API exists (AOS-SCHED-001): `POST/GET /projects/{id}/schedules`, `GET/PATCH/DELETE /schedules/{id}`, `POST /schedules/{id}/run`. `ScheduleRead` in schemas.
- Jobs: `POST /jobs` + `GET /jobs/{id}` only — **no list endpoint**. `JobRead` schema exists (`id, project_id, repository_id, job_type, status, priority, payload, result, error, queued_at, started_at, finished_at, attempts`).
- Dashboard (`apps/web/src/main.tsx`) has sections (Runtime Health, Projects, Repositories, Scan Summary, Architecture, Decisions & Research, Nightly Digest) following a pattern: `api.ts` fetch/create functions + a section with lists/forms + per-section error isolation. `apps/web/e2e/` has the Playwright suite (guardian enforces a web-src change ships with an e2e change).
- Selected-project state drives the sections; forms locate fields by exact placeholder (drives/e2e depend on this).

## In-Scope Files

- `apps/api/app/main.py` (`GET /projects/{id}/jobs`), `apps/api/tests/test_jobs_api.py` (new — list endpoint)
- `apps/web/src/api.ts` (schedule + job + enqueue functions + types), `apps/web/src/main.tsx` (Scheduling & Jobs section)
- `apps/web/e2e/scheduling.spec.ts` (new)
- state docs + this spec (fold PR #47 reconciliation in)

## Out-of-Scope

- new scheduler/worker behavior (AOS-SCHED-001 delivered it); cron cadences; schedule editing beyond enable/disable + interval; auth
- the `test`/other job types in the UI (surface `repository_scan` + `project_digest` enqueue; schedules allow those two)

## Design

- **API**: `GET /projects/{project_id}/jobs` → recent jobs for the project (desc by `queued_at`, cap ~50), `response_model=list[JobRead]`. 404 if project missing (match conventions). Read-only.
- **`api.ts`**: types `Schedule`, `Job`; functions `fetchSchedules(projectId)`, `createSchedule(projectId, {name, job_type, interval_seconds})`, `setScheduleEnabled(scheduleId, enabled)` (PATCH), `deleteSchedule(scheduleId)`, `runSchedule(scheduleId)` (POST run), `enqueueJob({project_id, repository_id?, job_type})` (POST /jobs), `fetchJobs(projectId)`.
- **`main.tsx`** — new "Scheduling & Jobs" section for the selected project:
  - Schedules list: name, job_type, interval (seconds), enabled, next_run_at; per row an enable/disable toggle, Run now, Delete.
  - Create-schedule form: placeholders `Schedule name`, a job_type select (`repository_scan` / `project_digest`), `Interval seconds`; Create Schedule button.
  - Enqueue-now controls: "Run digest as job" button (enqueue `project_digest` for the project); a repo select + "Run scan as job" (enqueue `repository_scan` for the chosen repo).
  - Job history list: recent jobs (job_type, status, queued_at, attempts). A Refresh button.
  - Per-section error isolation like the others.
- **e2e `scheduling.spec.ts`**: project + (for scan) a repo; create a schedule (name + project_digest + small interval) → appears in the list; click Run now → a job appears in Job history; assert. Reuse the `serve-api.sh` stack (the scheduler container isn't needed — Run now enqueues via the API, and the test asserts the Job row/queued state, not worker execution).

## Acceptance Criteria

- Jobs list endpoint — evidence: `test_list_project_jobs` (create jobs → GET returns them desc; unknown project 404).
- Schedules manageable from the UI — evidence: e2e `scheduling.spec.ts` creates a schedule, it lists; enable/disable + delete work (assert list updates).
- Enqueue-now works from the UI — evidence: e2e Run-now (schedule) → a job appears in history; "Run digest as job" enqueues.
- Job history renders — evidence: e2e asserts a job row (job_type + status) after enqueue.
- Build/type safety — evidence: strict `tsc` + `vite build` exit 0.
- Nothing broken — evidence: api suite (75 + new) green; worker 6; ruff/compileall; the existing e2e specs still pass.
- Closes AOS-18 — evidence: on merge, AOS-18 → Done (Phase 3 complete).

## Verification Plan

Level 2: ruff/compileall/pytest (api + worker). Level 4 (local): Orchestrator runs the full Playwright suite headless (`PW_LOCAL_CHROMIUM` seam) incl. the new `scheduling.spec.ts`. Level 3: CI api-tests + web-e2e (the new spec runs on ubuntu) + compose-smoke. Merge under the Manual Merge Gate; then AOS-18 Done.

## Suggested Delegation

Runtime Agent (Opus): jobs endpoint + api.ts + main.tsx section + e2e spec + api test. Orchestrator (Opus 4.8): spec, independent headless Playwright run of the new spec, api re-run, PR, gate, AOS-18 close-out.

## Board Linkage

- Plane: AOS-18 (In Progress — Phase 3b of 3; **this package closes it**), Sprint 5 cycle `8bc59801-82c5-4550-b188-9f15323a1ddc`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`; RFC: `docs/rfc/RFC-0007-Scheduling-Control-Plane-Job-Origination.md`
