# AOS-WEB-001 — Web Test Framework: Playwright Suite, Enforced (Plane AOS-16)

## Status

In Progress

## Origin

Plane AOS-16 (urgent, target 2026-07-28). Hard deadline: the guardian's accepted-warnings entry for `web-tests-not-enforced` (LES-006) expires **2026-08-01**, after which every web PR BLOCKs. This package makes web tests real and enforced, then retires the acceptance rather than renewing it. First package of Sprint 5 and the first under the Opus 4.8 orchestrator.

## Verified Baseline

Confirmed by inspection:

- `apps/web` is a Vite 7 / React 19 / TS 5.9 app (`apps/web/package.json`); scripts `dev` (vite --host), `build` (tsc && vite build). No test dependency, no test script.
- CI (`.github/workflows/ci.yml`) has 5 jobs; `web-build` uses `actions/setup-node@v4` node 22, `npm install` + `npm run build` in `apps/web`. No web test job.
- `scripts/web_drive/` holds 3 committed drive scripts (`drive.mjs` control tower, `drive_dec.mjs` decisions/research, `drive_digest.mjs` digest) using bare `playwright` with `chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })` — a path specific to THIS managed container; it does not exist on CI ubuntu runners. These are the seed corpus.
- `drive.mjs:18` comment ("redis absent -> /health 500") is STALE: post-PR #39 `/health` returns 200 `degraded` without Redis. This is a live LES-007 (doc staleness) instance and matters here: Playwright's `webServer` readiness can poll `/health` and get 200 without a Redis service.
- Guardian `check_tests_for_code_changes` (`tools/pr_guardian.py:182-193+`): api/worker emit BLOCK when app code changes without test changes; web emits an UNCONDITIONAL `web-tests-not-enforced` WARN on any `apps/web/src/` change (line ~190). `.archetype/guardian/accepted_warnings.json` annotates that warn until 2026-08-01, then escalates to BLOCK (AOS-PRG-003).
- Toolchain: node 22 present; `redis-server` at `/usr/bin/redis-server`; pre-installed Playwright chromium at `/opt/pw-browsers/` (build 1194); env has `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`.

## In-Scope Files

- `apps/web/package.json` (add `@playwright/test`, `test:e2e` script), `apps/web/playwright.config.ts` (new)
- `apps/web/e2e/` (new): `control-tower.spec.ts`, `decisions.spec.ts`, `digest.spec.ts`, `serve-api.sh` (scratch-stack boot), `fixtures/demo-repo/` (a tiny Python file so the scanner detects Python)
- `apps/web/.gitignore` (new or amend): ignore `test-results/`, `playwright-report/`, `node_modules/`
- `.github/workflows/ci.yml` (add `web-e2e` job)
- `tools/pr_guardian.py` (evolve `web-tests-not-enforced`), `.archetype/guardian/accepted_warnings.json` (retire entry), `apps/api/tests/test_guardian_evolution.py` (add cases)
- `knowledge/wiki/lessons/LES-009.md` + `index.md` (guardian change requires a lesson; the acceptance mechanism worked as designed)
- `docs/PR_GUARDIAN.md` (web-tests enforcement note), `scripts/web_drive/README.md` (point at the promoted suite), `docs/CAPABILITY_MAP.md`
- state docs + this spec (fold AOS-ORCH-004/PR #42 status flip in; backfill Board ID Registry AOS-16..23)

## Out-of-Scope

- component/unit tests (Vitest) — the seed corpus is E2E; unit tests can be a later package
- new dashboard features or `main.tsx`/`api.ts` behavior changes
- the compose-smoke job (unchanged; the e2e job runs its own lighter stack)
- migrations, worker changes (AOS-17/18)

## Design

**Framework**: `@playwright/test@1.61.1` (matches the pre-installed chromium build 1194, so the local container resolves it via `executablePath`; CI installs the matching browser). Added to `apps/web` devDependencies; `test:e2e` script = `playwright test`.

**Config `apps/web/playwright.config.ts`**:
- `testDir: './e2e'`, `workers: 1` (one shared API/db), `retries: process.env.CI ? 1 : 0`, `reporter: 'list'`.
- `use.baseURL: 'http://localhost:5173'`; `use.launchOptions` sets `executablePath: process.env.PW_LOCAL_CHROMIUM` ONLY when that env var is present (local container passes `PW_LOCAL_CHROMIUM=/opt/pw-browsers/chromium`; CI omits it and uses the installed browser). This is the portability seam — no hardcoded container path in committed code.
- `webServer: [ {command: 'bash ./e2e/serve-api.sh', url: 'http://localhost:8000/health', timeout: 60000, reuseExistingServer: !process.env.CI}, {command: 'npm run dev', url: 'http://localhost:5173', reuseExistingServer: !process.env.CI} ]`. The `/health` poll returns 200 degraded without Redis (PR #39) — no Redis service needed.

**`e2e/serve-api.sh`**: creates a fresh scratch sqlite + artifact dir under a temp path, ensures `REPOSITORY_ROOT` contains `demo-repo` (the committed `fixtures/demo-repo/`), launches `uvicorn app.main:app --port 8000` with `PYTHONPATH=../api` (repo-relative), `DATABASE_URL=sqlite`, `REDIS_URL=redis://localhost:9999/0`. Idempotent DB reset each run.

**Specs** (converted from the drives, `expect`-based, not the custom `check()` harness): `control-tower.spec.ts` (project create/select, repo register/scan, Python detected, .env risk flag, architecture counts, reload persistence), `decisions.spec.ts` (research note + linked decision via forms, typed evidence via API), `digest.spec.ts` (run digest, summary counts, draft recommendation, reload persistence). Each creates uniquely-named entities so serial reuse of one DB is safe. **Correct** the stale /health-500 assumption in comments.

**CI `web-e2e` job**: node 22; `npm install` in `apps/web`; `npx playwright install --with-deps chromium`; set up python 3.12 + `pip install -r apps/api/requirements.txt`; `npm run test:e2e` (webServer boots API + web). Sixth job; guardian-gate table in the merge-gate comment extends to 6.

**Guardian evolution** (cites LES-006/LES-009): `web-tests-not-enforced` warn becomes conditional — fires only when `apps/web/src/` changed WITHOUT `apps/web/e2e/` changes (mirrors api/worker, kept as WARN not BLOCK for one sprint of settling). Retire the `.archetype/guardian/accepted_warnings.json` entry to `[]` (tests now exist; acceptance no longer needed). Add guardian tests for the new conditional. Record **LES-009**: the dated-acceptance forcing function worked — a deadline drove the package before the gap could persist.

## Acceptance Criteria

- Playwright suite runs headless and passes locally — evidence: Orchestrator runs `PW_LOCAL_CHROMIUM=/opt/pw-browsers/chromium npm run test:e2e` in `apps/web`; all specs green (captured output in PR body). THIS is the core deliverable; the Orchestrator runs it, not the builder alone.
- Portable browser resolution — evidence: config sets `executablePath` only under `PW_LOCAL_CHROMIUM`; CI job installs its own browser; no `/opt/pw-browsers` string in committed test/config code.
- CI sixth job wired — evidence: `.github/workflows/ci.yml` `web-e2e` job; green on the PR (Level 3).
- Guardian enforces web tests going forward — evidence: `test_web_source_without_e2e_warns` and `test_web_source_with_e2e_clean` in `test_guardian_evolution.py`; the 10 existing guardian-evolution tests + all prior guardian tests still pass unchanged.
- Acceptance retired, not renewed — evidence: `accepted_warnings.json` is `[]`; LES-009 records the mechanism working.
- Full suite green, nothing weakened — evidence: `pytest apps/api/tests` (≥67) + `apps/worker/tests` green; ruff/compileall exit 0.
- Housekeeping folded in — evidence: state docs show AOS-ORCH-004 Merged (PR #42, `74e9370`); Board ID Registry lists AOS-16..23 with Plane-fetched UUIDs.

## Verification Plan

Level 2: ruff/compileall/pytest. Level 4 (local): Orchestrator runs the Playwright suite headless in this container (`PW_LOCAL_CHROMIUM` seam) — the deliverable verifies itself. Level 3: GitHub CI, including the new `web-e2e` job running the suite on ubuntu with its own installed browser. Merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): the suite, config, serve script, CI job, guardian change, tests. Orchestrator (Fable→Opus 4.8): spec, INDEPENDENT execution of the suite headless (mandatory — the point is that it runs), guardian re-verification, lesson, PR, gate. Iterate with the builder if the browser/webServer wiring doesn't launch first try.

## Board Linkage

- Plane: AOS-16 (In Progress, urgent, target 2026-07-28), Sprint 5 cycle `8bc59801-82c5-4550-b188-9f15323a1ddc`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
