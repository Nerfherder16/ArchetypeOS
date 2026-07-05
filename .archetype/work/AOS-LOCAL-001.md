# AOS-LOCAL-001 — WSL Windows 11 Local Verification

## Status

Done — executed on `teevee-1` 2026-07-05 (Level 4 handoff in `docs/HANDOFF.md`; remediations in the same PR)

## Verified Baseline

- First execution of the full runtime on the declared v0.1 target (Windows 11 + WSL 2 Ubuntu, Docker), by the human operator on `teevee-1` via Tailscale.

## Acceptance Criteria and Evidence

- `docker compose up` healthy, API/web respond — evidence: `docker compose ps` all six services Up/healthy; `GET /health` returned `{"status":"ok","api":true,"database":true,"redis":true}` (first all-true health including real Redis).
- Register + scan a real repository end to end — evidence: operator drove the dashboard (project create, repository register, two scans); scan history API returned the artifacts.
- Artifacts written and versioned — evidence: `GET /repositories/{id}/scans` returned two `repository-scan-<uuid>.json` entries with identical checksums (deterministic scanner, unchanged repo) and distinct files.
- `/repositories` mount read-only at runtime — evidence: `touch /repositories/write-probe` inside the api container → "Read-only file system", no file created (probed twice).
- Dashboard persistence — evidence: operator screenshot after reload showing all-green Runtime Health and the project present.
- `scripts/pre_pr_guardian.sh` on WSL — partially: blocked first by Finding 1 (exec bit, fixed in PR #31) then by Finding 4 (test suite not hermetic against `.env`, fixed in this PR); the commands it wraps are CI-covered on the same commits, and the hermeticity fix was verified by running the suite with a `.env` present (32/32).

## Findings

1. Shell scripts committed without the executable bit (fresh clones cannot run them) — fixed in PR #31.
2. Operator Python was 3.13; repo pins 3.12 (`.python-version`) — psycopg-binary 3.2.3 has no cp313 wheels; resolved with a python3.12 venv via deadsnakes.
3. Default host ports collide when co-hosting with the local Plane stack (Postgres 5432) — worked around via `POSTGRES_PORT=5433`; guidance added to `.env.example` in this PR.
4. API test suite was not hermetic: a local `.env` (docker-network hostnames) broke all TestClient tests at app startup — conftest now pins runtime env before app imports; verified 32/32 with and without `.env`.
5. Minor UX note: dashboard project selection is not persisted across reloads (by design in the minimal slice; candidate for a later UI package).

## Board Linkage

- Plane: AOS-7
- Executed on: `teevee-1` (operator) with remote orchestration support
