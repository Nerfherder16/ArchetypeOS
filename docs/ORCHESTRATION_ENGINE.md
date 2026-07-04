# Orchestration Engine

## Purpose

The Orchestration Engine coordinates work across agents, conversations, branches, pull requests, research tasks, decisions, and implementation streams.

It exists to prevent context rot, duplicated work, scope drift, and agent collisions.

## Core Principle

Conversations are temporary execution contexts. The repository is the durable source of truth.

## Mission

ArchetypeOS should manage a team of specialized AI agents the way a strong technical lead manages an engineering organization:

- define work clearly
- assign work to the right agent
- enforce hierarchy
- track dependencies
- require evidence
- collect outputs
- resolve conflicts
- update project state
- generate the next task

## Hierarchy

```text
Human Owner
  -> Chief Architect / Orchestrator
      -> Final Judge
      -> PMO Agent
      -> Runtime Agent
      -> Frontend Agent
      -> Knowledge Agent
      -> Repository Intelligence Agent
      -> CI / DevOps Agent
      -> Research Council
```

## Agent Communication Rule

Agents may communicate with each other through governed artifacts, not untracked side conversations.

Approved communication channels:

- GitHub issues
- pull requests
- review comments
- RFCs
- ADRs
- decision cards
- current state files
- task handoff files
- knowledge vault entries
- orchestration events

Unapproved communication:

- invisible assumptions
- private memory only
- unstored chat conclusions
- untracked cross-agent instructions

## Responsibilities

- Maintain current project state
- Maintain active work queue
- Generate session bootstrap briefs
- Assign tasks to agents
- Enforce capability boundaries
- Track dependencies and blockers
- Track PR lifecycle
- Detect stale work
- Detect conflicting work
- Require handoff updates
- Update roadmap and state after merges
- Escalate disagreements to Final Judge

## Agent Authority Boundaries

Each agent has a charter.

Agents may:

- execute assigned tasks
- inspect relevant repository files
- propose RFCs
- create implementation plans
- open PRs within scope
- update required state artifacts

Agents may not:

- silently change architecture
- expand scope without RFC
- override another agent's domain
- merge their own work without review
- bypass PR Guardian
- bypass approval gates

## Task Lifecycle

```text
Idea
-> Research
-> RFC or Decision
-> Accepted
-> Task Created
-> Agent Assigned
-> Implementation
-> CI
-> PR
-> Review
-> Merge
-> Knowledge Updated
-> Current State Updated
-> Next Task Generated
```

## Required State Artifacts

The Orchestration Engine maintains:

- `docs/CURRENT_STATE.md`
- `docs/ACTIVE_WORK.md`
- `docs/HANDOFF.md`
- `docs/RECENT_CHANGES.md`
- `docs/SESSION_BOOTSTRAP.md`

These files are required even after ArchetypeOS has a database and dashboard.

Reason: markdown state files make recovery possible if the database, Plane instance, dashboard, or local server is unavailable.

## Plane Integration

Plane should remain the issue and sprint tracker when available.

ArchetypeOS adds engineering intelligence on top of Plane:

- RFC linkage
- decision linkage
- architecture impact
- repository intelligence reports
- knowledge distillation
- agent assignments
- acceptance criteria generation
- PR Guardian output
- session bootstrap generation

If Plane is unavailable, the markdown state files remain the fallback execution board.

## Conflict Resolution

When agents disagree:

1. Preserve both positions.
2. Require evidence from each agent.
3. Surface tradeoffs.
4. Escalate to Final Judge.
5. Record the verdict in the relevant decision artifact.

## Context Rot Defense

No conversation is allowed to be the only place where project state exists.

At the end of a task, the owning agent must update durable state artifacts before the task is considered complete.

## Acceptance Criteria

- New sessions can restart from repository state alone.
- Agents know their hierarchy and authority.
- Active work is visible.
- Blockers are visible.
- Recent changes are visible.
- Handoffs are explicit.
- The next recommended task is clear.

## Principle

ArchetypeOS should make engineering coordination durable, inspectable, and recoverable.