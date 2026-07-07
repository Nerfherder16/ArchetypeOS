# AOS-UI-002 — WebGL radar instrument for the Reuse view (react-three-fiber)

Status: in progress
Owner: Orchestrator (Opus 4.8) → Opus builder subagent
Branch: claude/aos-ui-002-radar (cut fresh from origin/main)
Depends on: AOS-UI-001 (#76 — design system + Reuse view, on main)

## Summary

Add the signature scanner **radar** to the Reuse view as a real WebGL instrument built
on **react-three-fiber / three.js** (a maintained stack — the earlier hand-rolled GLSL
shader was fragile and wouldn't render reliably). The radar plots the **live reuse
candidates** returned by the Transfer Engine: each candidate is a blip whose
**distance from center = reuse strength** (`1 − confidence`), so the operator reads
portfolio reuse at a glance. It is wired to the existing card list both ways:
**click a blip → expand + scroll to its card**, and **hover a card → highlight its blip**.

Strict superset of AOS-UI-001: consumes the same `fetchReuseRecommendations` data and
adds an instrument surface above the ranked cards. First WebGL surface in the Control Tower.

Operator decisions (locked): r3f/three; **Reuse view only** (not yet a generic reusable
`<Radar>`); **both** interactions (blip↔card).

## Scope (file boundaries)

Create:
- `apps/web/src/features/reuse/radarLayout.ts` — PURE, deterministic mapping (no React,
  no three): `candidateToPolar({ confidence, index, total }) → { radius, angle }` and
  `polarToXZ(radius, angle) → { x, z }`. Distance grows as `1 − confidence` (clamped to a
  sane ring range, e.g. 0.35..1.0 of max radius); angle is a stable even spread by index
  (deterministic — same inputs always yield the same layout, so tests + screenshots are
  stable). Exported constants for max radius / ring count.
- `apps/web/src/features/reuse/Radar.tsx` — the r3f instrument. `export function Radar({
  candidates, activeIndex, hoveredIndex, onSelect, onHover })`. Renders an `<Canvas>` with:
  concentric ring line-geometry, a subtle rotating sweep, a pulsing core, and one blip mesh
  per candidate positioned via `radarLayout`. Blip color by tier from the design tokens
  (cyan = has matched_terms / semantic-strong; periwinkle = lexical-lean; red reserved for
  a future conflict flag — default cyan/periwinkle by matched_terms length). The
  `activeIndex` blip is enlarged/brightened; the `hoveredIndex` blip pulses. Clicking a blip
  calls `onSelect(index)`; pointer over a blip calls `onHover(index)` / `onHover(null)` on
  out. Camera tilted for depth. Respect `prefers-reduced-motion` (freeze sweep/pulse).
  Labels: use `@react-three/drei` `<Html>` for the top candidate's short label, or omit
  labels and rely on the cards — keep it readable, not cluttered.
- `apps/web/src/features/reuse/radarLayout.test.ts` — unit tests for the pure mapping
  (monotonic distance vs confidence; deterministic angle spread; clamping; total=0/1 edge).

Modify:
- `apps/web/src/features/reuse/ReuseView.tsx` — lift the card expand state up so the radar
  can drive it. Track `activeIndex: number | null` (the expanded card) and
  `hoveredIndex: number | null` in `ReuseView`. Refactor `ReuseCard` to be **controlled**
  (`open`, `onToggle`, `highlighted`, `onHover` props) instead of its local `useState`.
  Render `<Radar candidates={results} activeIndex hoveredIndex onSelect onHover />` above
  the "Ranked candidates" list when `results.length > 0`. `onSelect(i)` sets `activeIndex=i`
  and scrolls that card into view (`ref.scrollIntoView({ behavior: reduced ? 'auto' :
  'smooth', block: 'nearest' })`). Hovering a card sets `hoveredIndex`. Keep all existing
  states/behavior and test ids; add `data-testid="reuse-radar"` on the radar container.
- `apps/web/package.json` (+ `package-lock.json`) — add deps: `three`, `@react-three/fiber`,
  and `@react-three/drei` (pinned versions compatible with React 19 / Vite 7). Run
  `npm install` so the lockfile updates; the "Web typecheck and build" CI job runs `npm ci`.
- `apps/web/src/design/tokens.css` — only if a small addition is needed (e.g. a radar
  container sizing class). Prefer not to touch it.

Do NOT: change backend/Python, the API client, or other views; do NOT build a generic
reusable `<Radar>` beyond the Reuse view (AOS-UI-003 territory); do NOT regress AOS-UI-001.

## Graceful degradation (required)

- **No WebGL** (or context creation throws): the radar renders nothing (or a slim static
  placeholder) and the **cards remain fully functional** — the radar is an enhancement, not
  a dependency. Wrap the Canvas so a WebGL failure never breaks the view (error boundary or
  a capability check before mount).
- **`prefers-reduced-motion`**: no sweep/pulse animation; static instrument.
- Bundle-size note: three + r3f add ~150 KB gzipped to `apps/web`. Acknowledge in the PR.

## Acceptance criteria

- `npm run build` (tsc + vite) passes; lockfile committed; no `any` in new code.
- Radar renders above the ranked cards, plotting one blip per live candidate with
  distance = `1 − confidence`; layout is deterministic.
- Click a blip → its card expands and scrolls into view; hover a card → its blip highlights.
- With WebGL absent, the cards still render and function (radar degrades silently).
- `radarLayout` unit tests pass; existing web e2e suite still green; new/updated e2e asserts
  the radar container is present when results render and the card contract still holds.
- PR Guardian PASS / PASS_WITH_WARNINGS.

## e2e / tests

- `radarLayout.test.ts` (unit) — the pure mapping. Runner: whatever the repo uses for TS
  unit tests; if none exists for web, keep the mapping trivially importable and assert via a
  tiny node/vitest harness ONLY if already available — otherwise fold the assertions into a
  Playwright spec that imports the module. Do not add a new test runner/toolchain.
- Update `apps/web/e2e/reuse.spec.ts` (or add `reuse-radar.spec.ts`): with results present
  (route-mock the transfer endpoint to return ≥2 candidates), assert `reuse-radar` is
  visible and that clicking is wired (card expands) — WebGL is available in the Playwright
  chromium build. Keep the existing terminal-state assertions intact.

## Verification (Orchestrator, independent — builder ≠ verifier)

- Run `npm run build`, the unit tests, and the full Playwright suite against a booted API.
- Route-mock candidates and **screenshot** the rendered radar + cards (real app) to confirm
  blips map by confidence and the blip↔card interactions work.
- Confirm graceful degradation path (no crash without WebGL).
- Guardian gate + Manual Merge Gate with CI evidence. Fresh branch — normal push, no force.

## Out of scope / follow-ups
- AOS-UI-003: generic reusable `<Radar>` + full rail-shell migration + landing-page reuse.
