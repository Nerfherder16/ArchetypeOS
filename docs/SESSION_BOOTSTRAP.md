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
8. `docs/VERIFICATION_PROTOCOL.md`
9. domain-specific docs for the assigned task

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
- docs/VERIFICATION_PROTOCOL.md
- relevant domain docs

Treat GitHub as the source of truth.
Do not rely on prior conversation memory.
Do not expand scope without RFC.
Do not change architecture silently.
Do not bypass PR Guardian or CI.
Do not claim completion without verification metadata.

Assigned task:
[PASTE TASK]

Acceptance criteria:
[PASTE ACCEPTANCE CRITERIA]

Required deliverables:
- implementation or documentation changes
- tests where applicable
- docs updates where applicable
- handoff update
- verification metadata
- PR

Work cycle:
inspect -> plan -> patch -> verify -> update docs/state -> PR.

Allowed verification states:
- Verified
- Verified with warnings
- Verification pending
- Verification unavailable
- Verification blocked
```

## Verification Startup Rule

Every agent must decide how the assigned work will be verified before implementation begins.

Use this decision order:

```text
Local execution available?
  -> run Level 2 checks.
Else GitHub CI available?
  -> use Level 3 checks and record pending status until visible.
Else repository inspection available?
  -> use Level 1 checks and record limitations.
Else human judgment required?
  -> request Level 5 verification.
Else
  -> mark Verification unavailable or Verification blocked.
```

Every final handoff and PR body must include:

```text
Verification Status:
Verification Level:
Verification Method:
Evidence:
Limitations:
Required Next Verifier:
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

Focus on GitHub Actions, PR Guardian, branch protection, Docker validation, release gates, and verification providers.

### Research Council

Focus on evidence and alternatives. Do not implement code.

## End-Of-Session Requirement

Every session must update or propose updates to:

- `docs/HANDOFF.md`
- `docs/CURRENT_STATE.md` if state changed
- `docs/ACTIVE_WORK.md` if task status changed
- `docs/RECENT_CHANGES.md` if meaningful work merged or proposed

Every session must also record verification metadata using only the allowed verification states from `docs/VERIFICATION_PROTOCOL.md`.

## Principle

A new session should be able to recover the project in minutes from repository state alone, including how the last work was verified or why verification remains pending.
