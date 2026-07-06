# Capability Map

## Purpose

The Capability Map defines how ArchetypeOS capabilities fit together.

It prevents the platform from becoming a collection of unrelated ideas. Every engine, agent, dashboard, workflow, and runtime component should map to a coherent capability layer.

## North Star

ArchetypeOS is an Engineering Intelligence Platform that helps users:

```text
Research -> Model -> Decide -> Build -> Verify -> Validate -> Learn -> Evolve
```

## Capability Layers

```text
Layer 0: Constitution and Governance
Layer 1: Knowledge and Memory
Layer 2: Research and Evidence
Layer 3: Architecture and Modeling
Layer 4: Decision and Recommendation
Layer 5: Design and User Experience
Layer 6: Build and Execution
Layer 7: Validation and Release Gates
Layer 8: Self Learning and Evolution
Layer 9: Portfolio and Organizational Intelligence
Layer 10: Interface and Interaction
Layer 11: Runtime and Infrastructure
Layer 12: Orchestration and Work Management
```

## Layer 0: Constitution and Governance

Owns the rules of the system.

Capabilities:

- Engineering Constitution
- RFC process
- Arbiter and Final Judge rules
- decision lifecycle
- human approval model
- safety model
- agent contract
- agent hierarchy
- external review triage

Primary artifacts:

- docs/ENGINEERING_CONSTITUTION.md
- docs/CONSTITUTION_AMENDMENTS.md
- docs/RFC_PROCESS.md
- docs/ARBITER_FINAL_JUDGE.md
- docs/DECISION_LIFECYCLE.md
- docs/AGENT_HIERARCHY_AND_COMMUNICATION.md
- docs/EXTERNAL_REVIEW_TRIAGE_2026_07_04.md
- agents/UNIVERSAL_AGENT_CONTRACT.md

## Layer 1: Knowledge and Memory

Owns durable knowledge.

Capabilities:

- Engineering Memory
- Knowledge Graph
- Knowledge Distillation Engine (repository **content extraction** — proposed RFC-0008: read a scanned repo's actual README/source, distill provenance-tagged knowledge into `wiki/repositories/` + a re-syncable `KnowledgePage`; motivated by the `free-llm-api-resources` reality test where a structural fingerprint yielded an abstention. Queued behind Phase B; not built.)
- Obsidian integration
- Graphify-style ingestion
- documentation lifecycle
- repository knowledge standard
- knowledge packs
- Knowledge read path (AOS-KNOW-002: vault lessons synced to `KnowledgePage`, a DB read projection with a global read API; open lessons surface in the digest)
- Knowledge dashboard (AOS-KNOW-003: the global Control Tower Knowledge view — Sync-from-vault, lesson list with open-lesson emphasis, All/Open filter; compose `./knowledge:ro` vault mount so in-container sync works)
- Decision ADR projection (AOS-COUNCIL-PHASEC2A: approved decisions export to an ADR under `knowledge/wiki/decisions/` and project as re-syncable `KnowledgePage` `page_type="decision"`; `sync_knowledge` re-derives decision pages from the vault so a DB reset loses nothing)

Primary artifacts:

- docs/ENGINEERING_MEMORY.md
- docs/KNOWLEDGE_GRAPH.md
- docs/KNOWLEDGE_DISTILLATION_ENGINE.md
- docs/rfc/RFC-0008-Knowledge-Distillation-Engine-Repository-Content-Extraction.md (proposed — content-extraction MVP + the "tools upstream, not in judges" decision; LES-021 prerequisite)
- docs/KARPATHY_OBSIDIAN_REVIEW.md
- docs/OBSIDIAN_GRAPHIFY_INTEGRATION.md
- docs/DOCUMENTATION_LIFECYCLE_ENGINE.md
- docs/REPOSITORY_KNOWLEDGE_STANDARD.md
- packages/aos_core/aos_core/services/knowledge.py (parse_lessons_index + sync_knowledge; vault → KnowledgePage upsert, repo stays source of truth)
- apps/api/app/routes/knowledge.py (POST /knowledge/sync, GET /knowledge/pages, GET /knowledge/pages/{id})
- apps/web/src/main.tsx (global "Knowledge" Control Tower section: sync + lesson list + open badge + All/Open filter) with apps/web/e2e/knowledge.spec.ts; docker-compose.yml api service `${HOST_KNOWLEDGE_ROOT:-./knowledge}:/knowledge:ro` mount + `KNOWLEDGE_ROOT`

## Layer 2: Research and Evidence

Owns fact gathering and source quality.

Capabilities:

- Research Engine
- Continuous Research Engine
- Research Librarian
- Repository Intelligence Engine
- source ranking
- research notes
- research freshness

Primary artifacts:

- docs/RESEARCH_ENGINE.md
- docs/REPOSITORY_INTELLIGENCE_ENGINE.md
- docs/CONTINUOUS_RESEARCH_ENGINE.md
- docs/REPOSITORY_SCANNER.md
- templates/research_note.md
- agents/research_librarian/CLAUDE.md

## Layer 3: Architecture and Modeling

Owns system structure.

Capabilities:

- Architecture Studio
- Architecture Spine Graph (AOS-ARCH-SEMANTICS-001: beyond directory `contains` edges, the scanner now parses detected Docker Compose files into `service` nodes and `depends_on` edges — both the list form `depends_on: [db, redis]` and the map form `depends_on: {db: {condition: ...}}` — persisted through the generic node/edge path and surfaced in `RepositoryDNA.runtime_services`; parsing is tolerant, so a missing/malformed/non-mapping compose adds a note and never raises. LES-014 compose/service half; manifest/dependency + import-graph edges remain)
- Engineering Digital Twin
- Portfolio Architecture
- repository maps
- trust boundaries
- data flow
- Engineering OS strategy
- Source-classified language weighting (AOS-ARCH-SEMANTICS-001: the scan summary derives a `primary_language` from the top **source**-classified language via `LANGUAGE_CLASS` (source/config/markup/data/docs) and ranks `primary_language_hints` source-first, so config/docs-heavy repos are no longer misreported as YAML/Markdown-primary; raw `language_mix` counts retained — LES-013)

Primary artifacts:

- docs/ARCHITECTURE_STUDIO.md
- docs/ENGINEERING_DIGITAL_TWIN.md
- docs/PORTFOLIO_ARCHITECTURE.md
- docs/ENGINEERING_OS_STRATEGY.md
- docs/REPOSITORY_SCANNER.md (compose-derived `service`/`depends_on` edges + source-classified language weighting — AOS-ARCH-SEMANTICS-001)
- agents/architecture_cartographer/CLAUDE.md
- packages/aos_core/aos_core/repository_scanner.py (compose parse → service/depends_on edges; `LANGUAGE_CLASS` → `primary_language`/`language_classes`)

## Layer 4: Decision and Recommendation

Owns engineering choices.

Capabilities:

- Decision Intelligence
- Recommendation Intelligence
- Technology Fitness Engine
- Strategy Engine
- Portfolio Knowledge Marketplace
- Knowledge Transfer Engine
- Agent Council (backend seed: four MVP agents produce structured, persisted, evidence-bearing outputs; validated on real external code — first live run over pydantic-ai correctly abstained)
- Final Judge synthesis (deterministic, rule-based verdict + abstention over agent outputs)
- Decision loop (AOS-COUNCIL-PHASEC: a `CouncilReview` drafts a governed `Decision` linked back to the review as evidence; a named human approves/rejects it with an `ApprovalRecord` audit trail; an abstained-review draft is `needs_evidence` and cannot be approved until re-drafted — LES-019 operationalized; pending drafts surface in the digest)
- Decision → Knowledge ADR export (AOS-COUNCIL-PHASEC2A: an approved `Decision` renders into a repo-vault ADR under `knowledge/wiki/decisions/` and projects as a re-syncable `KnowledgePage`; a separate explicit approved-only step — local-first write, `409` (not `500`) on a `:ro` vault, never mutating approval state; `POST /decisions/{decision_id}/adr`)
- LLM provider abstraction (swappable reasoning backend; deterministic default + Claude Code subscription backend; parse seam hardened for live-model Markdown-fenced JSON — LES-018)

Primary artifacts:

- docs/TECHNOLOGY_FITNESS_ENGINE.md
- docs/STRATEGY_ENGINE.md
- docs/KNOWLEDGE_TRANSFER_ENGINE.md
- docs/PORTFOLIO_KNOWLEDGE_MARKETPLACE.md
- templates/decision_card.md
- templates/recommendation_card.md
- templates/adr.md
- docs/rfc/RFC-0005-Intelligence-Layer-Agent-Council-Final-Judge.md
- docs/COUNCIL_REALRUN_PYDANTIC_AI.md (first real Council run — reality test + honest gaps)
- docs/LLM_PROVIDER_ABSTRACTION.md
- docs/ARBITER_FINAL_JUDGE.md (verdict set + abstention rule the Final Judge encodes)
- packages/aos_core/aos_core/llm/ (Provider protocol + DeterministicProvider + ClaudeCodeProvider)
- packages/aos_core/aos_core/services/council.py (run_council + synthesize_verdict; the four agent personas)
- packages/aos_core/aos_core/services/decisions.py (Council → Decision loop: draft_decision_from_review + approve_decision + reject_decision; abstention blocks approval — LES-019)
- packages/aos_core/aos_core/services/adr.py (render_adr_markdown + export_decision_adr; approved decision → repo-vault ADR + re-syncable KnowledgePage — AOS-COUNCIL-PHASEC2A)
- docs/DECISION_LIFECYCLE.md (Decision stage — implemented: draft → approve/reject with ApprovalRecord memory; approved → repo-vault ADR export)

## Layer 5: Design and User Experience

Owns product visual language and workflow usability.

Capabilities:

- Design Intelligence
- Dashboard Interface
- Workspace Layout Engine
- Visual Engineering Intelligence
- Voice Command Center

Primary artifacts:

- docs/DESIGN_INTELLIGENCE.md
- docs/DASHBOARD_INTERFACE.md
- docs/WORKSPACE_LAYOUT_ENGINE.md
- docs/VISUAL_ENGINEERING_INTELLIGENCE.md
- docs/VOICE_COMMAND_CENTER.md

## Layer 6: Build and Execution

Owns implementation handoff and execution.

Capabilities:

- Build Intelligence
- Claude Code Bridge
- local LLM routing
- node agents
- proof labs
- builder workflows

Primary artifacts:

- docs/CLAUDE_CODE_BRIDGE.md
- docs/DISTRIBUTED_RUNTIME.md
- docs/LOCAL_LLM_GPU_NODE.md

## Layer 7: Validation and Release Gates

Owns correctness, readiness, and verification.

Capabilities:

- Verification Protocol
- Verification Engine
- Verification Provider abstraction
- Local CLI verification provider
- GitHub Actions verification provider
- Docker verification provider
- Runtime Health verification provider
- Connector Inspection verification provider
- Human Approval verification provider
- PR Guardian
- CI enforcement
- branch protection setup
- branch freshness validation
- WSL local Level 2 verification
- post-merge validation
- Engineering Evaluation Standard
- Engineering Evolution Score
- benchmarks
- experiments
- risk register
- release readiness
- alpha self-evaluation review (system evaluates its own repository)
- Level 4 dashboard browser-drive verification

Primary artifacts:

- docs/ALPHA_REVIEW_V0_1.md
- .archetype/alpha/ (captured self-evaluation evidence)
- scripts/web_drive/ (headless-Chromium dashboard drives — seed corpus)
- apps/web/e2e/ (enforced Playwright e2e suite; CI web-e2e job)
- .archetype/guardian/accepted_warnings.json
- docs/VERIFICATION_PROTOCOL.md
- docs/PR_GUARDIAN.md
- docs/BRANCH_PROTECTION.md
- docs/POST_MERGE_VALIDATION.md
- docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md
- docs/WSL_WIN11_RUNTIME_TARGET.md
- scripts/pre_pr_guardian.sh
- scripts/post_merge_validation.sh
- .github/workflows/ci.yml
- docs/ENGINEERING_EVOLUTION_SCORE.md
- templates/benchmark_record.md
- templates/experiment_record.md
- templates/risk_register.csv

## Layer 8: Self Learning and Evolution

Owns continuous improvement.

Capabilities:

- Nightly Self Learning Loop
- Learning Feedback Loop (lessons registry; RFC-0004)
- Evolution Intelligence
- Meta Agent
- Prompt and Workflow Evolution
- Engineering Simulation Lab

Primary artifacts:

- docs/rfc/RFC-0004-Learning-Feedback-Loop.md
- knowledge/wiki/lessons/index.md
- docs/NIGHTLY_SELF_LEARNING_LOOP.md
- docs/EVOLUTION_INTELLIGENCE.md
- docs/META_AGENT.md
- docs/PROMPT_WORKFLOW_EVOLUTION.md
- docs/ENGINEERING_SIMULATION_LAB.md

## Layer 9: Portfolio and Organizational Intelligence

Owns cross-repository learning.

Capabilities:

- Organizational Intelligence Engine
- Portfolio Architecture
- Knowledge Transfer Engine
- Portfolio Knowledge Marketplace
- Repository DNA
- Repository Intelligence outputs
- Knowledge Distillation outputs
- cross-repository recommendations
- Repository acquisition (`clone_repo` / `scripts/onboard_repo.sh` — the acquire step for the portfolio; AOS-21)
- Portfolio reality test (first external repo scanned end to end — pydantic-ai; AOS-21)

Primary artifacts:

- docs/ORGANIZATIONAL_INTELLIGENCE_ENGINE.md
- docs/PORTFOLIO_ARCHITECTURE.md
- docs/KNOWLEDGE_TRANSFER_ENGINE.md
- docs/PORTFOLIO_KNOWLEDGE_MARKETPLACE.md
- docs/REPOSITORY_INTELLIGENCE_ENGINE.md
- docs/KNOWLEDGE_DISTILLATION_ENGINE.md
- docs/PORTFOLIO_PYDANTIC_AI.md (AOS-21 reality test + honest findings LES-013/LES-014)
- packages/aos_core/aos_core/services/onboarding.py; scripts/onboard_repo.sh
- templates/repository_dna.md

## Layer 10: Interface and Interaction

Owns how users interact with ArchetypeOS.

Capabilities:

- Dashboard
- Command palette
- Voice interface
- agent council dashboard
- engineering observatory
- multi-monitor layouts

Primary artifacts:

- docs/DASHBOARD_INTERFACE.md
- docs/VOICE_PROVIDER_ADAPTERS.md
- docs/VOICE_SAFETY_MODEL.md
- docs/AGENT_COUNCIL_DASHBOARD.md
- docs/ENGINEERING_OBSERVATORY.md

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

## Layer 12: Orchestration and Work Management

Owns cross-agent coordination, durable project state, task sequencing, handoffs, and anti-context-rot workflows.

Capabilities:

- Orchestration Engine
- agent hierarchy
- agent communication protocol
- current state tracking
- active work tracking
- handoff protocol
- verification handoff metadata
- branch isolation protocol
- worktree protocol
- connector fallback branch isolation
- backup head preservation
- branch freshness before ready-for-review
- recent changes log
- session bootstrap generation
- Plane integration
- task lifecycle enforcement
- dependency and blocker tracking

Primary artifacts:

- docs/ORCHESTRATION_ENGINE.md
- docs/ORCHESTRATOR_PLAYBOOK.md
- docs/AGENT_HIERARCHY_AND_COMMUNICATION.md
- docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md
- docs/CURRENT_STATE.md
- docs/ACTIVE_WORK.md
- docs/HANDOFF.md
- docs/RECENT_CHANGES.md
- docs/SESSION_BOOTSTRAP.md

## Capability Dependency Graph

```text
Constitution
  -> RFC Process
  -> Agent Contract
  -> Arbiter and Final Judge
  -> Decision Lifecycle
  -> Agent Hierarchy

Engineering OS Strategy
  -> WSL Runtime Target
  -> Runtime Verification
  -> Repository Scanner Loop
  -> Engineering Control Tower

Orchestration
  -> Current State
  -> Active Work
  -> Session Bootstrap
  -> Agent Assignment
  -> Handoff
  -> Branch Isolation
  -> Worktree Protocol
  -> Connector Fallback
  -> Verification Metadata
  -> Plane Sync
  -> PR Lifecycle

Knowledge and Memory
  -> Knowledge Distillation
  -> Research
  -> Architecture
  -> Decision Intelligence
  -> Portfolio Intelligence

Research
  -> Repository Intelligence
  -> Technology Fitness
  -> Design Intelligence
  -> Strategy Engine

Repository Intelligence
  -> Architecture Reverse Engineering
  -> Pattern Mining
  -> Reuse Analysis
  -> Portfolio Knowledge

Architecture
  -> Digital Twin
  -> PR Guardian
  -> Verification Protocol
  -> Release Gates

Decision Intelligence
  -> Build Intelligence
  -> Verification
  -> Validation
  -> Evolution

Verification
  -> Local CLI Provider
  -> GitHub Actions Provider
  -> Docker Provider
  -> Runtime Health Provider
  -> Connector Inspection Provider
  -> Human Approval Provider
  -> Branch Freshness Validation
  -> PR Guardian
  -> Release Gates

Nightly Self Learning
  -> Knowledge Distillation
  -> Meta Agent
  -> Prompt Evolution
  -> Skill Recommendations
  -> Portfolio Knowledge
```

## MVP Path

The first build should not implement every capability.

Minimum coherent product:

1. Project registry
2. WSL Windows 11 runtime target
3. Local Docker runtime verification
4. Repository scan
5. Architecture Spine Graph draft
6. Decision cards and ADRs
7. Research notes
8. PR Guardian first pass
9. Verification Protocol
10. Branch Isolation / Worktree Protocol
11. Nightly self-learning digest
12. Dashboard shell
13. Voice inbox capture
14. Orchestration state files
15. Session bootstrap and handoff protocol

## Later Capabilities

- full marketplace
- full simulation lab
- full strategy engine
- advanced multi-monitor support
- production-grade voice session streaming
- advanced digital twin prediction
- write-capable build workflows after approval gates mature
- live multi-agent communication bus
- full Plane synchronization
- automatic Verification Engine provider selection

## Update Rule

Whenever a new capability, engine, agent, or runtime component is added, this capability map must be updated in the same change set or explicitly marked as not affected.

## Principle

ArchetypeOS should grow from a concrete path, not from scattered features.