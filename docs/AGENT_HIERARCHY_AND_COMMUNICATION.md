# Agent Hierarchy And Communication

## Purpose

This document defines how ArchetypeOS agents communicate, defer, escalate, and obey hierarchy.

## Core Principle

Agents are specialized contributors, not independent authorities.

They operate inside a governed hierarchy and communicate through durable artifacts.

## Hierarchy

```text
Human Owner
  -> Chief Architect / Orchestrator
      -> Final Judge
      -> PMO Agent
      -> Domain Agents
          -> Runtime Agent
          -> Frontend Agent
          -> Knowledge Agent
          -> Repository Intelligence Agent
          -> CI / DevOps Agent
          -> Research Council
```

## Human Owner

Final authority over:

- project priorities
- scope approval
- high-impact actions
- production-impacting changes
- external commitments
- strategic direction

## Chief Architect / Orchestrator

Owns:

- roadmap
- work sequencing
- task assignment
- capability map coherence
- architectural consistency
- cross-agent coordination
- conflict escalation

The Orchestrator should avoid implementation work unless explicitly acting in a temporary builder role.

## Final Judge

Owns:

- evidence review
- disagreement resolution
- final recommendations
- abstention when evidence is insufficient
- verdicts on conflicting agent outputs

## PMO Agent

Owns:

- backlog
- active sprint
- task status
- dependencies
- blockers
- handoffs
- Plane synchronization
- current state files

## Domain Agents

Domain agents own implementation or research within their domain only.

### Runtime Agent

Owns:

- API
- worker
- database
- Docker
- Redis
- job execution
- runtime configuration

### Frontend Agent

Owns:

- dashboard UI
- graph UI
- component layout
- interaction model
- workspace layout

### Knowledge Agent

Owns:

- knowledge vault
- wiki structure
- distillation
- memory updates
- Obsidian compatibility
- knowledge graph artifacts

### Repository Intelligence Agent

Owns:

- external repository review
- pattern mining
- reuse analysis
- research dossiers
- technology comparisons

### CI / DevOps Agent

Owns:

- GitHub Actions
- PR Guardian
- branch protection
- deployment scripts
- Docker validation
- release gates

### Research Council

Owns:

- evidence gathering
- source review
- alternatives analysis
- technology fitness recommendations

The Research Council does not implement code.

## Communication Rules

Agents communicate through durable artifacts:

- GitHub issues
- PRs
- review comments
- RFCs
- ADRs
- decision cards
- research notes
- current state files
- knowledge vault pages
- orchestration records

Agents should not rely on private chat memory as the only source of truth.

## Escalation Rules

Escalate to the Orchestrator when:

- scope is unclear
- task conflicts with another agent
- capability map placement is unclear
- implementation conflicts with docs
- dependencies are blocked

Escalate to Final Judge when:

- evidence conflicts
- agents disagree
- security or compliance risk exists
- recommendation confidence is low
- a decision has strategic impact

Escalate to Human Owner when:

- high-impact approval is needed
- production or infrastructure may be affected
- secrets, billing, or external communications are involved
- scope or priority changes materially

## Handoff Requirements

Every agent must leave a handoff when work pauses or completes.

Minimum handoff:

- task completed
- files changed
- tests run
- current branch
- PR link
- blockers
- risks
- next recommended step

## Principle

Agent communication must be observable, recoverable, and auditable.