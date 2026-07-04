# Authority And Approval Engine

## Purpose

The Authority and Approval Engine governs what ArchetypeOS agents, workflows, voice commands, desktop automation, browser automation, Claude Code sessions, local LLM nodes, and sidecars are allowed to do.

This is inspired by the JARVIS authority-gating pattern but adapted for ArchetypeOS engineering workflows.

## Core Principle

Powerful actions require explicit authority, auditability, and human approval.

## Action Levels

### Level 0: Read Only

Allowed by default:

- inspect files
- search repositories
- read docs
- summarize code
- generate reports
- analyze diffs
- produce recommendations
- inspect verification evidence

### Level 1: Draft Creation

Allowed with normal user intent:

- create draft notes
- create draft decisions
- create draft recommendations
- create draft issues
- create draft reports
- create draft verification reports

### Level 2: Internal Writes

Requires approval:

- write knowledge artifacts
- update docs
- update local metadata
- update repository knowledge vault
- update verification metadata

### Level 3: Repository Modification

Requires explicit approval:

- modify source files
- apply patches
- install dependencies
- run formatters that change files
- run local verification commands that may create or mutate runtime artifacts

### Level 4: Source Control Actions

Requires explicit approval:

- commit
- push
- open PR
- update PR
- tag release
- update PR verification status

### Level 5: High-Impact Actions

Requires explicit approval and elevated confirmation:

- delete data
- modify infrastructure
- change secrets
- change authentication
- send external communications
- spend money through APIs
- affect production systems
- approve high-impact verification exceptions

## Authority Artifacts

Every governed action should record:

- actor
- agent
- tool
- action level
- requested capability
- target path or system
- reason
- approval status
- timestamp
- output
- rollback notes
- verification status when applicable

## Verification Authority

Verification providers must obey the same authority model as every other agent capability.

Default authority levels:

- Connector inspection verification: Level 0 read-only.
- Documentation-only verification report creation: Level 1 draft creation.
- Repository documentation updates that record verification metadata: Level 2 internal write.
- Local CLI, Docker, formatter, test, and build execution: Level 3 repository modification when commands can create files, mutate caches, or affect runtime state.
- Commit, push, PR creation, and PR verification metadata updates: Level 4 source control action.
- Production runtime checks, infrastructure changes, destructive testing, and high-impact exception approvals: Level 5 high-impact action.

A verifier may not silently escalate authority. If the strongest verifier requires unavailable authority, the agent must record the limitation and choose the next permitted verifier from `docs/VERIFICATION_PROTOCOL.md`.

## Temporary Grants

Temporary grants may allow specific tools or paths for a limited time.

Grant fields:

- scope
- capability
- path or target
- expiration
- approver
- reason

## Voice And Driving Mode

Voice mode defaults to capture-only.

Driving mode may create notes and drafts but must not perform repository, infrastructure, or external actions.

## Desktop And Browser Automation

Desktop and browser automation require strict authority gates because they can act outside the repository.

Default state:

- screenshot: approval or trusted local mode
- keyboard: approval required
- mouse: approval required
- browser navigation: approval required
- form submission: elevated approval required
- credential entry: prohibited unless explicitly delegated

## Audit Trail

Every approval and execution should be logged.

The audit trail must be queryable by project, agent, tool, capability, action level, verification status, and time.

## Emergency Stop

The runtime should provide an emergency stop that cancels active jobs and revokes temporary grants.

## Principle

ArchetypeOS should become more capable only as its authority model becomes more trustworthy.
