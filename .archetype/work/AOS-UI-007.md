# AOS-UI-007 — Workspace-mode shell + resolution-adaptive layout

## Summary

Layer two structural capabilities onto the existing rail shell (`apps/web/src/shell/Shell.tsx`),
keeping the current `.aos-*` blue+red design system unchanged:

1. **Workspace modes** — a top-level organizing level in the rail. The 8 shipped views are
   grouped under 6 workspace modes (Operations, Council, Architect, Research, Executive,
   Builder), per `docs/WORKSPACE_LAYOUT_ENGINE.md`. Planned-but-unbuilt surfaces appear as
   disabled **"soon"** entries so the full system structure from the surface map is visible
   and honest.
2. **Resolution-adaptive layout** — four responsive tiers so the same shell adapts across
   devices: **Command Wall** (≥2200px, G9 57" 32:9), **Desktop** (1180–2199px), **Tablet**
   (720–1179px), **Phone** (<720px).

This is a **strict subset** of the mature-state target (a moded, resolution-adaptive,
neon-red command deck with an orb Operations-home). This PR is **structure + responsiveness
only**: no palette change, no neon re-skin, no canvas orb. Those are follow-up packages.

## Non-goals (explicitly deferred)

- The black→neon-red palette migration (own package; a token migration touching every view).
- The canvas orb / voice command-deck as the Operations home (own package).
- Restyling any view's interior. Views render as-is inside the new shell.
- Building any "soon" surface. They are disabled placeholders only.
- Any API/backend/schema change. **Frontend only. No new dependencies.**

## Design

### Surface + mode registry (new module: `apps/web/src/shell/workspaces.ts`)

Define the mode + surface model as data:

```ts
export type WorkspaceModeId =
  | 'operations' | 'council' | 'architect' | 'research' | 'executive' | 'builder';

export type Surface = {
  id: string;              // stable slug, e.g. 'research-inbox'
  label: string;
  status: 'live' | 'soon';
  view?: ViewId;           // present iff status === 'live'
  note?: string;           // one-line mono subtitle (optional)
};

export type WorkspaceMode = {
  id: WorkspaceModeId;
  label: string;           // e.g. 'Operations'
  focus: string;           // one-line description
  surfaces: Surface[];
};
```

Mode → surface mapping (live surfaces reuse the existing 8 `ViewId`s; everything else `soon`):

- **operations** — *"Command home — live ops."*
  - Digest → `digest` (live), Scheduling → `scheduling` (live)
  - soon: Command home, Observatory, Live Activity, Nodes / Runtime, Providers & Model Routing, Claude Code Bridge
- **council** — *"Deliberation & governance."*
  - Council & Decisions → `council` (live)
  - soon: Final Judge, PR Guardian Gate, Approvals & Authority, Work Packages, Orchestration
- **architect** — *"System structure & choices."*
  - Repositories → `repositories` (live), Architecture → `architecture` (live), Reuse → `reuse` (live)
  - soon: Digital Twin, Tech Fitness, Recommendations
- **research** — *"Evidence & knowledge."*
  - Knowledge → `knowledge` (live)
  - soon: Research Inbox, Signals / Ecosystem Watch, Knowledge Graph, Distillation, Docs / Freshness, Marketplace
- **executive** — *"Portfolio & strategy."*
  - Overview → `overview` (live)
  - soon: Portfolio Intelligence, Evolution Scorecards, Strategy Planner, Reports
- **builder** — *"Execution."* (no live surfaces yet)
  - soon: Claude Code Session, Creation Loop, Test results / CI, Simulation Lab

Helper exports: `WORKSPACE_MODES: WorkspaceMode[]`, `modeForView(view: ViewId): WorkspaceModeId`
(returns the mode whose surfaces contain a live surface with that view), and
`firstLiveView(mode: WorkspaceModeId): ViewId | undefined`.

### Shell restructure (`Shell.tsx`)

- New rail structure: **brand → mode switcher → active mode's surface list → project foot.**
- Props change: replace the flat `navItems: NavItem[]` with the mode model. Shell owns the
  **active mode** state, derived initially from the incoming `activeView`
  (`modeForView(activeView)`). Keep `activeView` + `onNav` as the view-routing contract (App
  still owns view state).
- **Mode switcher**: a compact segmented control of the 6 modes.
  - `data-testid="mode-<id>"`, `aria-pressed` on the active mode, keyboard operable.
  - Clicking a mode: set active mode; if it has a live surface, call `onNav(firstLiveView(mode))`
    so the workspace follows; if it has none (builder), leave `activeView` unchanged and the
    workspace shows the empty-state (below).
- **Surface list** (the active mode's surfaces):
  - `live` → a nav button, **preserving `data-testid="nav-<view>"`** (e2e compatibility),
    `aria-current="page"` when active, routes via `onNav`.
  - `soon` → a disabled item with a `.aos-nav-soon` "soon" chip; `disabled`, `aria-disabled`,
    not focusable-as-link, `data-testid="soon-<surface.id>"`.
- **Breadcrumb**: `Engineering Control Tower / <Mode label> / <View label>`.
- **Empty state**: when the active mode has no live surface (builder), the workspace shows a
  small centered `.aos-empty` panel — mode name + "This workspace is coming soon" + the list
  of planned surfaces. Provide this from Shell (it can render children OR the empty state);
  simplest: App passes children as today, and Shell renders the empty-state instead of
  `children` when `firstLiveView(activeMode)` is undefined AND `activeView` is not in the mode.
  (Keep it simple and deterministic.)

### `main.tsx`

- Remove `NAV_ITEMS`; import `WORKSPACE_MODES` + helpers and pass the mode model to `Shell`.
- Keep `activeView` default `'overview'` (so the app still lands on Overview → Executive mode;
  preserves existing e2e). No other App logic changes.

### CSS (`apps/web/src/design/tokens.css`) — blue+red palette unchanged

Add, in the shell region:

- `.aos-modebar` (segmented control), `.aos-mode` / `.aos-mode.active` (reuse `--signal`
  active treatment consistent with `.aos-nav-item.active`).
- `.aos-nav-soon` chip (muted, `--ink-3`, `1px` frame) + disabled nav item styling.
- `.aos-empty` centered placeholder panel.
- **Four responsive tiers** (replace the single `@media (max-width:720px)` block):
  - **≥2200px (Command Wall)**: rail `flex-basis: 300px`; `.aos-workspace` padding `32px 40px`
    and raise/relax the content max-width so views use the ultrawide (center content, don't
    stretch line lengths past readable — e.g. workspace `max-width: none`, inner views keep
    their own caps but are centered with generous gutters). Larger modebar.
  - **1180–2199px (Desktop)**: current layout (rail 250px).
  - **720–1179px (Tablet)**: rail becomes a **horizontal top bar** (brand left, modebar +
    surface chips in a horizontally-scrollable row); workspace full width; project foot moves
    inline/right.
  - **<720px (Phone)**: modes render as a **fixed bottom tab bar**; the surface list is a
    horizontally-scrollable strip under the topbar; workspace full-bleed with bottom padding
    to clear the tab bar. Voice/console-friendly single column.
  - Respect `prefers-reduced-motion` (no new motion beyond existing).

## Acceptance criteria

1. Six modes render in the rail; clicking a mode reveals that mode's surface list.
2. All **8 existing views** remain reachable via their mode; **`data-testid="nav-<view>"`
   preserved**; the app still defaults to Overview.
3. Planned surfaces show as disabled **"soon"** items (`data-testid="soon-<id>"`), not clickable.
4. Switching to a mode with a live surface routes the workspace to that mode's first live view;
   switching to Builder (no live) shows the coming-soon empty state.
5. Breadcrumb shows Mode + View; `aria-current`/`aria-pressed` set correctly; mode switcher is
   keyboard operable.
6. Layout adapts at all four tiers — verified: at <720px the modes render as a bottom tab bar
   (distinct from the desktop left rail); at ≥2200px the rail widens and the workspace uses the
   extra width. `.aos-shell` never causes horizontal body scroll at any tier.
7. `npm run build` clean; **all Playwright e2e green** (existing specs unmodified in intent +
   a new `apps/web/e2e/shell-modes.spec.ts`).
8. PR Guardian PASS (web tests are added, so `web-tests-not-enforced` should not fire). Record
   a lesson only if a gate finding occurs.

## Tests (`apps/web/e2e/shell-modes.spec.ts` + keep existing green)

- Default load lands on Overview and Executive mode is active.
- Clicking `mode-architect` shows Repositories/Architecture/Reuse and routes to Repositories;
  `nav-repositories` is present and active.
- A `soon` surface (e.g. `soon-research-inbox` under Research) is visible and `disabled`.
- Clicking `mode-builder` shows the coming-soon empty state (no live view).
- Responsive: set viewport 390×780 → the mode tab bar is visible (bottom bar); set 2560×1080 →
  desktop/wall rail present. (At least one narrow + one wide assertion; no horizontal overflow.)
- Existing `nav.ts` support + specs continue to pass unchanged.

## Verification plan (Orchestrator, independent — builder ≠ verifier)

- `npm ci && npm run build` in `apps/web` (clean).
- `npx playwright test` full suite green (headless Chromium).
- Real-app screenshots at Wall / Desktop / Tablet / Phone widths.
- `python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file <body>` → PASS.

## Risk / effort

- **Risk**: low–moderate. Presentational + nav restructure; the only behavioral change is the
  mode→view routing. Main regression surface is the e2e nav contract — mitigated by preserving
  `nav-<view>` testids. Responsive CSS is additive.
- **Effort**: ~1 focused build cycle. One PR, one package.
