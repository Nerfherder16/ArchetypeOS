# v0.1 Runtime Foundation Implementation

## Summary

This implementation establishes the v0.1 local control plane foundation for ArchetypeOS.

Implemented runtime components:

- Docker Compose
- FastAPI API service
- React/Vite dashboard shell
- Python worker service
- Postgres
- Redis
- Local Docker volumes
- `.env.example`
- Configuration through environment variables
- Health checks
- Project registry
- Repository registration by local path
- Read-only repository scanner
- Artifact storage
- Worker queue
- Basic dashboard
- Knowledge vault starter structure

## Architecture Impact

The implementation creates the first concrete runtime topology described by the System Architecture and Runtime Decision Record:

```text
web -> api -> postgres
api -> redis
worker -> redis
worker -> postgres
api/worker -> local artifact volume
api/worker -> read-only repository mount
```

The API is the control plane boundary for project, repository, job, artifact, and scan operations. The worker proves queue execution without enabling autonomous coding or high-impact actions.

## Scope Verification

### In Scope

- Runtime services match `docs/RUNTIME_DECISION_RECORD.md`.
- Runtime components match `docs/V0_1_SCOPE_LOCK.md`.
- Capability placement maps to `docs/CAPABILITY_MAP.md` Layer 11.
- Architecture graph is stored as editable node and edge data, not a graph database.
- Repository scanner is read-only and path-constrained to the mounted repository root.

### Explicitly Deferred

Not implemented:

- desktop automation
- browser automation
- wake word
- voice streaming
- marketplace
- autonomous coding
- automatic PRs
- simulation lab
- graph database
- multi-user auth

## Acceptance Criteria Verification

| Acceptance Criteria | Status | Evidence |
| --- | --- | --- |
| Docker Compose starts all services | Implemented, requires runtime verification | `docker-compose.yml` defines `web`, `api`, `worker`, `postgres`, and `redis`. |
| API health endpoint responds | Implemented | `GET /health` checks API, database, and Redis. |
| Web app loads | Implemented | `apps/web` React/Vite shell fetches health and projects. |
| Worker can run a test job | Implemented | API pushes queued job IDs to Redis; worker marks jobs running/completed. |
| API can connect to Postgres and Redis | Implemented | health endpoint verifies both. |
| Local volumes persist data | Implemented | Compose defines Postgres, Redis, and Archetype data volumes. |
| Repository can be registered | Implemented | `POST /projects/{project_id}/repositories`. |
| Repository scanner produces read-only report | Implemented | Scanner walks repository files without writes and writes report to artifact volume. |
| Architecture graph draft is generated as data | Implemented | Scanner creates `architecture_nodes` and `architecture_edges`. |
| Artifact persistence exists | Implemented | `artifacts` table and scan JSON artifact. |

## Tests

Added:

- scanner unit test for manifest/language/deployment detection.
- route presence test for health endpoint.
- worker queue constant test.

Local syntax verification was run with Python bytecode compilation for API and worker modules.

## Known Limitations

- Alembic migrations are not yet added; v0.1 uses SQLAlchemy `create_all` for first scaffold speed.
- The dashboard is intentionally unpolished and only validates runtime visibility.
- Worker executes a safe test job only; domain jobs will be added after the foundation is verified.
- The repository scanner is intentionally shallow and deterministic.
- The graph model uses relational tables and JSON fields because a graph database is deferred.

## Future Work

Next milestones should proceed in documented order:

1. Verify `docker compose up` on the target local environment.
2. Exercise project creation and repository registration against a mounted local repository.
3. Run repository scan and inspect generated RepositoryDNA, ArchitectureNode, ArchitectureEdge, and Artifact records.
4. Add decision/research endpoints after runtime foundation is verified.
5. Add PR Guardian first pass only after repository scan loop is stable.

## RFC Triggers

Open an RFC before adding any feature outside v0.1 scope, especially:

- write-capable repository actions
- automatic commits or PRs
- multi-user auth
- graph database
- external paid APIs
- desktop/browser/voice automation
