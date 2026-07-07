# AOS-UI-009 — Orb command deck: the Operations-mode home

## Summary

Add the **Operations-mode home view** — the live agent-orb constellation the operator signed off
on across the deck mocks — as a new routed view `command`, and make it the Operations mode's
landing surface. Ports the proven canvas engine into a React/TypeScript component with correct
lifecycle, using the `--agent-*` design tokens from AOS-UI-008. The whole app is already on the
neon field (AOS-UI-008), so the deck sits in a coherent environment.

**Reference implementation (port faithfully):**
`/tmp/claude-0/-home-user-ArchetypeOS/a1cb3ca1-9017-53fc-a371-76de94a626b2/scratchpad/deck_v3.html`
— the approved mock. Its `<script>` contains the exact engine to port: `fib` (fibonacci sphere),
`rot` (rotate), `sphere` (additive-glow dot-sphere draw), `renderScene` (offscreen render), the
reflection composite in `frame`, satellite orbit math, `fireHandoff`/`bez` (hand-off packets),
and the `beginSpeak`/`endSpeak` + amplitude envelope (voice-reactive expand/contract). Reproduce
the visual behavior; adapt the plumbing to React (below).

## Scope — what this view includes

1. **The constellation**: an Orchestrator core dot-sphere (cyan) + 6 orbiting Council agent orbs
   using the real `AGENT_CATALOG` council — Librarian, Cartographer, Fitness, Scout, Guardian,
   Security — each colored from the design tokens `--agent-librarian … --agent-security`. Floor
   **reflection**, two-axis rotation, per-agent free-floating orbits, faint tethers, ambient
   **hand-off packets**, and the **voice-reactive** expand/contract + "SPEAKING · <AGENT>" banner.
2. **The command console**: a text input + Send, an optional **mic** (Web Speech `SpeechRecognition`
   STT) and **TTS** speak-back (`speechSynthesis`), all client-side and CSP-safe with graceful
   fallback when the APIs are absent. Submitting a task **routes** it to the best-matching agent
   (keyword map), fires the hand-off, drives the speaking animation, and updates a "routing to"
   indicator.
3. **Ambient life**: periodic hand-offs so the deck breathes when idle (as in the mock).

## Non-goals (explicitly deferred to their own packages)

- The **"Awaiting You" governance queue** wired to real Decisions / Guardian / Approvals data — a
  follow-up (AOS-UI-010).
- The **live activity feed** wired to real audit events — follow-up.
- The **real Claude token-usage** module wired to an actual usage source — follow-up (operator has
  asked for real Claude Code usage; that is its own data-integration package).
- The left scheduler calendar in the home (the Scheduling view already exists — not duplicated).
- Any **API/backend/schema** change. **Frontend only. No new dependencies** (Canvas 2D + optional
  Web Speech). Do NOT add three.js/r3f — this is a 2D canvas.

## React adaptation requirements (correctness)

- New feature module `apps/web/src/features/command/`:
  - **`orb.ts`** — the pure, testable helpers extracted from the engine: `fib(n)` (returns n
    points, each unit length ±1e-6), `routeForTask(text): number` (keyword→agent index; deterministic;
    default 0), and the agent registry (id/label/color/keywords). No DOM, no React — unit-testable.
  - **`CommandDeck.tsx`** — the view. Owns a `<canvas ref>` and the console. Renders orbs via the
    ported engine.
- **Lifecycle**: start the `requestAnimationFrame` loop in a `useEffect`; **cancel it on unmount**
  (return cleanup that cancels rAF, disconnects the `ResizeObserver`, and cancels any
  `speechSynthesis`/recognition). No leaks, no setState-after-unmount.
- **DPR + resize**: size the canvas by `devicePixelRatio` (cap 2) via a `ResizeObserver`, exactly
  as the mock does (offscreen buffer for the reflection composite).
- **prefers-reduced-motion**: when set, render **one static frame** (no rAF loop, no ambient
  hand-offs, no auto-speak). Assert-able.
- **Speaking without TTS**: the expand/contract must NOT depend on TTS audio firing (the mock's
  fix — drive the amplitude envelope directly on submit; TTS `onboundary` word-pulses layer on
  top when available). So routing a task always animates, even where `speechSynthesis` is blocked.
- Colors: read the six agent hues + core cyan from the design tokens where practical
  (`getComputedStyle` on the surface) or mirror the exact `--agent-*` hex values as constants in
  `orb.ts` (document that they mirror the tokens).
- Root element carries `data-testid="command-deck"`; the routing indicator carries
  `data-testid="command-routing"`; the speaking banner `data-testid="command-speaking"`.

## Wiring the view in

- `apps/web/src/shell/Shell.tsx` — add `'command'` to the `ViewId` union.
- `apps/web/src/shell/workspaces.ts` — add a **live** surface `{ id:'command', label:'Command',
  status:'live', view:'command' }` as the **first** surface of the `operations` mode (so
  `firstLiveView('operations') === 'command'` and Operations lands on the deck). Keep Digest /
  Scheduling live after it.
- `apps/web/src/main.tsx` — `renderView()` gains `case 'command': return <CommandDeck agents={…}/>`.
  The command deck is presentational/self-contained; it needs no App data for this package.
- `apps/web/e2e/support/nav.ts` — add `'command'` to its local `ViewId` union (so `navTo` can
  reach it; `modeForView('command')` → `operations`).

## Acceptance criteria

1. Operations mode's landing surface is **Command**; the canvas renders the core + 6 agent orbs
   with reflection and motion; `data-testid="command-deck"` present.
2. Submitting a task (type + Send, or a quick-action) **routes to the expected agent**
   (`command-routing` reflects it) and shows `command-speaking`; routing is deterministic per
   `routeForTask`.
3. Voice: mic/TTS used when available; **graceful, non-throwing fallback** when absent (no
   uncaught errors; a readable "voice unavailable" affordance is fine).
4. `prefers-reduced-motion` renders a static deck (no rAF loop) and does not auto-animate.
5. No console errors; rAF/observer/speech cleaned up on unmount (view switch away and back works).
6. Existing 8 views + AOS-UI-007 modes/soon/empty + AOS-UI-008 palette all still render; **full
   Playwright suite green** + a new `apps/web/e2e/command-home.spec.ts` + a unit test for
   `orb.ts` (`fib` lengths, `routeForTask` mapping) in the repo's e2e/unit pattern
   (see `apps/web/e2e/radarLayout.spec.ts`).
7. `npm run build` clean; PR Guardian PASS.

## Verification plan (Orchestrator, independent — builder ≠ verifier)

- `npm run build` clean; full `npx playwright test` green.
- Real-app screenshots of the Operations/Command deck (orbs + reflection + speaking state after a
  routed task) and confirm switching to another view and back re-mounts cleanly.
- Confirm reduced-motion static render.

## Risk / effort

- **Risk**: moderate. The canvas engine is proven in the mock; the real risk is React lifecycle
  (rAF/observer/speech leaks) and reduced-motion — covered by explicit cleanup + tests. Canvas
  visuals verified by screenshot, not e2e pixels.
- **Effort**: ~1 focused build cycle (the largest UI package so far). One PR, one package.
