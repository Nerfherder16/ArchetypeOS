# LES-L22 — contract-coherence PRs are type-only; override DOCS and WEB_TESTS with rationale citing this lesson

## Aliases

- coherence probe PR Guardian BLOCK on docs/web-tests
- type widening PR blocked on missing-docs
- AOS-SELFHEAL-005 override rationale
- nightly coherence PR guardian override

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session, AOS-SELFHEAL-005 run 2026-07-22)

## Evidence

- AOS-COHERENCE-2026-07-22 PR: `apps/web/src/api.ts` type widening (3 types, 10 fields) triggered
  `missing-docs` (no docs/ touched) and `web-tests-not-enforced` (no e2e specs changed).
- `missing-docs` is a false positive for type-contract files: the natural documentation artifact
  is the coherence digest (`.archetype/coherence/<date>.md`), which is gitignored by project
  convention; no docs/ update is appropriate for a pure type-seam fix.
- `web-tests-not-enforced` is not actionable at type-widening time: E2E specs test rendered UI
  behavior; newly-exposed fields have no view-layer consumer yet — that is a follow-up PR which
  will carry the Playwright specs.

## Linked Decisions / Projects

- `apps/web/src/api.ts` — Connector, Job, Repository types
- `tools/coherence_probe.py` — AOS-SELFHEAL-005 probe
- `tools/pr_guardian.py` — `missing-docs`, `web-tests-not-enforced` checks
- `scripts/nightly/coherence_learn.prompt.md` — coherence learn procedure

## Content

- Event: nightly coherence PR opened to widen three frontend types was BLOCKed by Guardian
  on `missing-docs` and warned on `web-tests-not-enforced`, both false positives for
  type-contract changes.
- Rules:
  1. **Type-widening PRs that close a frontend/backend contract seam need neither a docs/ update
     nor a Playwright spec at merge time.** The docs artifact (coherence digest) is gitignored;
     the test artifact belongs in the follow-up view PR. Use `PR_GUARDIAN_OVERRIDE_DOCS` and
     `PR_GUARDIAN_OVERRIDE_WEB_TESTS` with rationale + this lesson ID on every
     `AOS-COHERENCE-*` PR.
  2. **Always add an `## Acceptance Evidence` section with at least one `evidence:` bullet** —
     a markdown table does not satisfy the Guardian's line-start bullet + `evidence:` keyword check.
     Use the form `- Criterion: … evidence: git diff / command / CI job`.
  3. **The pre-existing `TS5107 moduleResolution=node10` deprecation** in `apps/web/tsconfig.json`
     causes `npm run build` to fail even before any changes; it is unrelated to type widening.
     Coherence PRs should open as draft and note the pre-existing failure.  Fix is to upgrade
     `moduleResolution` to `bundler` (separate PR).
