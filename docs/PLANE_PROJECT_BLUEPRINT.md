# Plane Project Blueprint

## Purpose

This document defines the intended Plane structure for ArchetypeOS.

Plane is currently unavailable because the local instance is offline during a power outage. Until it returns, this document and the markdown state files are the fallback planning system.

## Project

Name: ArchetypeOS

## Epics

1. Foundation Runtime
2. CI / Verification / PR Guardian
3. Orchestration Engine
4. Agent Communication Bus
5. Repository Intelligence
6. Knowledge Vault
7. App Creation Loop
8. Dashboard / Operator Console
9. Plane Integration
10. Local Agent Runtime / Worktrees

## Sprint 2

Name: Operating Loop

Goal: prove that ArchetypeOS can manage work, agents, branches, verification, PRs, state, and the WSL runtime target before broader product expansion.

## Suggested Issues

### AOS-PMO-001 — Reconcile State Files

Acceptance criteria:

- CURRENT_STATE reflects latest merged PRs
- ACTIVE_WORK reflects true task statuses
- HANDOFF has current next step
- RECENT_CHANGES is updated

### AOS-RESEARCH-001 — Claude Code Workflow Research

Acceptance criteria:

- research notes exist
- reusable patterns are extracted
- risks are documented
- recommended skills are listed

### AOS-LOOP-001 — App Creation Loop Design

Acceptance criteria:

- loop phases are defined
- gates are defined
- minimum viable loop is defined
- deferred automation is documented

### AOS-CTRL-001 — Engineering Control Tower Design

Acceptance criteria:

- dashboard sections are defined
- data sources are listed
- first v0.1 panels are chosen

### AOS-RUNTIME-002 — Repository Scanner MVP

Acceptance criteria:

- scan job exists
- read-only behavior is preserved
- report artifact is generated
- tests exist

### AOS-LOCAL-001 — WSL Windows 11 Local Verification

Acceptance criteria:

- Docker Compose runs from WSL
- API health endpoint responds
- web dashboard loads from Windows browser
- worker starts
- local pre-PR verification can run

## Labels

- area/runtime
- area/frontend
- area/knowledge
- area/ci
- area/orchestration
- area/research
- area/local-runtime
- type/docs
- type/implementation
- type/verification
- status/blocked
- status/ready

## Rule

Every Plane issue should map to a work package and a branch.