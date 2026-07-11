# AOS-WEB-DEPLOY-001 (finding P1-5): a production web image — build the Vite SPA to
# static assets, then serve them behind Caddy (with a single-origin /api reverse
# proxy) instead of shipping the Vite dev server.

# --- build stage: compile the SPA to static assets ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
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
