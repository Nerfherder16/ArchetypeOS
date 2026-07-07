# AOS-GOV-001 — "Awaiting You" governance queue (Approvals surface)

## Summary

Turn the Council-mode **"Approvals & Authority"** surface (a disabled "soon" stub from AOS-UI-007)
into a **live "Awaiting You" governance queue** — the human-in-the-loop panel from the deck mock —
that aggregates every **pending Decision** (`draft` / `needs_evidence`) across the operator's
projects into one place and lets the operator **approve / reject** each with a named approver.
This is the operator's core job: ArchetypeOS runs read-only + human-approval, and this surface is
where that approval happens. **Frontend only** — it composes existing endpoints.

## Why frontend-only

The decision loop is already fully wired in the API (per-project):
`GET /projects/{id}/decisions`, `POST /decisions/{id}/approve` (named approver), `POST
/decisions/{id}/reject`, and `GET /projects` (`fetchProjects`). The queue aggregates client-side:
fetch projects → fetch each project's decisions → keep the ones in `draft` / `needs_evidence`.
A dedicated `GET /decisions/pending` endpoint is a **future optimization** (noted, not built —
the operator's portfolio is small; N+1 is fine and avoids backend/seam churn).

## Design

### The surface

- `apps/web/src/shell/workspaces.ts` — flip the Council surface
  `{ id:'approvals-authority', label:'Approvals & Authority', status:'soon' }` →
  `{ id:'approvals-authority', label:'Awaiting You', status:'live', view:'approvals' }`
  (keep the id; relabel to the operator-facing "Awaiting You").
- `apps/web/src/shell/Shell.tsx` — add `'approvals'` to `ViewId`.
- `apps/web/e2e/support/nav.ts` — add `'approvals'` to its `ViewId`.
- `apps/web/src/main.tsx` — `renderView()` gains `case 'approvals': return <ApprovalsView />;`.

### `apps/web/src/features/approvals/ApprovalsView.tsx`

Mirror the `.aos-view` vocabulary + the existing decision UI in the Council view (reuse the
`.aos-pill` decision-status tiers already defined).

- **Load**: `fetchProjects()` → for each project `fetchDecisions(project.id)`; keep decisions with
  `status ∈ {draft, needs_evidence}`; tag each with its project id + name. A per-project fetch
  failure is skipped (does not fail the whole queue). Show a count badge of the total pending.
- **Card per pending decision** (most-actionable first — `draft` before `needs_evidence`):
  project name · title · confidence · evidence count · a **status pill** (`draft` = actionable,
  `needs_evidence` = blocked — distinct render, e.g. `.aos-pill warn`).
  - **Approve**: enabled only for `draft`. Requires a **named approver** — a small text input
    (default the operator handle if one is readily available, else empty; required). Calls
    `approveDecision(id, approver)`; on success remove the card + decrement the count. A
    `needs_evidence` decision's Approve is **disabled** with a readable reason ("needs evidence —
    assemble evidence before approval", mirroring the LES-019 409 the API enforces).
  - **Reject**: enabled for both `draft` and `needs_evidence`; calls `rejectDecision(id, approver?)`.
  - **Open**: a link/affordance to the project's Council & Decisions view for full context
    (optional — a `nav`-style jump; if trivial, route to `council` for that project; otherwise
    omit and note it).
- **States**: loading; **graceful error** (projects/decisions fetch fails → readable notice, no
  throw / white screen — mirror how other views degrade); **empty** (no pending → "Nothing awaiting
  you — the council queue is clear").
- testids: root `approvals-view`, a pending card `approval-card`, `approval-approve`,
  `approval-reject`, `approval-approver` (the name input), `approvals-empty`, `approvals-error`.
- Respect `prefers-reduced-motion` (no new looping motion).

## Non-goals (deferred)

- The broader **Approvals & Authority** vision (action-level authority gating 0–5, temporary
  grants, audit search, **Emergency Stop**) — this package is the **decisions-approval slice** only.
  Note that in the surface (a small "authority controls coming soon" footnote is fine).
- A cross-project `GET /decisions/pending` endpoint (future optimization).
- PR Guardian gates / risk signals in the queue (the mock's other "Awaiting You" rows) — those
  need their own data sources; this package is decisions only. Note it.
- Any backend/API/schema change. **Frontend only. No new dependencies.**

## Tests (`apps/web/e2e/approvals-view.spec.ts`)

- Council mode → the "Awaiting You" surface is **live** (not a `soon-*` disabled item) and routes
  to it (`nav-approvals` → `approvals-view`).
- The view mounts with its heading even when the API is absent (graceful loading→error/empty; no
  uncaught error).
- If the e2e harness seeds projects+decisions, assert a pending `approval-card` renders and a
  `needs_evidence` card's Approve is disabled; otherwise assert the graceful empty/error surface.
  Mirror the existing view-spec harness (`reuse.spec.ts` / `providers-view.spec.ts`).
- Existing suite stays green; `nav-approvals` added, no existing testid changed.

## Acceptance criteria

1. The Council "Awaiting You" (was "Approvals & Authority") entry is **live** and opens the queue.
2. The queue aggregates `draft` + `needs_evidence` decisions across projects; `draft` are
   approvable with a named approver; `needs_evidence` show Approve disabled with the evidence
   reason; both are rejectable. Actions call the existing endpoints and update the list.
3. Loading / empty / API-down states degrade gracefully (no uncaught errors / white screen).
4. `npm run build` clean; full Playwright suite green incl. the new spec; PR Guardian PASS.

## Verification plan (Orchestrator, independent — builder ≠ verifier)

- `npm run build` clean; full `npx playwright test` green.
- Real-app screenshots: (a) empty/API-down state; (b) a route-stubbed populated queue (a `draft`
  card approvable + a `needs_evidence` card with Approve disabled) to confirm the render + action
  affordances.

## Risk / effort

- **Risk**: low. Frontend-only, composes existing endpoints; no seam contention. Main care is
  graceful degradation + the N+1 aggregation (skip failed projects).
- **Effort**: ~1 focused build cycle. One PR.
