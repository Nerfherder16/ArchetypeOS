## Layer 5: Design and User Experience

Owns product visual language and workflow usability.

Capabilities:

- Design Intelligence
- Ops-deck design system (AOS-UI-001: a scoped `.aos-*` design-system layer — `apps/web/src/design/tokens.css` — with blue+red tokens, self-hosted Bebas Neue display type, and angular HUD-frame / neumorphic-chip / signal-meter primitives across both themes, scoped under `.aos-surface` so it is inert against the existing Control Tower page. Its first surface is the live **Reuse view** (`apps/web/src/features/reuse/ReuseView.tsx`) wired to `POST /projects/{id}/transfer` — ranked, evidence-backed reuse cards with a signal-strength confidence meter, matched-term chips, and expandable reason/evidence/required-changes/risks/provenance. **The WebGL radar instrument shipped (AOS-UI-002): the Control Tower's first WebGL surface on the `.aos-*` design system** — a react-three-fiber radar (`apps/web/src/features/reuse/Radar.tsx`) over a pure deterministic candidate→polar mapping (`radarLayout.ts`, distance-from-center = `1 − confidence`) that plots the same live reuse candidates: rings, rotating sweep, pulsing core, tier-colored blips (cyan = has matched_terms, periwinkle = lexical-lean), with a WebGL capability probe + error boundary → static-placeholder fallback and a prefers-reduced-motion freeze. `ReuseView` lifts card-expand state up so the radar drives it (click a blip → expand + scroll its card; hover a card → highlight its blip). Deferred superset: a generic reusable `<Radar>` + the full rail-shell migration onto the `.aos-*` system (AOS-UI-003))
- Dashboard Interface
- Workspace Layout Engine
- Visual Engineering Intelligence
- Voice Command Center

Primary artifacts:

- docs/DESIGN_INTELLIGENCE.md
- docs/DASHBOARD_INTERFACE.md
- apps/web/src/design/tokens.css (AOS-UI-001: the scoped `.aos-*` ops-deck design system — tokens, Bebas Neue, HUD/neumorphic/signal-meter primitives, both themes)
- apps/web/src/features/reuse/ReuseView.tsx (AOS-UI-001: the live Reuse view — the design system's first surface, wired to the Transfer Engine) with apps/web/e2e/reuse.spec.ts
- apps/web/src/features/reuse/radarLayout.ts + Radar.tsx (AOS-UI-002: the WebGL radar instrument — pure deterministic candidate→polar mapping + the react-three-fiber `<Canvas>`, the Control Tower's first WebGL surface) with apps/web/e2e/radarLayout.spec.ts + reuse-radar.spec.ts
- docs/WORKSPACE_LAYOUT_ENGINE.md
- docs/VISUAL_ENGINEERING_INTELLIGENCE.md
- docs/VOICE_COMMAND_CENTER.md

