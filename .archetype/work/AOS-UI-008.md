# AOS-UI-008 — Neon command-deck palette migration

## Summary

Migrate the `.aos-*` ops-deck **dark theme** from the current blue+navy ground to the approved
**black → neon-red** command-deck palette (from the deck mocks the operator signed off on),
while keeping **cyan (`--signal`) as the cool accent** and the blue/purple family for
secondary/agent hues. This is a **values-level token migration** — token *names*, primitive
classes, DOM structure, and every view's markup are unchanged; only custom-property *values*
(and the shell background) change, so the whole app adopts the neon look coherently in one step.

This is the substrate for AOS-UI-009 (the orb Operations-home), built first so nothing is
built twice against a soon-to-change palette.

## Non-goals (deferred)

- The canvas orb / voice command-deck Operations-home (AOS-UI-009).
- Any layout/structure/markup change, new view, or new primitive.
- Any API/backend/schema change. **Frontend CSS only. No new dependencies.**

## Design — target DARK palette

Apply these values to **both** dark declarations in `apps/web/src/design/tokens.css`: the default
`.aos-surface` block (line ~25) **and** `:root[data-theme='dark'] .aos-surface` (line ~133). Keep
them identical to each other.

```
--ground: #0a0406;          /* near-black, faint warm */
--ground-2: #050304;        /* blackest ground */
--panel: #120a0d;           /* warm near-black panel */
--panel-2: #1a0f13;
--glass: rgba(18, 10, 13, 0.5);
--frame: #3a2029;           /* warm-dark hairline */
--frame-bright: #5e3340;
--ink: #f0e6ea;             /* warm off-white */
--ink-2: #b39aa4;
--ink-3: #7a6470;

--red: #ff2f4d;             /* neon red (danger/critical accent) */
--red-deep: #c8112e;
--red-wash: #2a0810;

--signal: #2fd3e8;          /* KEEP cyan — the cool anchor accent */
--signal-bright: #63ecfb;
--signal-deep: #0fa6bc;
--signal-wash: #07222b;

--lex: #5b8df0;             /* keep blue for secondary accents */
--lex-wash: #141026;        /* warmer wash on the dark ground */

--glow: 0 0 20px rgba(47, 211, 232, 0.45);        /* cyan glow retained */
--glow-soft: 0 0 12px rgba(47, 211, 232, 0.28);
--glow-red: 0 0 22px rgba(255, 47, 77, 0.42);     /* NEW token for red emphasis */
--elev: 0 18px 40px rgba(0, 0, 0, 0.72);
--elev-lo: 0 6px 16px rgba(0, 0, 0, 0.55);
--neu-up: -2px -2px 4px rgba(200, 120, 145, 0.10), 2px 2px 6px rgba(0, 0, 0, 0.72);
--neu-down: inset 2px 2px 5px rgba(0, 0, 0, 0.72), inset -2px -2px 4px rgba(200, 120, 145, 0.08);
```

Add these **per-agent hue tokens** to both dark blocks (forward-looking; reused by the orb in
AOS-UI-009; harmless if unreferenced now):

```
--agent-librarian: #35d0f0;
--agent-cartographer: #4f7cf7;
--agent-fitness: #7b5cf5;
--agent-scout: #b45cf0;
--agent-guardian: #ff3d68;
--agent-security: #ff2f3f;
```

### Shell background glow (the neon field)

Give the dark deck the black→neon-red field from the mock. On `.aos-shell` (dark only — do NOT
apply under a light theme), add a fixed, non-interactive background:

```
background-color: #050304;
background-image:
  radial-gradient(1500px 900px at 50% 116%, rgba(255, 28, 66, 0.20), transparent 60%),
  radial-gradient(1100px 700px at 100% -6%, rgba(255, 44, 84, 0.10), transparent 54%),
  radial-gradient(880px 780px at 0% 106%, rgba(180, 92, 240, 0.08), transparent 58%);
```

Keep it subtle enough that panels/text stay legible. Scope this so light theme keeps its flat
light ground (guard with `:root:not([data-theme='light'])` / the dark selector, or place it only
in the dark blocks — your call, but light must NOT get the red glow).

### Light theme

Keep the light theme (both the `@media (prefers-color-scheme: light)` block and
`:root[data-theme='light']`) **functional and legible**. Minimal changes only: align `--red` to
the new red family (e.g. `#d3313d` is fine to keep) and, if needed, nudge neutrals a touch warm
for consistency. The deck's intent is dark; do not invest in a full light re-theme, but do not
break it — the theme toggle must still produce a legible light surface.

### `.aos-legacy`

Unchanged — it is a deliberate light quarantine container for the one remaining un-restyled
notice. Leave as-is.

## Acceptance criteria

1. Dark theme renders the black→neon-red field; **all 8 views** (Overview, Repositories,
   Architecture, Knowledge, Reuse, Digest, Scheduling, Council & Decisions) + the AOS-UI-007 mode
   switcher / "soon" items / Builder empty state are **legible** (text contrast holds; pills,
   chips, HUD frames, buttons, signal meters read correctly) on the new ground.
2. Cyan `--signal` remains the primary accent; `--red` is neon; no blue-navy ground remains in
   dark.
3. Light theme still toggles to a legible light surface (no red glow, no black ground).
4. No structural/markup change; **all Playwright e2e still green** (unchanged specs).
5. `npm run build` clean. PR Guardian PASS.

## Tests / verification (Orchestrator, independent — builder ≠ verifier)

- `npm run build` clean; full `npx playwright test` green (no test changes expected — this is a
  values migration; if a test asserted a specific color it must be updated, but none should).
- Real-app screenshots (dark) of every view + the mode switcher, Builder empty state, and a
  representative pill/chip/HUD, plus one light-theme screenshot to confirm legibility.

## Risk / effort

- **Risk**: low structural, moderate visual. The only risk is contrast/legibility regressions on
  specific components against the darker warm ground — caught by the per-view screenshot pass.
  No behavior change; e2e is a safety net for structure.
- **Effort**: ~1 focused build cycle. One PR, one package.
