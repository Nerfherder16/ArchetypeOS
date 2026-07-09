# LES-L12 — Playwright getByText(string) is case-insensitive substring; a "Loading X…" placeholder sharing a heading's words causes timing-dependent strict-mode violations (green locally, red in CI)

## Aliases

- getByText matched 2 elements strict mode violation only in CI
- Scan summary matched Loading scan summary
- test passes locally fails in CI Playwright
- heading locator also matches loading placeholder
- flaky e2e assertion depends on load timing

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- AOS-WEB-SPINE-001 slice 3a added a characterization case to `project-context.spec.ts`: select a repo, then `await expect(page.getByText('Scan summary')).toBeVisible()`. The Repositories view renders a `Scan summary` eyebrow AND, while `dnaLoading` is true, a `Loading scan summary…` placeholder.
- `page.getByText('Scan summary')` matches by **case-insensitive substring** by default, so it matched BOTH nodes ("Scan summary" and "Loading scan **summary**…" — the lowercase substring still matches case-insensitively).
- Locally it passed: by the time the assertion ran, the mocked DNA fetch had resolved and `dnaLoading` was false, so the placeholder was gone → exactly 1 match. In CI's docker stack the DNA response was caught mid-load → placeholder still mounted → 2 matches → strict-mode violation → the whole `Web e2e (Playwright)` job failed and blocked the merge (mergeStateStatus UNSTABLE).

## Linked Decisions / Projects

- `apps/web/e2e/project-context.spec.ts` — fixed with `getByText('Scan summary', { exact: true })`
- `apps/web/src/main.tsx` — the `Scan summary` eyebrow (~L1119) and the `Loading scan summary…` placeholder (~L1121) that shares its words
- AOS-WEB-SPINE-001 slice 3a — RepositoryDataProvider extraction (the change under test; the product was correct, the test locator was not)
- [[LES-L11]] — sibling "separate real regressions from env flakes; a green-local/red-CI result is often the test, not the product"

## Content

- Event: a self-authored e2e assertion passed locally and on the branch's full local run, but failed the CI Playwright job on a strict-mode violation, blocking the merge. The product change (slice 3a) was correct; the test locator was ambiguous.
- Root cause: Playwright `getByText(string)` (and `getByRole({ name })`) default to **case-insensitive, whitespace-normalized substring** matching. A heading like "Scan summary" is a substring of the sibling loading placeholder "Loading scan summary…", so both match. Whether both are in the DOM at assertion time depends on async load timing — fast local mocks resolve before the assertion (1 match), a slower CI backend is caught mid-load (2 matches). That timing dependence is exactly why it was green locally and red in CI.
- Fix: `getByText('Scan summary', { exact: true })` so the heading does not match the loading placeholder. Alternatively assert on a unique `data-testid` (the retrying `getByTestId('dna-frameworks').toHaveText(...)` already waits for the loaded state and is unambiguous).
- General rule: when asserting a heading/label that has a sibling "Loading …" / "…ing" placeholder state, never use a bare `getByText` substring. Use `{ exact: true }`, a `data-testid`, or a role+exact-name. A test that is green locally but red in CI on a strict-mode "resolved to N elements" error is almost always a locator that races an async placeholder, not a product regression — fix the locator, don't touch the product. Local pass is not sufficient evidence for a new e2e assertion; the CI docker stack's real backend timing is the real gate.
