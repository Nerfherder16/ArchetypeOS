# AOS-RES-001 — Research Inbox (Research)

## Summary

Turn the Research-mode **"Research Inbox"** surface (a disabled "soon" stub from AOS-UI-007) into a
**live inbox of the portfolio's research notes** — the evidence-dossier surface from the mock — by
aggregating every project's research notes into one ranked list. **Frontend only** — it composes
existing endpoints.

## Why frontend-only

`ResearchNote` (`id`, `title`, `summary`, `freshness`, `confidence`) is real, and
`GET /projects/{id}/research-notes` + `fetchResearchNotes(projectId)` + `fetchProjects()` already
exist. The inbox aggregates client-side (like "Awaiting You" / "Live Activity"): projects →
per-project notes → merge → rank. The Research Engine's ranked-web-dossiers are a separate future
capability; this surfaces the research notes the platform already stores.

## Design

### The surface

- `apps/web/src/shell/workspaces.ts` — flip the Research `research-inbox` surface
  `status:'soon'` → `status:'live', view:'research'` (keep id + label "Research Inbox").
- `apps/web/src/shell/Shell.tsx` — add `'research'` to `ViewId`.
- `apps/web/e2e/support/nav.ts` — add `'research'` to its `ViewId`.
- `apps/web/src/main.tsx` — `renderView()` gains `case 'research': return <ResearchInboxView />;`.

### `apps/web/src/features/research/ResearchInboxView.tsx`

Mirror the aggregate-across-projects pattern (`features/approvals/ApprovalsView.tsx`) + the
`.aos-view`/`.aos-card` vocabulary.

- **Load**: `fetchProjects()` → `Promise.allSettled(projects.map(p => fetchResearchNotes(p.id)))`;
  flatten fulfilled, tag each note with its project name; a per-project failure is skipped. **Rank
  by confidence desc** (tie-break: keep project grouping stable). Show a total count + "across N
  projects".
- **Card per note**: title · project · a **confidence signal meter** (reuse `.aos-bars`/a pill;
  e.g. confidence → a 0–1 strength meter) · a **freshness pill** when present (`freshness` string,
  e.g. `.aos-pill info`) · the summary text (clamped). Keep it scannable.
- **States**: loading; **graceful error** (top-level `fetchProjects` fails → readable notice);
  **empty** (no notes → "No research yet — notes captured for your projects will collect here").
- testids: root `research-view`, a note card `research-note-card`, `research-empty`,
  `research-error`.
- Respect `prefers-reduced-motion`.

## Non-goals

- The Research Engine's web-sourced ranked dossiers / source-quality ladder / continuous-research
  signals (planned engines — not built here). Footnote it.
- Creating/editing notes (the Council view already has an add-research-note form). Read-only inbox.
- Any backend/API/schema change. **Frontend only. No new dependencies.**

## Tests (`apps/web/e2e/research-view.spec.ts`)

- Research mode → the "Research Inbox" surface is **live** and routes to it (`nav-research` →
  `research-view`).
- Mounts with heading even when API absent (graceful loading→error/empty; no uncaught error).
- Route-stub `GET /projects` + `GET /projects/{id}/research-notes` with a few notes of varied
  confidence → assert `research-note-card`s render ranked by confidence; else assert graceful
  empty/error. Mirror the existing view-spec harness.
- Existing suite stays green; `nav-research` added, no existing testid changed.

## Acceptance criteria

1. The Research "Research Inbox" entry is **live** and opens the inbox.
2. Aggregates research notes across projects, ranked by confidence, with title/project/confidence
   meter/freshness/summary.
3. Loading / empty / API-down states degrade gracefully.
4. `npm run build` clean; full Playwright suite green incl. the new spec; PR Guardian PASS.

## Verification plan (Orchestrator)

- `npm run build` clean; full `npx playwright test` green.
- Real-app screenshots: empty/API-down + a route-stubbed populated inbox (ranked notes).

## Risk / effort

- **Risk**: low. Frontend-only, composes existing endpoints; no seam contention.
- **Effort**: ~1 focused build cycle. One PR (UI → auto-merge on green).
