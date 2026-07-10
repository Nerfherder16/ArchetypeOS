## Layer 11: Runtime and Infrastructure

Owns deployment and execution environment.

Capabilities:

- Windows 11 host runtime
- WSL 2 Ubuntu runtime target
- WSL filesystem layout
- WSL Docker runtime verification
- CasaOS or Portainer deployment
- Docker Compose
- Postgres
- Redis
- API
- worker
- web dashboard
- GPU node
- WSL node
- GitHub integration
- database schema migrations (Alembic)

Primary artifacts:

- docs/WSL_WIN11_RUNTIME_TARGET.md
- docs/DISTRIBUTED_RUNTIME.md
- docs/LOCAL_LLM_GPU_NODE.md
- docs/CLAUDE_CODE_BRIDGE.md
- docs/CONNECTOR_POLICY.md (AOS-CONNECTOR-001: connector registry governance — privacy class, egress, browser-exposed, health)
- docs/DATABASE_MIGRATIONS.md
- docker-compose.yml
- .env.example
- apps/web
- apps/api
- apps/api/alembic/ (Alembic migrations; baseline schema)
- apps/api/docker-entrypoint.sh (runs migrations before serving)
- apps/worker
- apps/scheduler (control-plane scheduler: materializes due schedules into jobs; RFC-0007)
- packages/aos_core (shared domain library: config/database/models/scanner + scan/digest/jobs/scheduler services; RFC-0006)
- docs/rfc/RFC-0006-Shared-Core-Domain-Library.md
- docs/rfc/RFC-0007-Scheduling-Control-Plane-Job-Origination.md (schedules-as-data; control plane decides + stores, nodes execute)

