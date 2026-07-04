# Session Bootstrap

## Purpose

This file defines how every new ArchetypeOS engineering conversation should start.

The goal is to make conversations disposable and project state durable.

## Bootstrap Rule

Every new session must reconstruct state from the repository before acting.

Do not rely on prior chat memory as the source of truth.

## Required First Read

Read these files first:

1. `docs/CURRENT_STATE.md`
2. `docs/ACTIVE_WORK.md`
3. `docs/HANDOFF.md`
4. `docs/RECENT_CHANGES.md`
5. `docs/CAPABILITY_MAP.md`
6. `docs/V0_1_SCOPE_LOCK.md`
7. `docs/CONCRETE_BUILD_PATH.md`
8. domain-specific docs for the assigned task

## Session Startup Prompt Template

```text
You are the [AGENT ROLE] for ArchetypeOS.

Repository:
https://github.com/Nerfherder16/ArchetypeOS

Before doing any work, read:
- docs/CURRENT_STATE.md
- docs/ACTIVE_WORK.md
- docs/HANDOFF.md
- docs/RECENT_CHANGES.md
- docs/CAPABILITY_MAP.md
- docs/V0_1_SCOPE_LOCK.md
- docs/CONCRETE_BUILD_PATH.md
- relevant domain docs

Treat GitHub as the source of truth.
Do not rely on prior conversation memory.
Do not expand scope without RFC.
Do not change architecture silently.
Do not bypass PR Guardian or CI.

Assigned task:
[PASTE TASK]

Acceptance criteria:
[PASTE ACCEPTANCE CRITERIA]

Required deliverables:
- implementation or documentation changes
- tests where applicable
- docs updates where applicable
- handoff update
- PR

Work cycle:
inspect -> plan -> patch -> verify -> update docs/state -> PR.
```

## Agent-Specific Notes

### Orchestrator

Focus on sequencing, scope, decisions, coordination, and review.

### Runtime Agent

Focus on API, worker, database, Docker, Redis, and jobs.

### Frontend Agent

Focus on dashboard, UI, workspace, graphs, and interaction.

### Knowledge Agent

Focus on vault, wiki, graph artifacts, distillation, and memory.

### Repository Intelligence Agent

Focus on external repository reviews and pattern extraction.

### CI / DevOps Agent

Focus on GitHub Actions, PR Guardian, branch protection, Docker validation, and release gates.

### Research Council

Focus on evidence and alternatives. Do not implement code.

## End-Of-Session Requirement

Every session must update or propose updates to:

- `docs/HANDOFF.md`
- `docs/CURRENT_STATE.md` if state changed
- `docs/ACTIVE_WORK.md` if task status changed
- `docs/RECENT_CHANGES.md` if meaningful work merged or proposed

## Principle

A new session should be able to recover the project in minutes from repository state alone.