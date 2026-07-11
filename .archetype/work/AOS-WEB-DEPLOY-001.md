# AOS-WEB-DEPLOY-001 — Static Web Build Behind a Reverse Proxy

## Status

Proposed

## Origin

Closes AOS-REVIEW-002 finding P1-5 (live web deployment is still a Vite dev server), verified in [[LES-033]]. PR #184 (host-allowlist repair) should merge now as a tactical stopgap; this package is the durable replacement. Independent, low-risk, parallelizable.

## Verified Baseline

Confirmed by inspection (2026-07-11):

- `docker-compose.yml:136-151` — `web` service builds `apps/web/Dockerfile`, exposes `${WEB_PORT:-5173}:5173`, passes `VITE_API_BASE_URL` (default `http://localhost:8000`).
- `apps/web/Dockerfile` — single-stage `node:22-alpine`, `CMD ["npm","run","dev"]`; `apps/web/package.json` `"dev": "vite --host 0.0.0.0"`. No `npm run build`, no nginx/caddy, no `/api` proxy.
- Browser hits the API directly via baked `VITE_API_BASE_URL` (LES-L04 documents the tailnet base-URL fragility this causes).
- PR #184 not in the tree (unmerged).

## In-Scope Files

- `apps/web/Dockerfile` — multi-stage: build stage runs `npm ci && npm run build`; serve stage is Caddy or Nginx serving `dist/` with `/api` reverse-proxied to the API container.
- `apps/web/Caddyfile` or `nginx.conf` (new) — single origin, `/api/*` → api:8000, SPA fallback to `index.html`, cache policy (hashed assets immutable, `index.html` no-cache), a real web healthcheck.
- `docker-compose.yml` (web service) — serve the built image on 80/443; healthcheck; drop the dev-server port.
- `apps/web/package.json` — ensure `build` script + preview parity.
- `.github/workflows/ci.yml` — web build job (build must succeed); compose-smoke includes the served web.
- `docs/` deploy note (supersedes the LES-L04 auto-deploy topology); this spec; lesson if a defect is self-found.

## Out-of-Scope

- Operator authentication / HTTPS certs beyond Tailscale Serve wiring (Track F hardening).
- The tactical PR #184 host-allowlist fix (merge separately; this replaces it).
- API/CORS changes beyond what single-origin proxying removes.

## Acceptance Criteria

- The web image serves built static assets, not the Vite dev server — evidence: image `CMD` runs Caddy/Nginx; no `vite` process; `docker run` serves `dist/`.
- `/api` is proxied through the same origin — evidence: compose-smoke: browser request to `/api/health` via the web origin returns the API health payload (no cross-origin base URL).
- SPA routing + cache policy correct — evidence: deep-link to a hash route returns `index.html`; hashed asset carries `immutable`, `index.html` `no-cache`.
- Web healthcheck real — evidence: compose `healthcheck` on the web service passes only when assets are served.
- Existing Playwright e2e still green against the served build — evidence: CI web-e2e.

## Verification Plan

Level 3 is authoritative here (Docker/compose is the artifact): compose-smoke builds the multi-stage image and asserts the served origin + `/api` proxy; web-e2e runs against it. Level 2 for the build. One PR, Manual Merge Gate.

## Suggested Delegation

Sonnet builder (Dockerfile/Caddyfile/compose are mechanical, follow LES-L04 topology). Orchestrator: review the proxy config for correctness (SPA fallback, cache headers, `/api` path), confirm e2e passes against the served build, PR, gate.

## Board Linkage

- Plane: unassigned (parallel track)
- Branch: TBD, cut off latest main per `aos-ship-pr`
