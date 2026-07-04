# Agent Communication Bus

## Purpose

The Agent Communication Bus is the governed message and event layer for ArchetypeOS agents.

It prevents agents from coordinating through private memory, invisible assumptions, or untracked chat conclusions.

## Core Principle

Agents do not merely chat. Agents exchange typed engineering artifacts.

## Why This Exists

During early ArchetypeOS development, manual coordination revealed a repeatable pattern:

```text
Builder Agent opens PR
-> CI / DevOps Agent verifies PR
-> Builder Agent patches failures
-> CI / DevOps Agent re-verifies
-> Orchestrator approves merge
-> State files update
-> Next task is assigned
```

That is an event-driven coordination loop. ArchetypeOS should treat it as a first-class system.

## Communication Model

Agents communicate through durable, typed artifacts:

- WorkPackage
- TaskAssignment
- VerificationRequest
- VerificationReport
- PatchRequest
- PatchCompletion
- ResearchRequest
- ResearchDossier
- DecisionRequest
- DecisionVerdict
- RiskEscalation
- HandoffRecord
- StateUpdate
- MergeRecommendation
- SkillInvocation

## Message Requirements

Every bus message should include:

- id
- type
- version
- project_id
- task_id
- source_agent
- target_agent or broadcast_scope
- authority_level
- status
- created_at
- updated_at
- related_pr
- related_branch
- related_docs
- payload
- evidence
- limitations

## Initial Durable Channels

Before the runtime bus exists, the durable channels are:

- GitHub issues
- PR comments
- PR reviews
- state files
- handoff files
- RFCs
- ADRs
- verification reports
- work packages

## Runtime Bus Later

Later, ArchetypeOS may implement the bus through:

- Postgres tables
- Redis streams
- worker jobs
- WebSocket notifications
- dashboard inboxes
- Plane synchronization

## Event Examples

```text
PRCreated
VerificationRequested
VerificationFailed
PatchRequested
PatchApplied
VerificationPassed
MergeRecommended
MergeApproved
StateUpdated
NextTaskGenerated
```

## Authority

Messages may request action, but authority rules still apply.

A bus event must not bypass:

- Authority and Approval Engine
- PR Guardian
- Verification Protocol
- Final Judge
- Human Owner approval

## Conflict Handling

If two agents produce conflicting artifacts, the bus should preserve both and escalate to Final Judge.

## Principle

Reliable agent communication is not free-form conversation. It is typed, durable, auditable coordination.