# AOS-UI-006 — Restyle Council & Decisions onto the ops-deck (final legacy view)

Status: in review
Owner: Orchestrator (Opus 4.8) — cloud session
Branch: claude/aos-ui-006-restyle-council (fresh from origin/main)
Depends on: AOS-UI-004/005 (restyle vocabulary, on main)
Coordination: `main.tsx` council/decisions region — cloud session claimed with operator OK;
laptop pauses edits to that region until merge.

## Summary

The last legacy view. Restyle the `council` case in `renderView()` + the two shared badge
components onto the native dark `.aos-*` ops-deck, reusing the AOS-UI-004/005 vocabulary.
After this, the entire Control Tower is on the ops-deck (no `.aos-legacy` left except the
shared `SelectProjectNotice`).

## Scope
- `apps/web/src/main.tsx`:
  - Restyle the `council` case (Decisions & Research + Agent Council) from its `.aos-legacy`
    wrapper to `.aos-view` + `.aos-hud .glass .aos-card` panels, `.aos-rows` lists,
    `.aos-input`/`.aos-btn`/`.aos-btn-ghost` forms, `.aos-kv` where useful. Mirror the
    knowledge/scheduling restyles. No data-logic/handler/state changes.
  - Restyle `VerdictBadge` and `DecisionStatusBadge` from their hardcoded light pastel
    palettes into ops-deck `.aos-pill` variants (both are used ONLY in this view). Map to the
    blue/red palette: draft → info (signal/cyan), needs_evidence → warn (caution), approved →
    good, rejected → risk (red), active/other → neutral. Verdicts similarly (Accept→good,
    Reject→risk, Defer/Research→info, Escalate→warn). The **abstention** verdict
    "Insufficient evidence" MUST stay visually distinct (dashed border + italic), as today.
- `apps/web/src/design/tokens.css`: add `.aos-pill` tier variants as needed
  (`.aos-pill.info` / `.warn` / `.neutral` alongside `.good` / `.risk`) using the tokens
  (`--signal` / `--caution` / `--good` / `--red` / `--ink-3`). Keep `.aos-*`-prefixed.

Leave every OTHER `renderView()` case and the shared `SelectProjectNotice` untouched.

## Hard constraint — preserve every selector VERBATIM
Testids: `decision-row`, `council-review-row`, `council-detail-panel`, `council-agent-card`.
Button labels: `Enqueue council review`, `Refresh reviews`, `Draft decision`, `Refresh council`,
`Approve`, `Reject`, `Export ADR`, `Add research note`, `Add decision`, `Show details`/`Hide details`.
Placeholders: `Council question`, `Approver name`, `Research note title`, `Summary`,
`Decision title`, `Decision text`. Option: `No linked research`.
Text asserted by specs: verdict strings (`Insufficient evidence`, `Escalate to human`, …),
decision status strings (`draft`, `needs_evidence`, `approved`, `rejected` — exact), the
`approved by <name>` text, the 409 alert text (`cannot be approved` / `evidence`), `ADR exported
to wiki/decisions/`, and the heading `Decision Loop`. Guarded by `decision-loop.spec.ts`,
`council-dashboard.spec.ts`, `decisions.spec.ts`.

## Acceptance
- `npm run build` clean; no `any`.
- Council view renders native ops-deck; badges are pills; abstention stays distinct.
- Full Playwright suite green (decision-loop ×2, council-dashboard, decisions especially).
- Guardian PASS / PASS_WITH_WARNINGS.

## Verification
- Orchestrator: build + full `npx playwright test` (15/15) + screenshot the council view
  (with a review/decision present). Guardian + ci-green Merge Gate.

## Result
Completes the per-view restyle arc — the whole Control Tower on the ops-deck.
