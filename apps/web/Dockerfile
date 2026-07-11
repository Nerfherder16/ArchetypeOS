# AOS-WEB-DEPLOY-001 (finding P1-5): a production web image — build the Vite SPA to
# static assets, then serve them behind Caddy (with a single-origin /api reverse
# proxy) instead of shipping the Vite dev server.

# --- build stage: compile the SPA to static assets ---
# AOS-WEB-LOCK-001: build on the glibc (Debian) node image, NOT alpine/musl. npm
# records only the HOST platform's Rollup native binary in the lockfile
# (@rollup/rollup-linux-x64-gnu), so a musl (alpine) `npm ci` hit npm/cli#4828
# ("Cannot find module @rollup/rollup-linux-x64-musl") — the reason the old build
# deleted the lockfile and ran `npm install`, making every build non-reproducible.
# Building on glibc matches the locked gnu binary AND the CI ubuntu runner, so a
# plain `npm ci` from the committed lockfile is reproducible. The serve stage stays
# alpine (Caddy) — it only copies static assets, no node runtime.
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
# `npm ci` installs exactly the committed lockfile and FAILS if it and package.json
# disagree, so a build can no longer silently drift from the pinned dependency graph.
RUN npm ci --no-audit --no-fund
COPY . .
# Single origin: the API is reached at /api (proxied by Caddy), so the baked base
# is a RELATIVE url — a tailnet viewer hits their OWN origin, fixing the baked-
# absolute-IP fragility of the dev-server topology (LES-L04). VITE_* are compiled
# in at build time, so they are build args, not runtime env.
ARG VITE_API_BASE_URL=/api
ARG VITE_SOTTO_WS_URL=
ARG VITE_SOTTO_TOKEN=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_SOTTO_WS_URL=$VITE_SOTTO_WS_URL \
    VITE_SOTTO_TOKEN=$VITE_SOTTO_TOKEN
RUN npm run build

# --- serve stage: Caddy serves dist/ and reverse-proxies /api ---
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80
