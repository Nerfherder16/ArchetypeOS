# v0.1 Data Model

## Purpose

This document defines the first runtime schema for ArchetypeOS v0.1 before endpoint implementation.

It implements the documented v0.1 scope: local Docker runtime, project registry, repository registration, read-only repository scanner, artifact storage, worker queue, health endpoints, and dashboard shell.

## Scope Traceability

- `docs/CAPABILITY_MAP.md` Layer 11 authorizes Docker Compose, Postgres, Redis, API, worker, and web dashboard.
- `docs/V0_1_SCOPE_LOCK.md` authorizes runtime, project/repository, architecture graph draft, knowledge artifacts, validation records, learning digest, and dashboard shell.
- `docs/RUNTIME_DECISION_RECORD.md` accepts FastAPI, Python worker, React/Vite, Postgres, Redis, Docker Compose, local volumes, and read-only repository access.
- `docs/ARCHITECTURE_STUDIO.md` defines minimum architecture node and edge fields.
- `docs/AUTHORITY_APPROVAL_ENGINE.md` defines authority grants and approval records.

## Model Conventions

Every table uses:

- `id`: UUID primary key.
- `created_at`: UTC creation timestamp.
- `updated_at`: UTC update timestamp.
- `version`: integer optimistic version.
- `status`: lifecycle status string.
- `created_by`: actor identifier, defaulting to `system`.
- `updated_by`: actor identifier, defaulting to `system`.
- `metadata`: JSON object for extensibility.

Where a model represents generated or inferred knowledge, it also records evidence, confidence, and provenance where applicable.

## Core Status Values

Status values are intentionally simple in v0.1 and may be specialized later through an RFC:

- `draft`
- `active`
- `queued`
- `running`
- `completed`
- `failed`
- `archived`
- `deprecated`
- `blocked`
- `requires_approval`

## Models

### Project

Represents a managed engineering project or product.

Fields:

- `id`
- `name`
- `slug`
- `description`
- `status`
- `version`
- `created_at`
- `updated_at`
- `created_by`
- `updated_by`
- `metadata`

Relationships:

- one Project has many Repositories.
- one Project has many Decisions, ResearchNotes, Recommendations, Artifacts, Jobs, Evaluations, Risks, Benchmarks, Experiments, NightlyDigests, AuthorityGrants, and ApprovalRecords.

### Repository

Represents a local repository registered to a project.

Fields:

- `id`
- `project_id`
- `name`
- `local_path`
- `default_branch`
- `remote_url`
- `status`
- `is_read_only`
- `last_scanned_at`
- `version`
- audit fields

Relationships:

- belongs to Project.
- has one RepositoryDNA draft.
- has many ArchitectureNodes, ArchitectureEdges, Artifacts, Jobs, Risks, Benchmarks, and Experiments.

### RepositoryDNA

Stores first-pass repository identity and scan-derived characteristics.

Fields:

- `id`
- `repository_id`
- `purpose`
- `maturity`
- `language_mix`
- `package_managers`
- `frameworks`
- `runtime_services`
- `deployment_files`
- `risk_flags`
- `scan_summary`
- `confidence`
- `evidence`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Repository.

### ArchitectureNode

Represents editable Architecture Spine Graph node data.

Fields:

- `id`
- `project_id`
- `repository_id`
- `label`
- `type`
- `parent_id`
- `confidence`
- `evidence`
- `risks`
- `related_decision_ids`
- `manual_correction`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- optionally belongs to Repository.
- may have a parent ArchitectureNode.
- participates in ArchitectureEdges.

### ArchitectureEdge

Represents an editable relationship between architecture nodes.

Fields:

- `id`
- `project_id`
- `repository_id`
- `from_node_id`
- `to_node_id`
- `type`
- `confidence`
- `evidence`
- `manual_correction`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- optionally belongs to Repository.
- connects two ArchitectureNodes.

### Decision

Stores a decision card or ADR metadata.

Fields:

- `id`
- `project_id`
- `title`
- `context`
- `decision`
- `alternatives`
- `tradeoffs`
- `consequences`
- `evidence`
- `confidence`
- `approved_by`
- `approved_at`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- may be referenced by ArchitectureNodes and Recommendations.

### ResearchNote

Stores evidence-backed research notes.

Fields:

- `id`
- `project_id`
- `title`
- `question`
- `summary`
- `sources`
- `findings`
- `freshness`
- `confidence`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- may support Decisions and Recommendations.

### Recommendation

Stores recommendation cards.

Fields:

- `id`
- `project_id`
- `title`
- `recommendation`
- `rationale`
- `alternatives`
- `pros`
- `cons`
- `risk`
- `effort`
- `dependencies`
- `acceptance_criteria`
- `evidence`
- `confidence`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- may link to ResearchNotes and Decisions through JSON references in v0.1.

### Artifact

Stores generated or imported runtime artifacts.

Fields:

- `id`
- `project_id`
- `repository_id`
- `job_id`
- `artifact_type`
- `name`
- `path`
- `content_type`
- `checksum`
- `size_bytes`
- `summary`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- optionally belongs to Repository and Job.

### KnowledgePage

Represents a human-readable knowledge vault page.

Fields:

- `id`
- `project_id`
- `title`
- `vault_path`
- `page_type`
- `validation_state`
- `source_refs`
- `checksum`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.

### Job

Represents queued and executed work.

Fields:

- `id`
- `project_id`
- `repository_id`
- `job_type`
- `status`
- `priority`
- `payload`
- `result`
- `error`
- `queued_at`
- `started_at`
- `finished_at`
- `attempts`
- `version`
- audit fields

Relationships:

- belongs to Project.
- optionally belongs to Repository.
- has many Artifacts.

### Agent

Represents an agent capability registration.

Fields:

- `id`
- `name`
- `agent_type`
- `capabilities`
- `authority_level`
- `status`
- `version`
- audit fields

Relationships:

- may produce Jobs, Recommendations, Evaluations, and ApprovalRecords through metadata references in v0.1.

### Engine

Represents an engine capability registration.

Fields:

- `id`
- `name`
- `engine_type`
- `capabilities`
- `inputs`
- `outputs`
- `status`
- `version`
- audit fields

Relationships:

- may produce Jobs, Evaluations, Recommendations, and Artifacts through metadata references in v0.1.

### Evaluation

Stores engineering evaluation results.

Fields:

- `id`
- `project_id`
- `repository_id`
- `evaluation_type`
- `score`
- `findings`
- `evidence`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- optionally belongs to Repository.

### Risk

Stores risk register items.

Fields:

- `id`
- `project_id`
- `repository_id`
- `title`
- `description`
- `severity`
- `likelihood`
- `mitigation`
- `evidence`
- `owner`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- optionally belongs to Repository.

### Benchmark

Stores benchmark records.

Fields:

- `id`
- `project_id`
- `repository_id`
- `name`
- `benchmark_type`
- `metric`
- `value`
- `unit`
- `environment`
- `evidence`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- optionally belongs to Repository.

### Experiment

Stores experiment records.

Fields:

- `id`
- `project_id`
- `repository_id`
- `title`
- `hypothesis`
- `method`
- `result`
- `conclusion`
- `evidence`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- optionally belongs to Repository.

### NightlyDigest

Stores manually runnable v0.1 learning digest output.

Fields:

- `id`
- `project_id`
- `digest_date`
- `summary`
- `changes`
- `recommendations`
- `repeated_tasks`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.

### AuthorityGrant

Stores temporary or persistent delegated authority.

Fields:

- `id`
- `project_id`
- `scope`
- `capability`
- `target`
- `authority_level`
- `expires_at`
- `approver`
- `reason`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- may be referenced by ApprovalRecords.

### ApprovalRecord

Stores approval requests and outcomes.

Fields:

- `id`
- `project_id`
- `authority_grant_id`
- `actor`
- `agent`
- `tool`
- `action_level`
- `requested_capability`
- `target`
- `reason`
- `approval_status`
- `output`
- `rollback_notes`
- `status`
- `version`
- audit fields

Relationships:

- belongs to Project.
- optionally belongs to AuthorityGrant.

## v0.1 Relationship Strategy

The first implementation uses Postgres relational tables and JSON columns for flexible evidence, metadata, and cross-reference fields. A graph database is explicitly deferred by `docs/V0_1_SCOPE_LOCK.md`; graph-shaped data is stored relationally through `architecture_nodes` and `architecture_edges`.

## Acceptance Criteria Verification

- Data models are documented before endpoint implementation.
- Models include IDs, timestamps, relationships, status, versioning, and audit fields.
- Architecture nodes and edges include confidence and evidence fields.
- Authority and approval models include audit fields required by the Authority and Approval Engine.
- Graph database and autonomous execution remain deferred.

## Future Work

- Normalize many-to-many evidence links after v0.1 proves access patterns.
- Add migrations with Alembic once schema churn stabilizes.
- Add graph export formats for Architecture Studio.
- Add approval workflows before enabling higher-impact actions.
