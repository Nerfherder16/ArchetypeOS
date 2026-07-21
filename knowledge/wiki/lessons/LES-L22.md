# LES-L22 — frontend TypeScript types silently drop backend Pydantic fields; widen the type seam, don't redesign views

## Aliases

- contract-lag: frontend type thinner than backend schema
- TS type missing fields that the API already returns
- API silently drops fields the frontend type never surfaced
- coherence probe signal=true
- ConnectorRead / JobRead / RepositoryRead missing fields

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Nightly coherence probe (2026-07-13): `tools/coherence_probe.py` found 3 schemas with 10 missing fields:
  - `ConnectorRead → Connector`: `credential_present`, `reachable` (AOS-CONNECTOR-RUNTIME-001)
  - `JobRead → Job`: `sensitivity`, `requires_write`, `required_capability`, `assigned_node_id`, `routing_status`, `routing_explanation`, `routed_at` (AOS-NODE-EXECUTION-001)
  - `RepositoryRead → Repository`: `sensitivity` (AOS-AUTHORITY-HARDEN-001)
- All 10 fields were already being returned by the FastAPI backend; the frontend `export type` declarations simply never listed them, so TypeScript silently discarded them when deserializing API responses.
- The gap was the same class of manual finding the system evaluation found by hand ("the API silently dropped fields the frontend type never surfaced").
- Digest: `.archetype/coherence/2026-07-13.md`.

## Linked Decisions / Projects

- `apps/web/src/api.ts` — `Connector`, `Job`, `Repository` types
- `apps/api/app/schemas.py` — `ConnectorRead`, `JobRead`, `RepositoryRead`
- `tools/coherence_probe.py` — the deterministic probe that caught the gap
- `scripts/nightly/coherence_learn.prompt.md` — self-heal routine instructions
- [[LES-L08]] — override tokens must cite a lesson ID

## Content

- Event: The nightly coherence probe found that 10 backend Pydantic fields were present in `*Read` schemas but absent from their corresponding frontend TypeScript `export type` declarations. FastAPI serializes and sends these fields in every response; the TS type boundary silently drops them.
- Rules:
  1. **Widen the type, don't redesign the view.** A type-seam closure (adding missing fields to `export type`) is the minimum viable fix — it makes the data available to the UI without prescribing how a view should use it. Follow-up UI work is separate.
  2. **Domain fields are always real contract-lag.** Only exclude a field when it is a pure FK the UI gets from context, or a field with genuinely no view (and document the exclusion). Never omit a field to silence the probe (Article XII).
  3. **TS type must mirror the Pydantic annotation faithfully.** `str → string`, `str | None → string | null`, `bool → boolean`, `bool | None → boolean | null`, `datetime | None → string | null` (FastAPI serializes datetime as ISO string).
  4. **Override tokens require a lesson citation.** `PR_GUARDIAN_OVERRIDE_*` tokens must include a `LES-<n>` citation in the same line to pass Guardian (RFC-0004, `override-without-lesson-citation`).
  5. **Acceptance Evidence lines require an `evidence:` pointer.** Guardian checks for `evidence:` in each criterion bullet; a table row without it fails `empty-acceptance-evidence`.
  6. **Pre-existing build failures are not introduced by the type widening.** Confirm by `git stash` baseline — if the build fails identically on main, the PR is not the cause; open as a draft and document the pre-existing error.
