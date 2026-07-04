# Claude Code Bridge

## Purpose

The Claude Code Bridge lets ArchetypeOS communicate with Claude Code sessions running in containers, WSL, developer workstations, or future remote nodes.

## Responsibilities

- route approved build tasks to Claude Code
- provide project context
- provide agent outputs
- enforce read-only mode by default
- collect logs
- collect diffs
- return structured results
- require approval for writes, commits, pushes, and PRs

## Modes

### Read Only

Claude Code may inspect files, summarize code, map architecture, and propose changes.

### Proposed Patch

Claude Code may produce patches or instructions, but not apply them without approval.

### Write Approved

Claude Code may modify files after explicit approval.

### PR Approved

Claude Code may help create commits and PRs after explicit approval.

## Required Context Packet

Each Claude Code task should receive:

- project context
- repository DNA
- relevant docs
- relevant ADRs
- agent outputs
- acceptance criteria
- safety mode
- allowed tools
- forbidden actions

## Output

- summary
- changed files or proposed files
- commands run
- tests run
- risks
- follow-up tasks
- confidence

## Principle

Claude Code is an execution engine. ArchetypeOS owns reasoning, context, approvals, and memory.
