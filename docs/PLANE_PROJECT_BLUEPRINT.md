# Plane Project Blueprint

## Purpose

This document defines the Plane structure for ArchetypeOS and records its live status.

Plane is back online as of 2026-07-05 (power restored to the local instance). The `ArchetypeOS` project has been created and seeded per this blueprint. Plane is now the live working board; this document and the other markdown state files remain the durable fallback and win on conflict until AOS-9 defines full sync discipline. Note: the user's workstation WSL/Docker status is a separate concern and is not yet confirmed — see the WSL local-verification blocker in `docs/ACTIVE_WORK.md` / `docs/CURRENT_STATE.md`, which stays pending confirmation.

## Project

Name: ArchetypeOS
Identifier: AOS
Plane project id: `765d909a-a20a-4487-967d-866b9ea60ded`
Status: Live. Default states (Backlog / Todo / In Progress / Done / Cancelled) and 12 blueprint labels have been created in Plane.

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

Status: the Sprint 2 cycle could not yet be created via the Plane API because the project's Cycles feature is disabled. Modules (the 10 epics above, as Plane Modules) are blocked the same way. A human must enable Modules and Cycles in Plane Project Settings -> Features before either can be created.

## Current Items (Live in Plane)

These are the actual seeded Plane work items (identifier `AOS-<n>`), superseding the conceptual `Suggested Issues` below where they overlap:

- AOS-1 — Repository Scanner MVP — Done
- AOS-2 — Build process hardening — In Progress (work package `AOS-PROC-001`)
- AOS-3 — Knowledge Vault Seed — Todo, `status/ready` (work package `AOS-KNOW-001`)
- AOS-4 — Scan persistence/history — Backlog
- AOS-5 — Architecture Spine Graph draft — Backlog
- AOS-6 — PR Guardian reads scanner output — Backlog
- AOS-7 — WSL Win11 local verification — Todo
- AOS-8 — Control Tower first dashboard surface — Backlog
- AOS-9 — Plane board sync discipline — Todo

GitHub issues #16-#20 were briefly opened to mirror this seed and have since been closed as migrated to Plane; Plane is the source for these items going forward.

## Suggested Issues

Original conceptual work-package naming from before the project was seeded in Plane. Retained for historical mapping; new work should use the `AOS-<n>` Plane items above plus a `.archetype/work/<TASK-ID>.md` spec.

- AOS-PMO-001 — Reconcile State Files
- AOS-RESEARCH-001 — Claude Code Workflow Research
- AOS-LOOP-001 — App Creation Loop Design
- AOS-CTRL-001 — Engineering Control Tower Design
- AOS-RUNTIME-002 — Repository Scanner MVP
- AOS-LOCAL-001 — WSL Windows 11 Local Verification

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

## Precedence Rule

Plane is the live working board. The markdown state files (`docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`) are the durable fallback and win on conflict until AOS-9 — Plane board sync discipline defines full two-way sync.

## Rule

Every Plane issue should map to a work package and a branch.