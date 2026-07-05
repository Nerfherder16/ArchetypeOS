# AOS-CTRL-001 — Engineering Control Tower First Dashboard Surface

## Status

In Review

## Verified Baseline

Confirmed by inspection:

- `apps/web/src/main.tsx` is a single-file React 19 shell: runtime health, project list, static v0.1 placeholder list. Plain `fetch`, no router, strict TypeScript, `build = tsc && vite build`. CI enforces the build only (no UI tests in v0.1).
- API today: projects CRUD-lite, repository register/list, `POST /repositories/{id}/scan`, `GET /projects/{id}/architecture` (from AOS-ARCH-001), artifacts list. There is NO endpoint to read a repository's stored scan results (`RepositoryDNA`) — the scan POST response is the only way to see them, so the dashboard cannot show prior scan summaries after reload.
- `RepositoryDNA` model has `language_mix`, `package_managers`, `deployment_files`, `risk_flags`, `scan_summary`, `confidence`, `evidence`.
- CORS defaults allow `http://localhost:5173`; web reads `VITE_API_BASE_URL`.

## In-Scope Files

- `apps/api/app/main.py` (one new read route: repository DNA)
- `apps/api/app/schemas.py` (`RepositoryDnaRead`)
- `apps/api/tests/test_dna_endpoint.py` (new)
- `apps/web/src/main.tsx`, `apps/web/src/api.ts` (new; keep the web change to at most these two files plus types)
- state docs + this spec

## Out-of-Scope

- routing/library additions (no react-router, no UI framework, no CSS framework)
- UI test infrastructure (v0.1 has none; runtime verification is done by the Orchestrator driving the app)
- nightly digest view, voice inbox (placeholders remain)
- architecture graph visualization (counts/summary only)
- any change to scanner, worker, models, or compose

## Acceptance Criteria

- Stored scan results are readable via API: `GET /repositories/{repository_id}/dna` returns DNA fields, 404 for unknown repository or never-scanned repository — evidence: `test_dna_endpoint.py` (both paths).
- Dashboard shows project list and allows creating a project — evidence: driven-browser check (project created via form appears in list).
- Dashboard shows a selected project's repositories and allows registering one by local path — evidence: driven-browser check.
- Dashboard can trigger a scan and shows a scan summary (languages, package managers, risk flags, has_docker/has_ci/has_tests, last_scanned_at) from stored DNA — evidence: driven-browser check + DNA fetch after reload.
- Dashboard shows architecture graph node/edge counts for the selected repository — evidence: driven-browser check against `GET /projects/{id}/architecture`.
- Failures are isolated: health being down does not block project/repository data — evidence: driven-browser check with redis absent (health shows down, rest works).
- `npm run build` (tsc strict + vite) passes; API suite passes — evidence: build exit 0, pytest green in CI.

## Verification Plan

Level 2: ruff/compileall/pytest (25 existing + new DNA tests), `npm run build`. Level 4 (local): run uvicorn with sqlite (redis absent), `vite dev`, drive the dashboard with headless Chromium (Playwright) through the full project → register → scan → summary flow. Level 3: GitHub CI on the PR; merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): API route/schema/tests plus the dashboard implementation. Orchestrator (Fable): spec, review, browser-driven runtime verification, PR, merge gate.

## Board Linkage

- Plane: AOS-8 (In Progress)
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
