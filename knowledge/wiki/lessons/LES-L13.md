# LES-L13 — an inline `style={{display:…}}` cannot be hidden by a CSS media query; a new topbar element widened the phone viewport and only the responsive-overflow spec caught it

## Aliases

- adding a topbar element broke the phone no-horizontal-overflow test
- inline display style overrides CSS media query display:none
- status strip caused scrollWidth > clientWidth on narrow viewport
- responsive layout regression only one spec catches it
- move layout to CSS class so the media query can hide it

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- AOS-UX-IA-001 (d3) added `OperatorStatusStrip` (two pills) to the topbar actions. Every functional spec passed, but the full suite showed **5** local failures instead of the canonical **4** — the extra one was `shell-modes.spec.ts:74` ("layout adapts — phone bottom tab bar vs wide rail, no h-overflow"), which sets a phone viewport and asserts `document.documentElement.scrollWidth > clientWidth === false`. The two extra pills pushed the topbar past the phone width → horizontal overflow → the assertion flipped to true.
- First fix attempt (a `@media (max-width: 719px) { .aos-status-strip { display: none } }` rule) did **not** work on its own because the component set `style={{ display: 'inline-flex', … }}` inline — an inline style beats a stylesheet rule regardless of media query, so the strip stayed visible on phones.
- Real fix: move the strip's layout (`display: inline-flex; align-items; gap`) out of the inline `style` into a `.aos-status-strip` CSS rule, so the phone media query's `display: none` can override the base rule. After that, `shell-modes` is back to 7/7 (incl. the overflow case) and the strip still renders on wide screens (2/2).

## Linked Decisions / Projects

- `apps/web/src/features/statusstrip/OperatorStatusStrip.tsx` — dropped inline layout styles
- `apps/web/src/design/tokens.css` — base `.aos-status-strip` layout rule + a phone `display: none` in the `max-width: 719px` block
- `apps/web/e2e/shell-modes.spec.ts:74` — the responsive-overflow guard that caught it
- [[LES-L11]] — the discipline that surfaced it: post-change failures must be a SUBSET of the canonical flake set; a 5th failure outside {council-dashboard, decision-loop x2, scheduling} is a real regression, not a flake

## Content

- Event: a purely-additive topbar element passed all its own functional tests but broke a responsive-layout invariant (no horizontal overflow at phone width). It was caught only because the canonical-flake-set discipline flags any failure outside the known set — here `shell-modes` made 5 total, so it could not be dismissed as a worker/scheduler flake.
- Root cause 1 (the bug): new fixed-width topbar content is not free — it must fit the narrowest supported viewport. Always consider the phone layout when adding to the topbar/rail.
- Root cause 2 (the failed first fix): **inline `style` always beats a stylesheet media query.** If an element must be responsively shown/hidden or restyled by breakpoint, its layout must live in a CSS class, not an inline `style` prop. Inline styles have higher specificity than any selector and ignore `@media`.
- General rules: (1) when adding anything to a width-constrained bar, hide or collapse it at narrow breakpoints and keep the responsive-overflow spec green; (2) put any property a media query needs to override in a CSS class, never inline; (3) trust the subset-of-canonical-flakes rule — the one "extra" failure is signal, chase it before shipping.
