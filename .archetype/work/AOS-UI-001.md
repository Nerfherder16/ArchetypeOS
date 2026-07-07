# AOS-UI-001 — Control Tower design system + Reuse view (live API)

Status: in progress
Owner: Orchestrator (Opus 4.8) → Opus builder subagent
Branch: claude/aos-runtime-002-scanner-1egyjw
RFC: RFC-0009 (portfolio reuse) — UI surface for `recommend_reuse`

## Summary

Lock in the ArchetypeOS "ops-deck" visual language as a real, reusable design-system
layer in `apps/web`, and ship the first feature built on it: a **Reuse** view wired to
the live transfer endpoint `POST /projects/{id}/transfer`. The Reuse view lets the
operator describe a need, scan the portfolio's distilled knowledge, and see ranked,
evidence-backed reuse recommendations — the UI for the Knowledge Transfer Engine.

This is a strict permanent subset of the mature-state Control Tower target (per the
"design to the mature state, don't build twice" rule). The tokens/primitives are the
foundation every later view migrates to; nothing here is throwaway scaffolding.

## Design source of truth

The approved visual language is the mock at (read it, adapt the CSS faithfully):
`/tmp/claude-0/-home-user-ArchetypeOS/a1cb3ca1-9017-53fc-a371-76de94a626b2/scratchpad/reuse_view_mock_v7.html`

Language summary (extract into tokens, both light + dark):
- Palette: **blue + red** cyberpunk ops-deck. cyan `--signal` (primary/semantic),
  periwinkle `--lex` (lexical/secondary), red `--red` (conflict/critical/active).
  Cool navy neutrals. NO amber/yellow, NO green. Semantic ≠ accent.
- Type: **Bebas Neue** (self-hosted, vendored at `apps/web/public/fonts/bebas-neue.woff2`)
  for display headings; system sans for body; monospace for readouts/labels.
- Geometry: angular cut-corner (clip-path) HUD frames with a bright frame edge + fill,
  panel elevation (drop-shadow following the clipped shape), subtle vignette + parallax.
- Chips: **neumorphic** raised tactile tags (rounded, soft dual shadow); mode toggles
  neumorphic raised=off / pressed-in=on.
- Confidence meter: signal-strength bars (▁▂▃▄▅) + numeric value.

## Scope (file boundaries — builder MUST stay within these)

Create:
- `apps/web/src/design/tokens.css` — token system (both themes via `@media
  prefers-color-scheme` + `:root[data-theme]`), `@font-face` Bebas Neue
  (`url('/fonts/bebas-neue.woff2')`), and primitive classes: `.aos-hud` (cut-corner
  frame+fill+elevation), `.aos-chip` (neumorphic), `.aos-btn` / `.aos-btn-ghost`,
  `.aos-bars` (signal meter), `.aos-eyebrow`, `.aos-mono`. Scope everything under a
  root class or `.aos-*` prefixes so it does NOT restyle the existing stacked page.
- `apps/web/src/features/reuse/ReuseView.tsx` — the Reuse feature component.
- `apps/web/e2e/reuse.spec.ts` — Playwright e2e (real API, sqlite → lexical path).

Modify:
- `apps/web/src/api.ts` — add `TransferRecommendation` type + `fetchReuseRecommendations(projectId, need)`.
- `apps/web/src/main.tsx` — import `./design/tokens.css`; mount `<ReuseView projectId={selectedProjectId} />`
  as a new section (consistent with existing section pattern; gated on a selected project).

Do NOT: rewrite existing sections, introduce client-side routing/the full rail shell,
add npm deps, or touch backend/Python. The radar instrument and the full control-tower
shell are explicitly OUT OF SCOPE for this package (follow-ups AOS-UI-002 / AOS-UI-003).

## API contract (already live — do not change backend)

`POST /projects/{project_id}/transfer`  body `{ "need": string }`
→ `200` `TransferRecommendationRead[]`, each:
```
source_repository: string
source_project_id: string | null
reusable_asset: string
reason: string
matched_terms: string[]
evidence: Array<{type:"distillation", ref:string} | {type:"repository", id:string}>
required_changes: string | null
risks: string | null
confidence: number      // 0..1
```
`404` if project not found. Empty portfolio / no matches → `200 []`.

## Component behavior (ReuseView)

- Header: eyebrow "Knowledge Transfer Engine", Bebas title, one-line description.
- Query: text input (default empty; placeholder describing a need) + "Find reuse"
  button. Scope note: results exclude the current project's own repos.
- On submit: call `fetchReuseRecommendations(selectedProjectId, need)`. States:
  - no project selected → prompt to select/create a project (reuse existing selection).
  - empty need → button disabled or inline "describe a need first" (no request).
  - loading → button shows "Scanning…", disabled.
  - error → inline error (surface `err.message`).
  - `[]` → empty state: "No reuse found across the portfolio for that need."
  - results → ranked cards sorted by confidence (API already sorts).
- Card: signal-bars meter (fill = round(confidence*5)) + numeric `confidence.toFixed(2)`,
  `source_repository` (mono), `reusable_asset`, matched-term neumorphic chips, and an
  expand toggle revealing: Reason, Evidence (render distillation `ref` / repository `id`),
  Required changes, Risks. Provenance footer: "cites <first distillation ref>".
- Accessibility: button is a real `<button>`, input has a label, expand is keyboard-
  operable, focus-visible states from tokens. Respect `prefers-reduced-motion`.
- test ids: `reuse-view`, `reuse-need-input`, `reuse-run`, `reuse-result-row`,
  `reuse-empty`, `reuse-error`, `reuse-expand`.

## e2e (apps/web/e2e/reuse.spec.ts)

Real API on sqlite (lexical path). Deterministic, stable contract:
1. `goto('/')`, create a project (auto-selected), confirm Reuse section renders.
2. Type a need into `reuse-need-input`, click `reuse-run`.
3. Assert the flow resolves to a well-formed terminal state: EITHER at least one
   `reuse-result-row` (if the portfolio has scorable distilled repos) OR the
   `reuse-empty` state — never a hang/error. Use retrying web-first assertions
   (LES-015: no one-shot `.count()`).
4. If a result row is present, expand it and assert Reason + provenance are visible.
Follow the harness conventions in `council-dashboard.spec.ts` (uid(), toPass polling).

## Acceptance criteria

- `npm run build` (tsc + vite) passes; `tsc` clean (no `any` leaks in new code).
- Reuse view renders in the new design language, both light and dark themes coherent.
- Live query round-trips to `POST /projects/{id}/transfer`; all states handled.
- New e2e passes locally; existing e2e unaffected.
- Design tokens are scoped and do not visually regress the existing sections.
- PR Guardian: PASS or PASS_WITH_WARNINGS (acknowledge-only).

## Verification (Orchestrator, independent — builder ≠ verifier)

- Run `npm run build` and the full `npm run test:e2e` (or at least reuse + one existing
  spec) against a booted API; drive the Reuse flow in a real browser and observe a live
  round-trip (network 200 from `/transfer`), not just tests.
- Confirm tokens don't regress existing sections (visual check of the page).
- Guardian gate + Manual Merge Gate comment with CI evidence.

## Out of scope / follow-ups
- AOS-UI-002: radar instrument (react-three-fiber) fed by real candidates.
- AOS-UI-003: full control-tower shell (left rail nav, view routing, telemetry) — migrate
  existing sections onto the design system.
- Voice agent / landing page (separate track).
