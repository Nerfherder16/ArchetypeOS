# Documentation Lifecycle Engine

## Purpose

The Documentation Lifecycle Engine makes documentation measurable, reviewable, and current.

Documentation is not a static artifact. It has state, age, ownership, confidence, and evidence.

## Lifecycle States

```text
Draft
Validated
Production
Deprecated
Archived
```

## Required Metadata

Each major document should track:

- owner
- status
- last verified date
- confidence level
- evidence sources
- related code
- related decisions
- related risks
- freshness score

## Freshness Signals

A document may become stale when:

- related code changes
- related architecture changes
- dependencies change
- compliance requirements change
- external documentation changes
- an ADR supersedes it
- a release modifies the behavior it describes

## Scores

Repositories should track:

- Documentation Coverage
- Documentation Freshness
- Decision Coverage
- ADR Coverage
- Architecture Coverage
- Research Freshness
- API Documentation Coverage
- Test Documentation Coverage

## Release Gate

Documentation freshness should affect release readiness.

A feature that changes system behavior but does not update documentation should trigger a PR Guardian warning or block depending on severity.
