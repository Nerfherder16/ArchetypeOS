# Runtime Decision Record

## Status

Accepted for v0.1.

## Decision

ArchetypeOS v0.1 will use a local-first Docker Compose runtime.

## Chosen Stack

- API: FastAPI
- Worker: Python worker service
- Web: React + Vite
- Database: Postgres
- Queue/cache: Redis
- Runtime: Docker Compose
- Local deployment target: CasaOS or Portainer
- Data storage: local Docker volumes
- Repository access: mounted local repository paths, read-only by default

## Why This Stack

### FastAPI

FastAPI is a strong fit for a Python-centered engineering intelligence platform because it is simple, typed, async-capable, and easy to pair with Python workers, repository scanners, model adapters, and future agent orchestration.

### React + Vite

React/Vite gives a fast dashboard shell and supports graph-heavy UI development, workspace layouts, command palettes, and future visual engineering dashboards.

### Postgres

Postgres is the initial system of record for projects, repositories, artifacts, jobs, scores, decisions, reports, and knowledge metadata.

### Redis

Redis provides simple job queue and cache support for v0.1 without overcommitting to a heavier orchestration system.

### Docker Compose

Docker Compose keeps v0.1 simple, local-first, and compatible with CasaOS and Portainer.

## Deferred Alternatives

- Kubernetes: too heavy for v0.1.
- Next.js: useful later, but Vite is simpler for dashboard shell.
- Neo4j or graph database: defer until the graph model proves itself.
- Celery/RQ/Temporal: defer final job-runner decision until worker needs are proven.
- Full OAuth/RBAC: defer until multi-user requirements are explicit.

## Runtime Services For v0.1

```text
web
api
worker
postgres
redis
```

## Safety Defaults

- Repository mounts read-only by default.
- No destructive actions by default.
- No automatic commits.
- No automatic external messages.
- No production infrastructure changes.
- Paid APIs disabled unless explicitly configured.

## Acceptance Criteria

- `docker compose up` starts all services.
- API health endpoint responds.
- Web app loads.
- Worker can run a test job.
- API can connect to Postgres and Redis.
- Local volumes persist data.

## Review Trigger

This decision should be revisited after v0.1 proves or fails the core loop.
