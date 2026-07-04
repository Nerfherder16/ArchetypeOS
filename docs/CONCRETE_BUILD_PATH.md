# Concrete Build Path

## Purpose

This document defines the path from concept to implementation.

No application code should be written until the foundation, capability map, and MVP boundaries are clear.

## Guiding Rule

Build the smallest coherent version of ArchetypeOS that proves the platform thesis:

```text
Research -> Model -> Decide -> Validate -> Learn
```

Do not attempt to build every future capability in the first implementation.

## Phase 0: Foundation Complete

Required before code:

- Engineering Constitution
- Capability Map
- System Architecture
- Engine Catalog
- Agent Catalog
- Repository Knowledge Standard
- Decision Lifecycle
- Templates
- Master Roadmap
- Concrete Build Path

Acceptance criteria:

- A new agent can read the repo and understand the mission.
- All major capabilities have a place in the map.
- MVP scope is explicit.
- Non-MVP scope is explicit.

## Phase 1: Runtime Skeleton

Build only the local control plane skeleton.

Components:

- docker-compose.yml
- .env.example
- apps/web
- apps/api
- apps/worker
- Postgres
- Redis
- local data volume
- repo mount volume

Acceptance criteria:

- Docker Compose starts.
- Web shell loads.
- API health endpoint responds.
- Worker starts.
- Postgres and Redis connect.

## Phase 2: Project Registry

Build the system of record for projects and repositories.

Features:

- create project
- attach repo path
- list projects
- project overview
- repository DNA draft

Acceptance criteria:

- User can register ArchetypeOS, AiGentOS, CPA Connector, Jellystream, or another repo.
- System stores repo metadata.
- Project appears in dashboard.

## Phase 3: Repository Scan MVP

Build first-pass read-only repo scanner.

Features:

- folder map
- language detection
- package manifest detection
- Docker detection
- API route hints
- database model hints
- worker hints
- risk flags

Acceptance criteria:

- Scanner produces a repository map.
- Scanner never writes to repo.
- Scanner output is stored.

## Phase 4: Architecture Spine Graph MVP

Convert repo scan output into editable graph data.

Features:

- spine nodes
- branch nodes
- edges
- node metadata
- confidence score
- manual correction field

Acceptance criteria:

- User can view an architecture graph draft.
- Graph is stored as data, not just an image.
- Uncertain relationships are marked.

## Phase 5: Decision and Research MVP

Build core reasoning artifacts.

Features:

- decision cards
- ADRs
- research notes
- recommendation cards
- evidence links
- confidence

Acceptance criteria:

- User can create and view decisions.
- Research can be linked to decisions.
- Recommendations require evidence field.

## Phase 6: PR Guardian First Pass

Build safe diff review.

Features:

- read git diff
- identify touched files
- detect docs needed
- detect test gaps
- detect risk areas
- output approve/warn/block draft

Acceptance criteria:

- PR Guardian produces a review report.
- No code is modified.
- Findings include evidence.

## Phase 7: Nightly Self Learning MVP

Build digest loop.

Features:

- collect daily repo changes
- collect notes and voice inbox items
- summarize activity
- detect repeated tasks
- recommend docs/tests/skills/research
- generate morning brief

Acceptance criteria:

- Nightly job can run manually.
- Digest is saved.
- Recommendations are drafts only.

## Phase 8: Voice Inbox MVP

Build capture-first voice workflow.

Features:

- text transcript ingestion first
- audio adapter later
- project assignment
- intent classification
- draft action
- dashboard review

Acceptance criteria:

- A voice note can become a research request, decision draft, architecture note, or task.
- Driving mode remains capture-only.

## Phase 9: Agent Council MVP

Build visible council flow without over-automation.

Features:

- run selected agents
- store outputs
- show statuses
- Final Judge synthesis

Acceptance criteria:

- Research, Architecture, Fitness, Security, and Final Judge can produce structured outputs.
- Disagreements are visible.

## Phase 10: Alpha Review

Before expanding, run ArchetypeOS on its own repo.

Questions:

- Did it understand itself?
- Did it find stale docs?
- Did it generate useful decisions?
- Did PR Guardian find real risks?
- Did nightly learning produce useful recommendations?

Acceptance criteria:

- ArchetypeOS can evaluate ArchetypeOS.
- Output is useful enough to guide next development.

## Deferred Until After Alpha

- full autonomous build actions
- full marketplace
- full simulation lab
- advanced voice streaming
- production cloud deployment
- advanced cost engine
- automatic PR creation
- external publishing

## Final Rule

Every phase must improve the repository knowledge base as well as the code.
