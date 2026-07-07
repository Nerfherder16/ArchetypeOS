# AOS-USAGE-002 — Usage surface: the Providers & Model Routing Operations view

## Summary

Turn the Operations-mode **"Providers & Model Routing"** surface (currently a disabled "soon"
stub from AOS-UI-007) into a **live view** that reads `GET /usage/summary` (shipped in
AOS-USAGE-001, #100) and renders the operator's **real LLM usage across all tiers** — Claude
subscription, local (RTX 3070), free hosted — the per-tier token/cost module from the deck mock,
now backed by real data. Frontend only.

## API contract (already live on `main`)

`GET /usage/summary?window=today|7d|30d` →

```ts
type UsageBucket = {
  input_tokens: number; output_tokens: number; total_tokens: number;
  cost_usd: number; events: number; estimated: boolean;
};
type UsageSummary = {
  window: 'today' | '7d' | '30d';
  since: string;                                   // ISO timestamp
  totals: UsageBucket;
  by_tier: { claude: UsageBucket; local: UsageBucket; free: UsageBucket };
  by_model: Array<UsageBucket & { model: string; tier: string }>;   // busiest first
};
```

Tiers are always present (zeroed when empty). `estimated: true` on any bucket means at least one
figure was length-derived (e.g. a Claude call whose envelope lacked `usage`) — surface it, never
present an estimate as exact.

## Scope

1. **`apps/web/src/api.ts`** — add `UsageBucket` / `UsageSummary` types + `fetchUsageSummary(window)`
   (mirror the existing `fetch*` helpers + `API_BASE_URL`).
2. **New view `apps/web/src/features/providers/ProvidersView.tsx`** (mirror `features/reuse/ReuseView.tsx`
   structure + `.aos-*` view vocabulary):
   - **Window selector** — today / 7d / 30d (re-fetches; default 7d).
   - **Headline** — total tokens (big, `.aos-display`) + total est. cost `$` for the window, with
     an `estimated` marker when `totals.estimated`.
   - **In/out split** — input vs output tokens.
   - **Per-tier rows** — Claude / Local / Free, each with a proportional bar (share of total
     tokens), tokens (in/out) + est. cost. Tier colors from design tokens: **Claude → `--signal`
     (cyan)**, **Local → `--lex` (blue)**, **Free → `--agent-scout` / a purple token**. A zeroed
     tier still renders (dimmed) so the operator sees all three.
   - **Per-model table** — `by_model` busiest-first: model · tier · total tokens · in/out · cost.
   - **States**: loading, **graceful error** (API down → a readable notice, no throw — mirror how
     Overview degrades), and **empty** (`totals.events === 0` → "No usage recorded yet" with a hint
     that the ledger records reasoned calls once a real provider tier is configured).
   - Respect `prefers-reduced-motion` (bar width transitions only; no looping animation).
3. **Wire the view in**:
   - `apps/web/src/shell/Shell.tsx` — add `'providers'` to `ViewId`.
   - `apps/web/src/shell/workspaces.ts` — change the operations surface
     `{ id: 'providers-routing', label: 'Providers & Model Routing', status: 'soon' }` →
     `status: 'live', view: 'providers'`. Keep its position (after the live command/digest/scheduling
     entries is fine).
   - `apps/web/src/main.tsx` — `renderView()` gains `case 'providers': return <ProvidersView />;`.
   - `apps/web/e2e/support/nav.ts` — add `'providers'` to its `ViewId`.

## Non-goals

- No change to `GET /usage/summary` or any backend (the contract is fixed by #100).
- No budget/quota concept (the API has no budget; the mock's "% of budget" meter is **not** built
  here — only real totals/cost). A budget feature would be a separate package + API field.
- No historical charts/time-series (the summary is windowed aggregates); a sparkline is a later
  increment.
- No new dependencies (Canvas/CSS bars only; no chart lib).

## Tests

- **`apps/web/e2e/providers-view.spec.ts`** — Operations mode → the "Providers & Model Routing"
  surface is now **live** (not a `soon-*` disabled item) and routes to it (`nav-providers`); the
  view mounts (`data-testid="providers-view"`) with its heading + window selector even when the API
  is absent (graceful loading→error/empty, no uncaught error); switching the window control issues a
  re-fetch (assert the control works). Mirror the existing view-spec harness (see `reuse.spec.ts` /
  how views behave without a seeded backend). If the e2e harness seeds the API, additionally assert
  a tier row renders; otherwise assert the graceful empty/error surface.
- Existing suite stays green; `nav-providers` added, no existing testid changed.

## Acceptance criteria

1. The Operations "Providers & Model Routing" entry is **live** and opens the usage view (no longer
   a "soon" stub).
2. The view renders totals (tokens + est. cost), in/out split, all three tier rows (zeroed tiers
   dimmed), and the per-model table from `GET /usage/summary`, with a window selector (today/7d/30d).
3. `estimated` is surfaced (never shown as exact); API-down and empty states degrade gracefully
   (no uncaught errors / no white screen).
4. `npm run build` clean; full Playwright suite green incl. the new spec; PR Guardian PASS.

## Verification plan (Orchestrator, independent — builder ≠ verifier)

- `npm run build` clean; full `npx playwright test` green.
- Real-app screenshots of the Providers view: (a) empty/API-down state (static preview has no
  backend), and — if feasible — (b) a seeded state via a stubbed `fetchUsageSummary` to confirm the
  tier bars + per-model table + estimated marker render.
- Confirm the surface is reachable from Operations and the window selector switches.

## Risk / effort

- **Risk**: low. Frontend-only, additive view on a fixed API contract; no seam contention. Main
  care is graceful degradation without a backend (the static preview / e2e path).
- **Effort**: ~1 focused build cycle. One PR. Completes the "real Claude usage on the dashboard"
  arc the operator asked for.
