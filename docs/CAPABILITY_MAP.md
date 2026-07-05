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
- Knowledge Distillation Engine
- Obsidian integration
- Graphify-style ingestion
- documentation lifecycle
- repository knowledge standard
- knowledge packs

Primary artifacts:

- docs/ENGINEERING_MEMORY.md
- docs/KNOWLEDGE_GRAPH.md
- docs/KNOWLEDGE_DISTILLATION_ENGINE.md
- docs/KARPATHY_OBSIDIAN_REVIEW.md
- docs/OBSIDIAN_GRAPHIFY_INTEGRATION.md
- docs/DOCUMENTATION_LIFECYCLE_ENGINE.md
- docs/REPOSITORY_KNOWLEDGE_STANDARD.md

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
- Architecture Spine Graph
- Engineering Digital Twin
- Portfolio Architecture
- repository maps
- trust boundaries
- data flow
- Engineering OS strategy

Primary artifacts:

- docs/ARCHITECTURE_STUDIO.md
- docs/ENGINEERING_DIGITAL_TWIN.md
- docs/PORTFOLIO_ARCHITECTURE.md
- docs/ENGINEERING_OS_STRATEGY.md
- agents/architecture_cartographer/CLAUDE.md

## Layer 4: Decision and Recommendation

Owns engineering choices.

Capabilities:

- Decision Intelligence
- Recommendation Intelligence
- Technology Fitness Engine
- Strategy Engine
- Portfolio Knowledge Marketplace
- Knowledge Transfer Engine

Primary artifacts:

- docs/TECHNOLOGY_FITNESS_ENGINE.md
- docs/STRATEGY_ENGINE.md
- docs/KNOWLEDGE_TRANSFER_ENGINE.md
- docs/PORTFOLIO_KNOWLEDGE_MARKETPLACE.md
- templates/decision_card.md
- templates/recommendation_card.md
- templates/adr.md

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

Primary artifacts:

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
- Evolution Intelligence
- Meta Agent
- Prompt and Workflow Evolution
- Engineering Simulation Lab

Primary artifacts:

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

Primary artifacts:

- docs/ORGANIZATIONAL_INTELLIGENCE_ENGINE.md
- docs/PORTFOLIO_ARCHITECTURE.md
- docs/KNOWLEDGE_TRANSFER_ENGINE.md
- docs/PORTFOLIO_KNOWLEDGE_MARKETPLACE.md
- docs/REPOSITORY_INTELLIGENCE_ENGINE.md
- docs/KNOWLEDGE_DISTILLATION_ENGINE.md
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

Primary artifacts:

- docs/WSL_WIN11_RUNTIME_TARGET.md
- docs/DISTRIBUTED_RUNTIME.md
- docs/LOCAL_LLM_GPU_NODE.md
- docs/CLAUDE_CODE_BRIDGE.md
- docker-compose.yml
- .env.example
- apps/web
- apps/api
- apps/worker

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