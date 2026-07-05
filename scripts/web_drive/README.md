# Web Drive Harness — Level 4 Dashboard Verification

This is the browser-drive harness the Orchestrator uses to verify dashboard packages at Level 4. It is the current answer to "how do we run the web tests": there is no unit/component web test suite yet (LES-006 — the guardian's accepted-warnings entry for `web-tests-not-enforced` expires **2026-08-01**, forcing that decision). Until then, these drives click through the real running dashboard with headless Chromium and assert on rendered content.

Each drive was written for the package it verified and is kept as both a regression probe and the seed corpus for the future Playwright test suite:

- `drive.mjs` — control tower basics (AOS-CTRL-001, PR #27): project create/select, repository register/scan, scan summary, architecture counts
- `drive_dec.mjs` — Decisions & Research section (AOS-DEC-001, PR #34): research note + linked decision via forms, typed evidence entry confirmed via API
- `drive_digest.mjs` — Nightly Digest section (AOS-LEARN-001, PR #36): run digest, summary counts, draft recommendation rendering, reload persistence

## Running a drive

Three processes: a scratch API, the web dev server, then the drive.

```bash
# 1. API on :8000 with throwaway state (from the repo root)
cd apps/api
DATABASE_URL="sqlite:////tmp/drive.db" ARTIFACT_ROOT=/tmp/drive-artifacts \
REPOSITORY_ROOT=/tmp/drive-repos REDIS_URL=redis://localhost:9999/0 \
PYTHONPATH=. python3 -m uvicorn app.main:app --port 8000 &

# 2. Web dev server on :5173
cd ../web && npm install && npm run dev &

# 3. The drive
cd ../../scripts/web_drive && npm install
npm run drive:digest        # or drive:tower / drive:decisions
```

Each drive prints `PASS`/`FAIL` per check, saves a full-page screenshot, and exits non-zero on any failure.

## Environment notes

- **Managed Claude containers**: Chromium is pre-installed; the drives use `chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })`. On other machines, either run `npx playwright install chromium` and drop the `executablePath` option, or set it to your Chromium binary.
- **State pollution**: drives create projects/repos by name and assert on them. Re-runs against a dirty database can false-fail — delete the sqlite file and restart the API between runs.
- **Selectors**: drives locate form fields by their exact placeholders (`'New project name'`, `'Repository name'`, `'Local path'`, `'Research note title'`, `'Summary'`, `'Decision title'`, `'Decision text'`). If a placeholder changes in `apps/web/src/main.tsx`, update the drive.
- **demo-repo**: scan flows register `local_path: 'demo-repo'`; ensure a directory of that name exists under the API's `REPOSITORY_ROOT` (any small folder works; no tests inside it makes the missing-tests draft rule observable in the digest drive).

## Relationship to CI

CI enforces strict `tsc` + `vite build` only. These drives are manual Level 4 evidence recorded in PR bodies under the Manual Merge Gate. Wiring them (or a proper Playwright suite grown from them) into CI is the web-tests package — do it before the 2026-08-01 acceptance expiry.
