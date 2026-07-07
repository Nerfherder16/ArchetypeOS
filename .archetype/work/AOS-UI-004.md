# AOS-UI-004 — Restyle Overview + Repositories onto the ops-deck (per-view restyle arc)

Status: in review
Owner: Orchestrator (Opus 4.8) — this cloud session
Branch: claude/aos-ui-004-restyle-entry (fresh from origin/main)
Depends on: AOS-UI-003 (rail shell, #82, on main)

## Summary

First increment of the per-view restyle arc AOS-UI-003 set up: move the **Overview** and
**Repositories** views off their transitional `.aos-legacy` light panels onto native dark
ops-deck `.aos-*` components. Establishes a reusable **view-restyle vocabulary** in
`tokens.css` that the remaining views (Architecture, Council & Decisions, Knowledge, Digest,
Scheduling) inherit in later increments (AOS-UI-005+).

## Scope (files)

- `apps/web/src/design/tokens.css` — add the restyle vocabulary: `.aos-view` / `.aos-view-head`,
  `.aos-card` (padded HUD), `.aos-pill` (+ `.good` / `.risk`), `.aos-kv` (stat grid),
  `.aos-table` (dark data table), `.aos-linkbtn`, `.aos-btn-sm`, `.aos-form-row`, `.aos-error`.
- `apps/web/src/main.tsx` — restyle ONLY the `overview` and `repositories` view cases in
  `renderView()`: replace their `.aos-legacy` wrappers with `.aos-view` + `.aos-hud .glass`
  cards. Overview: health → good/risk pills, active-project card. Repositories: `.aos-table`
  data table (repo name = `.aos-linkbtn`, scan = `.aos-btn`), register form (`.aos-input`),
  scan summary as `.aos-kv` + signal/risk `.aos-pill`s. No data logic changes.
- Docs: fold in the AOS-UI-003 (#82) reconciliation (per LES-029).

Do NOT touch other views (they stay legacy until their own increment), backend, or the API.

## Hard constraint — preserve every e2e selector

All existing test ids / button labels / placeholders / asserted body text stay verbatim:
`Repository name` / `Local path` placeholders, the repo-name `<button>` (role+name),
`never` for unscanned, `Run scan` / `Register repository` labels, and body text containing
`Python` / `docker` / `.env` in the scan summary. `control-tower.spec.ts` is the guard.

## Acceptance criteria

- `npm run build` clean; no `any`.
- Overview + Repositories render as native dark ops-deck views (screenshots).
- Full Playwright suite green (all selectors preserved).
- Guardian PASS / PASS_WITH_WARNINGS.

## Verification

- Orchestrator: `npm run build` + full `npx playwright test` (15/15) + screenshots of both
  restyled views. Guardian gate + ci-green-signalled Merge Gate.

## Follow-ups
- AOS-UI-005+: restyle the remaining views (Architecture, Council & Decisions, Knowledge,
  Digest, Scheduling) onto the same vocabulary; drop each `.aos-legacy` wrapper.
