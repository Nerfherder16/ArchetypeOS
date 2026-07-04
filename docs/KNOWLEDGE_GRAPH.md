# Knowledge Graph

## Purpose

The Knowledge Graph stores relationships between projects, repositories, technologies, decisions, research, agents, risks, experiments, benchmarks, and lessons learned.

## Core Entities

- Portfolio
- Repository
- Project
- Technology
- Agent
- Engine
- Decision
- ADR
- Research note
- Risk
- Benchmark
- Experiment
- Lesson learned
- Architecture node
- Source file
- External repo
- MCP
- Skill
- Knowledge pack

## Relationship Examples

```text
Repository -> uses -> Technology
Decision -> selected -> Technology
Research -> supports -> Decision
Experiment -> rejected -> Alternative
Risk -> affects -> ArchitectureNode
Repository -> can_reuse -> KnowledgePack
Agent -> produced -> Recommendation
```

## Storage

Early versions may use Postgres plus JSON graph files.

Later versions may add a graph database or graph-native index.

## Obsidian And Graphify

Obsidian can mirror human-readable notes. Graphify-style adapters can enrich the graph from code, docs, images, and diagrams.

## Principle

The graph allows ArchetypeOS to reason over relationships instead of isolated files.
