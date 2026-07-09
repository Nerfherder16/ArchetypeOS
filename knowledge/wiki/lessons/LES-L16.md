# LES-L16 — PR Guardian override tokens require an explicit LES-<n> lesson citation (RFC-0004)

## Aliases

- override-without-lesson-citation BLOCK
- PR_GUARDIAN_OVERRIDE_* must cite a lesson
- coherence probe type-widening PR blocked by missing lesson ref

## Status

validated

## Owner

Nightly coherence routine (AOS-SELFHEAL-005)

## Evidence

- AOS-COHERENCE-2026-07-09 PR run: coherence probe found real contract-lag in 7 frontend
  types; `apps/web/src/api.ts` was widened to match backend schemas. Guardian issued
  `[BLOCK] override-without-lesson-citation` when the PR body used
  `PR_GUARDIAN_OVERRIDE_DOCS`, `PR_GUARDIAN_OVERRIDE_WEB_TESTS`, and
  `PR_GUARDIAN_OVERRIDE_ACCEPTANCE` tokens without citing a lesson ID.
- Relevant rule: RFC-0004 §Override Policy — every override token must be accompanied
  by a `LES-<n>` lesson ID justifying why the normally-required artefact is
  unnecessary for this class of change.

## Content

- **Event**: A mechanical type-widening PR (pure TypeScript type declarations, zero
  runtime code, zero new endpoints) was blocked because override tokens lacked lesson
  citations, even though the overrides were well-justified.
- **Root cause**: RFC-0004 requires override tokens to reference a standing lesson so
  the reasoning is durable and reviewable; a one-off rationale string is not sufficient.
- **Rules**:
  1. Any `PR_GUARDIAN_OVERRIDE_*` token in a PR body MUST include `(LES-<n>)` citing
     the lesson that records why this class of change does not need the normally-required
     artefact.
  2. For a pure type-declaration widening (TypeScript `export type` changes only):
     - `PR_GUARDIAN_OVERRIDE_DOCS`: acceptable — type-boundary corrections are self-documented
       by the coherence digest; no prose doc update is needed (cite this lesson).
     - `PR_GUARDIAN_OVERRIDE_WEB_TESTS`: acceptable — TypeScript types emit no runtime
       code; Playwright specs cover behaviour, not type declarations (cite this lesson).
     - `PR_GUARDIAN_OVERRIDE_ACCEPTANCE`: acceptable when an `## Acceptance Evidence`
       section with a clean `tsc` build is present (cite this lesson).
  3. Write the lesson in the same change set as the override, not in a follow-up commit,
     so the lesson is in HEAD when Guardian re-runs.
