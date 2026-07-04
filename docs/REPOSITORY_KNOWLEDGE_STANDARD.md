# Repository Knowledge Standard

## Purpose

Every repository created or managed by ArchetypeOS should contain an explicit knowledge structure.

The repository is not only source code. It is an evolving engineering knowledge system.

## Required Structure

```text
.archetype/
docs/
architecture/
research/
knowledge/
decisions/
benchmarks/
experiments/
lessons_learned/
risks/
agents/
```

## Directory Responsibilities

### .archetype

Machine-readable project context, agent rules, engine settings, scorecards, and metadata.

### docs

Human-readable documentation.

### architecture

Architecture graphs, diagrams, topology, trust boundaries, and data flow.

### research

Research notes, source evaluations, comparison studies, and evidence records.

### knowledge

Reusable knowledge extracted from the project.

### decisions

Decision cards and ADRs.

### benchmarks

Performance, cost, reliability, and quality benchmarks.

### experiments

Successful and failed experiments with results and lessons.

### lessons_learned

Post-implementation learning, mistakes, and future guidance.

### risks

Risk register, mitigations, and release gate blockers.

### agents

Project-specific agent instructions and verification rules.

## Completion Rule

A feature is not complete until related documentation, architecture, decisions, risks, and lessons are updated when applicable.
