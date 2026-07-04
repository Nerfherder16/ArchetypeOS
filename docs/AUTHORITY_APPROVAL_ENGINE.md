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

### Level 1: Draft Creation

Allowed with normal user intent:

- create draft notes
- create draft decisions
- create draft recommendations
- create draft issues
- create draft reports

### Level 2: Internal Writes

Requires approval:

- write knowledge artifacts
- update docs
- update local metadata
- update repository knowledge vault

### Level 3: Repository Modification

Requires explicit approval:

- modify source files
- apply patches
- install dependencies
- run formatters that change files

### Level 4: Source Control Actions

Requires explicit approval:

- commit
- push
- open PR
- update PR
- tag release

### Level 5: High-Impact Actions

Requires explicit approval and elevated confirmation:

- delete data
- modify infrastructure
- change secrets
- change authentication
- send external communications
- spend money through APIs
- affect production systems

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

The audit trail must be queryable by project, agent, tool, capability, action level, and time.

## Emergency Stop

The runtime should provide an emergency stop that cancels active jobs and revokes temporary grants.

## Principle

ArchetypeOS should become more capable only as its authority model becomes more trustworthy.
