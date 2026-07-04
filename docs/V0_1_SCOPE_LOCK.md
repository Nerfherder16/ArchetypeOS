# v0.1 Scope Lock

## Purpose

This document locks the first implementation scope for ArchetypeOS.

The goal is to prevent architecture drift before code begins.

## v0.1 Thesis

Build the smallest coherent ArchetypeOS runtime that proves:

```text
Project Registry -> Repository Scan -> Architecture Draft -> Decisions/Research -> PR Guardian -> Nightly Learning -> Dashboard Review
```

## In Scope For v0.1

### Runtime

- Docker Compose local runtime
- FastAPI API service
- React/Vite dashboard shell
- Python worker service
- Postgres
- Redis
- local data volumes
- `.env.example`

### Project And Repository

- project registry
- repository registration by local path
- read-only repository scanner
- repository metadata capture
- repository DNA draft

### Architecture

- first-pass Architecture Spine Graph data model
- graph draft generated from repository scan
- node and edge confidence fields
- manual correction fields

### Knowledge

- local knowledge vault structure
- wiki-style `index.md`, `hot.md`, `log.md`, and `overview.md`
- source manifest for delta tracking
- basic research notes
- decision cards
- ADRs

### Validation

- PR Guardian first pass
- diff review report
- documentation impact detection
- test gap detection
- risk flags

### Learning

- manually runnable nightly self-learning digest
- repeated-task detection draft
- recommended docs/tests/skills/research items

### Interface

- dashboard shell
- project list
- project overview
- repository scan results
- architecture graph placeholder
- voice inbox text ingestion placeholder
- nightly digest view

## Explicitly Out Of Scope For v0.1

- autonomous code edits
- automatic commits or PRs
- production deployment
- paid API execution by default
- full voice streaming
- desktop control
- browser automation
- wake word
- full workflow automation
- multi-user auth
- marketplace
- full graph database
- advanced simulation lab
- advanced multi-monitor support
- full local LLM orchestration

## Approval Rule

Any feature not listed as in scope requires an RFC before implementation.

## v0.1 Acceptance Criteria

- Local Docker runtime starts reliably.
- Dashboard shell loads.
- API health endpoint responds.
- Worker can run a job.
- A repository can be registered.
- Repository scanner produces a read-only report.
- Architecture graph draft is generated as data.
- Decision/research artifacts can be created and viewed.
- PR Guardian can produce a first-pass review report.
- Nightly learning digest can run manually.
- Knowledge vault structure exists and is populated with initial artifacts.

## Principle

v0.1 proves the operating loop. It does not need to implement every future engine.
