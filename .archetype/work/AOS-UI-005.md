# AOS-UI-005 — Restyle Architecture + Knowledge + Digest + Scheduling onto the ops-deck

Status: in review
Owner: Orchestrator (Opus 4.8) — cloud session
Branch: claude/aos-ui-005-restyle-readviews (fresh from origin/main)
Depends on: AOS-UI-004 (restyle vocabulary, #84, on main)

## Summary

Second per-view restyle increment: move the four **read-surface** views — Architecture,
Knowledge, Digest, Scheduling — off their transitional `.aos-legacy` light panels onto the
native dark `.aos-*` ops-deck, reusing the AOS-UI-004 vocabulary. After this, only
**Council & Decisions** remains legacy (its own PR — it's the densest view and sits in the
laptop session's `main.tsx` territory, so it needs the coordination hold).

## Scope
- `apps/web/src/main.tsx` — restyle the `architecture`, `knowledge`, `digest`, `scheduling`
  cases in `renderView()`. Leave `council` and all other cases untouched. No data-logic change.
- `apps/web/src/design/tokens.css` — add `.aos-rows` / `.aos-subrows` / `.aos-rowmeta`
  (divider-row list that preserves `<li>` semantics for the specs' `getByRole('listitem')`).
- `apps/web/e2e/control-tower.spec.ts` — the architecture assertion reads the `Nodes:`/`Edges:`
  counts from `body` instead of a `<section>` wrapper (the restyle drops the `<section>`);
  the counts + `(repository)` checks are unchanged.

## Hard constraint
Preserve every other e2e selector verbatim (knowledge sync/filter/lesson listitems/badges;
digest run/summary counts/recommendations; scheduling placeholders/options/buttons/listitems;
architecture Nodes/Edges/(repository)). Guarded by knowledge/digest/scheduling/control-tower specs.

## Acceptance
- `npm run build` clean; full Playwright 15/15; all four views screenshotted; Guardian PASS.

## Follow-up
- Council & Decisions restyle (the last legacy view) — coordinated PR.
