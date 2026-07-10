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

## Layers

Each layer's capabilities and artifacts live in its own file (split for token-frugal reads + conflict isolation — LES-L07):

- [Layer 0: Constitution and Governance](capability-map/layer-00.md)
- [Layer 1: Knowledge and Memory](capability-map/layer-01.md)
- [Layer 2: Research and Evidence](capability-map/layer-02.md)
- [Layer 3: Architecture and Modeling](capability-map/layer-03.md)
- [Layer 4: Decision and Recommendation](capability-map/layer-04.md)
- [Layer 5: Design and User Experience](capability-map/layer-05.md)
- [Layer 6: Build and Execution](capability-map/layer-06.md)
- [Layer 7: Validation and Release Gates](capability-map/layer-07.md)
- [Layer 8: Self Learning and Evolution](capability-map/layer-08.md)
- [Layer 9: Portfolio and Organizational Intelligence](capability-map/layer-09.md)
- [Layer 10: Interface and Interaction](capability-map/layer-10.md)
- [Layer 11: Runtime and Infrastructure](capability-map/layer-11.md)
- [Layer 12: Orchestration and Work Management](capability-map/layer-12.md)

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

Whenever a new capability, engine, agent, or runtime component is added, the capability map must be updated in the same change set or explicitly marked as not affected. Record it in the relevant layer file under [`capability-map/`](capability-map/) (e.g. `capability-map/layer-08.md`); editing the layer file satisfies PR Guardian's capability-map check. Add a new layer only by also linking it from the Layers list above.

## Principle

ArchetypeOS should grow from a concrete path, not from scattered features.