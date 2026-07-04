# RFC-0001 — MVP Runtime

## Status

Accepted for v0.1.

## Summary

Use a local-first Docker Compose runtime with FastAPI, React/Vite, Python worker, Postgres, and Redis.

## Problem

ArchetypeOS needs an implementation baseline that is simple enough to build quickly but structured enough to support agents, jobs, projects, repository scans, reports, and knowledge artifacts.

## Proposal

Create a local runtime with these services:

```text
web
api
worker
postgres
redis
```

## Goals

- Start with `docker compose up`.
- Support CasaOS and Portainer.
- Keep repository mounts read-only by default.
- Persist data locally.
- Support background worker jobs.
- Provide a dashboard shell.

## Non-Goals

- Kubernetes
- multi-tenant auth
- production deployment
- full distributed node system
- automatic PR creation
- desktop/browser automation

## Acceptance Criteria

- API health check works.
- Web shell loads.
- Worker starts.
- API connects to Postgres and Redis.
- Local volumes persist data.
- Basic job can run.

## Final Judge Verdict

Accepted.
