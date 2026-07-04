# Decision Lifecycle

## Purpose

Engineering decisions are hypotheses until validated by evidence.

ArchetypeOS should track decisions through their full lifecycle rather than treating decisions as one-time documents.

## Lifecycle

```text
Idea -> Research -> Simulation -> Decision -> Implementation -> Validation -> Measurement -> Knowledge -> Reuse -> Evolution
```

## Stages

### Idea

A proposed direction, feature, technology, pattern, or architecture change.

### Research

Evidence gathering from official docs, reference implementations, benchmarks, internal history, and external sources.

### Simulation

Optional proof lab, benchmark, migration simulation, or what-if analysis.

### Decision

A recorded ADR or decision card with alternatives, tradeoffs, evidence, and acceptance criteria.

### Implementation

The decision is applied through controlled builder workflows.

### Validation

Tests, benchmarks, PR Guardian, user review, security review, and production feedback validate the decision.

### Measurement

ArchetypeOS compares expected outcomes against actual outcomes.

### Knowledge

Results become lessons learned, research updates, benchmark records, or reusable patterns.

### Reuse

Validated knowledge becomes available to other repositories through the Portfolio Knowledge Marketplace.

### Evolution

The decision is periodically re-evaluated against new evidence.

## Principle

A decision is not complete when it is accepted. It is complete when its outcome is measured and its learning is captured.
