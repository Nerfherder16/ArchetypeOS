## Layer 10: Interface and Interaction

Owns how users interact with ArchetypeOS.

Capabilities:

- Dashboard
- Command palette
- Voice interface
- agent council dashboard (AOS-COUNCIL-002: a Control Tower "Agent Council" section surfacing the full council reasoning the API already returns — verdict + confidence, a Final Judge panel with agreements/disagreements/unsupported claims/follow-up, and per-agent cards (summary/findings/evidence/concerns/status); the "Insufficient evidence" abstention is rendered distinctly. Read-focused; enqueue stays in the Decision Loop)
- Reuse view (AOS-UI-001: the first surface on the scoped `.aos-*` ops-deck design system — a live Control Tower view wired to the Transfer Engine `POST /projects/{id}/transfer`, rendering ranked evidence-backed reuse cards with a signal-strength confidence meter, matched-term chips, and expandable reason/evidence/required-changes/risks/provenance; see Layer 5)
- Reuse radar instrument (AOS-UI-002: the Control Tower's first WebGL surface — a react-three-fiber radar (`apps/web/src/features/reuse/Radar.tsx`, over pure deterministic `radarLayout.ts`, distance-from-center = `1 − confidence`) plotting the live reuse candidates; the radar and the Reuse cards are one interaction surface (click a blip → expand its card; hover a card → highlight its blip), with WebGL-probe/error-boundary → static-placeholder and reduced-motion fallbacks; see Layer 5)
- Nightly Audits board (AOS-SELFHEAL-OBS-UI: a Control Tower **Operations** surface (`apps/web/src/features/audits/AuditsView.tsx`, view id `audits`) reading `GET /audits/heartbeats` — one row per known self-learn routine (conflict / toil / coherence / session-pain) resolved to a single state: `clean`, `findings` (links its review PR), `failed`, `missed` (a heartbeat older than a day → a skipped nightly is visible, not silent), or `no report` (never checked in). An attention summary counts missed/failed routines; any routine the API returns outside the known set is appended so nothing is hidden. Read-only board over the AOS-SELFHEAL heartbeat observability — see Layer 8. **Per-project grouping:** below the global board a "Per-project audits" section lists projects with an enable/disable toggle (`PATCH /projects/{id}` via `updateProject`) and, for each opted-in project, its heartbeats filtered by `project_id` — the operator-facing surface of the per-project audit toggle.)
- engineering observatory
- multi-monitor layouts

Primary artifacts:

- docs/DASHBOARD_INTERFACE.md
- docs/VOICE_PROVIDER_ADAPTERS.md
- docs/VOICE_SAFETY_MODEL.md
- docs/AGENT_COUNCIL_DASHBOARD.md
- apps/web/src/main.tsx ("Agent Council" Control Tower section — AOS-COUNCIL-002) with apps/web/e2e/council-dashboard.spec.ts
- apps/web/src/features/audits/AuditsView.tsx (AOS-SELFHEAL-OBS-UI: Nightly Audits board) with apps/web/e2e/audits-view.spec.ts
- docs/ENGINEERING_OBSERVATORY.md

