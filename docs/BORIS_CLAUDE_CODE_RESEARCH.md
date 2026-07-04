# Claude Code Workflow Research

## Purpose

This document extracts reusable workflow principles from the public How Boris Uses Claude Code reference.

Source: https://howborisusesclaudecode.com/

## Useful Patterns

### Parallel Work

The reference describes running multiple Claude Code sessions in separate checkouts or worktrees.

ArchetypeOS adoption:

- one work package maps to one branch
- one local task maps to one isolated worktree
- connector sessions use one branch as the logical worktree

### Plan Before Build

Complex work should start with planning and review before edits begin.

ArchetypeOS adoption:

- work package created first
- acceptance criteria defined before assignment
- Orchestrator or Final Judge may review the plan before implementation

### Shared Agent Memory

Repeated mistakes should improve durable agent instructions and skills.

ArchetypeOS adoption:

- repeated errors become skills, rules, or docs
- state files and knowledge vault preserve lessons
- PR reviews can generate knowledge updates

### Skills And Commands

Repeated workflows should become reusable skills or commands.

ArchetypeOS adoption:

- PR Monitoring skill
- future state reconciliation skill
- future research dossier skill
- future repository scanner skill

### Verification Loop

The strongest pattern is giving the agent a way to verify its own work.

ArchetypeOS adoption:

- Verification Protocol is mandatory
- CI / DevOps owns independent PR monitoring
- local, CI, runtime, connector, and human verification are separate paths

## Caution

Claude Code patterns should be generalized into model-agnostic ArchetypeOS engines.

Do not hard-code the platform around one model, one CLI, or one vendor.

## Final Judgment

The most important transferable idea is the loop:

plan -> build -> verify -> learn -> update memory -> repeat.