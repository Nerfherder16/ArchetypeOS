# AOS-OPS-002 — Live Activity feed (Operations)

## Summary

Turn the Operations-mode **"Live Activity"** surface (a disabled "soon" stub from AOS-UI-007) into
a **live feed of real system activity** — the audit-stream panel from the deck mock — by
aggregating the platform's **Jobs** (scans, digests, council reviews, scheduled runs) across all
projects into one time-ordered stream. **Frontend only** — it composes existing endpoints.

## Why jobs, why frontend-only

`Job` is the real, timestamped record of platform work: it carries `job_type`, `status`, and
`queued_at`/`started_at`/`finished_at` (all exposed in `JobRead` and the frontend `Job` type), and
`GET /projects/{id}/jobs` + `fetchJobs(projectId)` + `fetchProjects()` already exist. The feed
aggregates client-side (like the "Awaiting You" queue): projects → per-project jobs → merge →
sort by timestamp. Council-verdict / decision-status events are a **future enrichment** — their
`Read` schemas don't yet expose `created_at`, so a richer feed needs a backend timestamp or a
dedicated `GET /activity` endpoint (noted, not built).

## Design

### The surface

- `apps/web/src/shell/workspaces.ts` — flip the Operations `live-activity` surface
  `status:'soon'` → `status:'live', view:'activity'` (keep id + label "Live Activity").
- `apps/web/src/shell/Shell.tsx` — add `'activity'` to `ViewId`.
- `apps/web/e2e/support/nav.ts` — add `'activity'` to its `ViewId`.
- `apps/web/src/main.tsx` — `renderView()` gains `case 'activity': return <ActivityView />;`.

### `apps/web/src/features/activity/ActivityView.tsx`

Mirror the `.aos-view` vocabulary + the aggregate-across-projects pattern from
`features/approvals/ApprovalsView.tsx`.

- **Load**: `fetchProjects()` → `Promise.allSettled(projects.map(p => fetchJobs(p.id)))`; flatten
  fulfilled results, tag each job with its project name; a per-project failure is skipped (never
  fails the whole feed). Sort **newest first** by `finished_at ?? started_at ?? queued_at`. Cap at
  ~50 rows (state the cap in the UI when truncated — no silent truncation).
- **Event row** (mono, dense, feed-like): timestamp (HH:MM:SS) · a **status pill** (map defensively:
  `done`/`complete`/`succeeded` → good/`--signal`; `running`/`started` → info; `queued`/`pending`
  → neutral; `failed`/`error` → risk/`--red`) · the `job_type` (human-labeled, e.g. `scan` →
  "Scan", `council_review` → "Council review", `digest` → "Digest") · project name · a short error
  snippet when `status` is failed (from `job.error`).
- **A window/scope note**: header shows a total count + "across N projects".
- **States**: loading; **graceful error** (top-level `fetchProjects` fails → readable notice, no
  throw); **empty** (no jobs → "No activity yet — scans, digests, and council runs will stream
  here").
- testids: root `activity-view`, a row `activity-row`, `activity-empty`, `activity-error`.
- Respect `prefers-reduced-motion` (the mock's slide-in is optional; keep it subtle or omit).

## Non-goals (deferred)

- Council-verdict / decision-status / lesson / scan-detail events (need `created_at` on those Read
  schemas, or a `GET /activity` endpoint) — noted in a footnote.
- Real-time streaming / websockets (this is a polled snapshot; a manual Refresh is fine).
- Any backend/API/schema change. **Frontend only. No new dependencies.**

## Tests (`apps/web/e2e/activity-view.spec.ts`)

- Operations mode → the "Live Activity" surface is **live** (not a `soon-*` item) and routes to it
  (`nav-activity` → `activity-view`).
- The view mounts with its heading even when the API is absent (graceful loading→error/empty; no
  uncaught error).
- Route-stub `GET /projects` + `GET /projects/{id}/jobs` with a few jobs of varied `job_type` +
  `status` → assert `activity-row`s render newest-first with the right status pills (incl. a failed
  row showing its error); otherwise assert the graceful empty/error surface. Mirror the existing
  view-spec harness.
- Existing suite stays green; `nav-activity` added, no existing testid changed.

## Acceptance criteria

1. The Operations "Live Activity" entry is **live** and opens the feed.
2. The feed aggregates jobs across projects, newest-first, with type + status pill + project +
   failed-error snippet; a truncation note appears if capped.
3. Loading / empty / API-down states degrade gracefully (no uncaught errors / white screen).
4. `npm run build` clean; full Playwright suite green incl. the new spec; PR Guardian PASS.

## Verification plan (Orchestrator, independent — builder ≠ verifier)

- `npm run build` clean; full `npx playwright test` green.
- Real-app screenshots: (a) empty/API-down state; (b) a route-stubbed populated feed (mixed
  job types + a failed row).

## Risk / effort

- **Risk**: low. Frontend-only, composes existing endpoints; no seam contention. Care: graceful
  degradation + N×fetch aggregation (skip failed projects) + a defensive status→pill map.
- **Effort**: ~1 focused build cycle. One PR (UI → auto-merge on green per operator standing OK).
