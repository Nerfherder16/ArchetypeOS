# AOS-UI-003 — Control Tower rail shell + state-based view routing

Status: in progress
Owner: Orchestrator (Opus 4.8) → Opus builder subagent
Branch: claude/aos-ui-003-rail-shell (fresh from origin/main)
Depends on: AOS-UI-001 (design system), AOS-UI-002 (radar) — both on main
Coordination: whole-file restructure of `apps/web/src/main.tsx` — claimed by the cloud
session with operator OK; the laptop session pauses `main.tsx` edits until this merges.

## Summary

Turn the Control Tower from one stacked scroll-page into an **ops-deck shell**: a left rail
nav + topbar + workspace, with **state-based view routing** (an `activeView` state; no router
dependency, no URL change). The existing 11 sections become routed views. This is the
full-page adoption of the `.aos-*` design language AOS-UI-001 seeded as a scoped island.

Structure-first, restyle-incrementally: this PR moves sections into views and builds the
shell chrome in the ops-deck style; each view's *internals* keep their current markup and
are quarantined in a light `.aos-legacy` panel so they stay legible on the dark deck. The
Reuse view already renders native `.aos-*` and needs no wrapper. Follow-up PRs restyle each
legacy view and drop its wrapper.

## Nav map (rail items → current sections)

| view id | Rail label | Section(s) moved (main.tsx headings) |
|---|---|---|
| `overview` | Overview | Runtime Health (+ a brief project summary) |
| `repositories` | Repositories | Repositories + Scan Summary |
| `architecture` | Architecture | Architecture |
| `council` | Council & Decisions | Decisions & Research + Agent Council |
| `knowledge` | Knowledge | Knowledge |
| `reuse` | Reuse | `<ReuseView>` (native `.aos-*`) |
| `digest` | Digest | Nightly Digest |
| `scheduling` | Scheduling | Scheduling & Jobs |

Default `activeView`: `overview`. Drop the "v0.1 Placeholders" section (or tuck a one-line
note under Overview). The **Projects** section becomes the shell's **active-project selector**
in the rail foot (persists across views); creating/selecting a project stays available there.

## Scope (files)

Create:
- `apps/web/src/shell/Shell.tsx` — presentational shell: `.aos-surface` root, left rail
  (brand mark, nav list, rail-foot project selector slot), topbar (breadcrumb `Project / View`
  + theme toggle + a health pip), and a `workspace` that renders `children` (the active view).
  Props: `activeView`, `onNav(viewId)`, `navItems`, and slots for `projectSelector` + `health`.
  Nav items are real `<button>`s with `data-testid="nav-<id>"` and accessible names = the Rail
  label. The active item is visibly marked (`aria-current`).
- (optional) `apps/web/src/shell/views.tsx` if extracting view render helpers keeps main.tsx
  readable — but see the closure note below; keeping the view JSX inside `App()` is fine.

Modify:
- `apps/web/src/main.tsx` — the restructure. Keep `App()` holding ALL existing state and
  handlers (do not rewrite any data logic). Add `const [activeView, setActiveView] =
  useState<ViewId>('overview')`. Move each section's existing JSX out of the single giant
  `return (...)` into a per-view chunk (a `views` record or a `renderView()` switch defined
  INSIDE `App()` so every handler keeps its closure over App state). `App()` returns
  `<Shell activeView … onNav={setActiveView} projectSelector={…} health={…}>{activeView===
  'reuse' ? <ReuseView …/> : <div className="aos-legacy">{…section JSX…}</div>}</Shell>`.
  Wrap every legacy view's content in `.aos-legacy`; the Reuse view renders bare.
  The `data-testid="decision-row"` (LES-030) and all existing test ids/placeholders/button
  names MUST be preserved verbatim — the e2e suite depends on them.
- `apps/web/src/design/tokens.css` — add shell/nav classes (`.aos-rail`, `.aos-nav`,
  `.aos-nav-item`, `.aos-topbar`, `.aos-workspace`) and `.aos-legacy` (a light-surface,
  rounded, padded panel that RESETS the ground/ink to a legible light scheme so the
  un-restyled inline-styled sections read correctly on the dark deck). Keep everything
  `.aos-*`-prefixed and under `.aos-surface`.
- ALL `apps/web/e2e/*.spec.ts` that drive a section — add a rail navigation step. After
  `goto('/')`, click the view's nav (`page.getByTestId('nav-<id>').click()`) before
  interacting with that section. Add a tiny shared helper if it reduces churn. Specs to
  touch: control-tower (nav to repositories + architecture), council-dashboard + decision-loop
  + decisions (nav to `council`), digest (`digest`), knowledge (`knowledge`), scheduling
  (`scheduling`), reuse + reuse-radar (`reuse`). Project create/select stays in the rail foot —
  update those interactions if their placement changes (keep the same placeholder/button text
  where possible to minimize churn). `radarLayout.spec.ts` is pure and needs no change.

Do NOT: change backend/Python or the API client; rewrite section internals or their data
logic (relocate only); add a routing library; change any existing test id / button label /
placeholder text unless unavoidable (if unavoidable, update every referencing spec in lockstep).

## Visual approach (transitional, mature-state-aligned)

- App root becomes `.aos-surface` (dark ops-deck ground + tokens) — the design system is now
  the page, not an island.
- Rail + topbar: full ops-deck chrome (mirror the Reuse mock's rail/topbar feel).
- Legacy views sit in `.aos-legacy` light panels (quarantined, legible) until restyled.
- Reuse view renders native dark `.aos-*`.
- Light/dark: the shell honors the tokens' theme system; `.aos-legacy` stays a stable light
  panel in both (it's a transitional container).

## Acceptance criteria

- `npm run build` (tsc + vite) clean; no `any` in new code.
- The app renders as a rail shell; clicking each nav item swaps the workspace to that view;
  only the active view is mounted. Default view is Overview. Active project persists across views.
- Every existing behavior still works (create project, register/scan repo, DNA/architecture,
  council review → draft → approve → ADR, decisions/research, digest, knowledge sync, scheduling,
  reuse + radar) — verified by the updated e2e suite.
- Full Playwright suite green (all specs updated to navigate via the rail).
- No existing test id / button label / placeholder text broken (or all references updated).
- PR Guardian PASS / PASS_WITH_WARNINGS.

## e2e / verification

- Each spec: `goto('/')` → `getByTestId('nav-<id>').click()` → existing interactions.
- Orchestrator independent verification: run `npm run build` + the FULL `npx playwright test`
  against a booted API (all specs), and screenshot the shell in ≥2 views (Overview + Reuse +
  one legacy, e.g. Council) to confirm the rail, routing, active-project persistence, and that
  legacy panels are legible. Confirm the Reuse radar still works inside the shell.
- Guardian gate + Manual Merge Gate (the ci-green signal now posts on all-green). Fresh branch.

## Out of scope / follow-ups
- AOS-UI-004+: restyle each legacy view onto `.aos-*` (drop `.aos-legacy`), one PR per view.
- Hash/URL routing (shareable deep links) — deferred; state-based is enough now.
- Extracting the radar into a generic reusable component for the landing page.
