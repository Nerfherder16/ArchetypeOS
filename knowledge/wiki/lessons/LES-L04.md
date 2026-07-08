# LES-L04 — a live cloud→teevee auto-deploy needs tracked compose env, a tailnet-baked frontend, and a poller (webhooks can't reach a tailnet host)

## Aliases

- "so when the cloud session makes a change it can deploy and I can see it"
- override file is a deploy single-point-of-failure
- Vite bakes VITE_* at build time; remote dashboard hits the viewer's localhost
- why the dashboard is blank from my laptop but fine on the box
- live-deploy watcher / auto-pull cron

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Operator ask (2026-07-07): "confirm exact url. i'd like to be able to live deploy so when the cloud session makes a change it can deploy and I can see it."
- The teevee stack was started with the council/pool worker env supplied by an **untracked** `docker-compose.override.yml`. A `git pull`-based auto-deploy never touches untracked files, so the override survives — but it is invisible to the repo, drifts silently, and must be hand-recreated on any fresh checkout. Forwarding the same `${VAR:-default}` env in the tracked `docker-compose.yml` (this change set) removes that dependency; the deterministic path is unchanged because every var defaults to empty/false.
- The frontend resolves its API base as `import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'`. Vite bakes `VITE_*` at build / dev-server-start, not at request time. A viewer opening `http://100.123.29.114:5173` from their laptop would have the bundle call **their own** `localhost:8000` (nothing there) unless the container is built/started with `VITE_API_BASE_URL=http://100.123.29.114:8000` (the box's tailnet IP). Verified the running web container carries that value and `http://100.123.29.114:8000/health` → 200.
- Proof the mechanism works end-to-end: while wiring it, the cloud session merged #106 (AOS-OPS-002) advancing `origin/main` to `e836b07`; the first run of the poller fetched it, fast-forwarded, `docker compose up -d --build`, and logged `deploy OK at e836b07` / `health: 200` — a real cloud commit deployed with zero human action.

## Linked Decisions / Projects

- `docker-compose.yml` (worker service) — this change: council/pool env forwarded in the tracked compose
- `~/aos-autodeploy.sh` on teevee + user crontab (`*/2 * * * *`) — the poller (outside the repo so `git pull` never clobbers it)
- `~/.claude/skills/deploy-archetypeos/SKILL.md` — deploy runbook + the no-echo-secrets rule
- [[LES-L03]] — the other half of the tandem-deploy story (auto-rebase)

## Content

- Event: making cloud-session merges appear on a tailnet-only box automatically. Three things had to line up, and each is a distinct failure mode if missed: (1) the frontend must be built with the **server's** reachable API URL, or a remote viewer silently hits their own localhost; (2) the deploy must not depend on untracked files, or a fresh checkout ships without the feature env; (3) something must *pull*, because a GitHub webhook or Action cannot reach a host that only exists on the tailnet.
- Fix (mechanism, not discipline): a teevee-side cron poller does `git fetch origin main`; if `HEAD != origin/main`, `git pull --ff-only` then `docker compose up -d --build`, with a `flock` guard so a slow build never overlaps the next tick and idle ticks staying silent. Pull-based (not push/webhook) is the right topology for a tailnet host — no inbound exposure, and it degrades safely (if WSL is down the tick simply doesn't run; it catches up on the next boot). `--ff-only` refuses to deploy a diverged local branch instead of guessing.
- Generalization: "live deploy to a private host" = bake the reachable backend URL into the frontend at build time + keep all runtime env in tracked config + poll from the host rather than pushing to it. Anything that depends on an untracked override or a build-time default is a latent "works on the box, broken on a fresh clone / broken for a remote viewer" bug.
