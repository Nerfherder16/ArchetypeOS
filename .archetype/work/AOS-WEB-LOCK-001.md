# AOS-WEB-LOCK-001 — Reproducible frontend dependency installation

## Status

In Review

## Verified Baseline

Confirmed on `main` @ `267f50f`:

- `apps/web/Dockerfile:13` — `RUN rm -f package-lock.json && npm install --no-audit --no-fund`: deletes the committed lockfile and resolves fresh from `package.json` every build (non-reproducible).
- `.github/workflows/ci.yml:157,177` — web-build + web-e2e jobs use `npm install`, not `npm ci`.
- `apps/web/package-lock.json` IS committed, Node 22 pinned, Caddy `/api`+SPA+`/healthz` present. But the lockfile records only the HOST platform's Rollup native (`@rollup/rollup-linux-x64-gnu`), not musl — a musl (alpine) `npm ci` hit npm/cli#4828, which is why the delete-and-install workaround existed.
- No dependency-lock consistency test.

## In-Scope Files

- `apps/web/Dockerfile` (glibc build stage + `npm ci`)
- `.github/workflows/ci.yml` (web jobs → `npm ci` + lockfile check step)
- `apps/web/scripts/check-lockfile.mjs` (new — consistency guard)
- `docs/capability-map/layer-11.md`

## Out-of-Scope

- Regenerating the whole dependency graph / bumping versions (kept the committed lockfile as-is).
- The Caddy serve stage, `/api` proxy, SPA fallback, `/healthz` (unchanged).

## Acceptance Criteria

- Two clean builds from one commit use the same dependency graph — evidence: `npm ci` from the committed lockfile (deterministic), on glibc in both Docker and CI.
- `npm ci` succeeds on the CI runner — evidence: ci.yml web-build/web-e2e jobs run `npm ci` (validated locally: `npm ci` exit 0).
- `npm ci` succeeds inside the Docker build; Vite build succeeds; Caddy image starts; `/healthz` + `/api` + SPA fallback work — evidence: compose-smoke `docker compose build web` + `up web` + curl :5173 (builds and starts the web image in CI).
- No Vite dev server in production — evidence: serve stage is `caddy:2-alpine` (unchanged).
- Dependency-lock consistency test — evidence: `apps/web/scripts/check-lockfile.mjs` (CI step) asserts lockfileVersion ≥ 3, name/version sync, required Rollup native present.

## Verification Plan

Level 2 — local `npm ci` + `npm run build` + `node scripts/check-lockfile.mjs`; CI web jobs + compose-smoke build/start the image.

## Board Linkage

- Branch: `claude/aos-web-lock-001`
