# LES-L11 — hash-backed routing must update React state synchronously in the setter, not rely solely on the async hashchange event (or DOM-reading tests race)

## Aliases

- URL hash routing breaks e2e that read the DOM after navigation
- setActiveView via location.hash is async
- hashchange event makes navigation one tick late
- control-tower/textContent race after navTo
- view switch not instant after clicking a nav item

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- AOS-WEB-SPINE-001 slice 1 replaced `const [activeView, setActiveView] = useState('overview')` with a hash-backed `useHashRoute()` hook. The first draft's `navigate()` only wrote `window.location.hash` and let the `hashchange` listener call `setView` — making every in-app navigation update React state **one tick late** (the browser dispatches `hashchange` asynchronously).
- The full Playwright suite went from all-green to 5 failing. Four were pre-existing local-harness flakes (real worker/scheduler specs that also fail on clean main — confirmed by `git stash -u` + re-run). The real regression was **one** spec: `control-tower.spec.ts` did `await navTo(page, 'architecture')` then immediately `await page.textContent('body')` (a non-retrying read). Nav-then-retrying-assertion specs (`toBeVisible`) tolerated the delay; the non-retrying read raced and got the previous view -> `nodeMatch` null.

## Linked Decisions / Projects

- `apps/web/src/shell/useHashRoute.ts` — the hook (setter updates state synchronously, then syncs the hash)
- `apps/web/e2e/hash-routing.spec.ts` — deep-link / fallback / nav-writes-hash / back-button
- AOS-WEB-SPINE-001 — the main.tsx decomposition enabler (Phase 4)
- [[LES-L06]] — sibling "replace local state with the full source of truth" write-path gotcha

## Content

- Event: making the URL the source of truth for a view is correct, but routing the in-app setter *through* the async `hashchange` event turns an instant state update into a deferred one, which surfaces as flaky/failing tests and a subtly laggy UI.
- Root cause: `window.location.hash = x` fires `hashchange` on a later task; a component that expects `setState` semantics (synchronous, batched, instant re-render) instead updates a tick later.
- Fix: the setter does BOTH — `setView(next)` synchronously (instant, matches the old bare `useState` behavior) AND `location.hash = '#/' + next` to sync the URL. Keep the `hashchange` listener ONLY for EXTERNAL changes (back/forward, manual address-bar edits, links). The listener re-running `setView(next)` after an in-app nav is an idempotent no-op.
- General rule: when you back a piece of React state with an external store (URL, localStorage, a broadcast channel), the local setter must update React state directly; treat the store's change event as a secondary sync path for out-of-band changes, never the primary in-app path. If a refactor flips a test from green to red, first separate real regressions from environment flakes (stash the change and re-run on clean main) before hunting — here 4 of 5 "failures" were pre-existing.
