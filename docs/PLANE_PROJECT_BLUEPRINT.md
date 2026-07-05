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

Status: live. Modules, Cycles, Pages, Intake, and Views were enabled in Project Settings -> Features on 2026-07-05. All 10 epics exist as Plane Modules with their issues assigned (cycle id `8f6103fe-f2f2-457b-973b-571bde6c5795`), and the "Sprint 2 — Operating Loop" cycle contains AOS-1, AOS-2, AOS-3, AOS-7, and AOS-9.

## Current Items (Live in Plane)

These are the actual seeded Plane work items (identifier `AOS-<n>`), superseding the conceptual `Suggested Issues` below where they overlap:

- AOS-1 — Repository Scanner MVP — Done
- AOS-2 — Build process hardening — Done (work package `AOS-PROC-001`, PR #21 merged)
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

Plane is the live working board. The markdown state files (`docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`) are the durable fallback and win on conflict.

## Sync Discipline (AOS-PLANE-001)

Manual, protocol-driven sync. Two-way sync automation is explicitly deferred; no sync code exists.

### When agents update Plane

- Work package starts: item → In Progress; description updated with spec path and branch.
- PR opens: description updated with the PR link.
- PR merges: item → Done.
- New work packages: create the item first, then the `.archetype/work/` spec, then start.

### When agents update markdown

- In the work-package PR itself: `ACTIVE_WORK` entry with verification metadata, `CURRENT_STATE`, `HANDOFF`, `RECENT_CHANGES`.
- Post-merge reconciliation (own PR, or folded into the next docs package): item → Merged with PR number, merge commit, and CI evidence.

### Conflict and outage handling

- On conflict, markdown wins. Fix Plane to match markdown, never the reverse.
- When Plane is unreachable: continue on markdown alone; record every deferred board change as a "Pending Plane updates" line under Blocked Work in `docs/ACTIVE_WORK.md`; apply and clear them when Plane returns. (Exercised twice on 2026-07-05.)

### Board ID Registry

Recorded so any session can update the board idempotently without discovery calls. Workspace-local UUIDs only — no credentials.

Project: `765d909a-a20a-4487-967d-866b9ea60ded` (identifier `AOS`)
Sprint 2 cycle: `8f6103fe-f2f2-457b-973b-571bde6c5795`

States:

| State | ID |
| --- | --- |
| Backlog | `24b8392d-2fac-48d0-bbaa-08eabe21f4e6` |
| Todo | `6b9f3eba-2b23-4438-b643-2b557dcff313` |
| In Progress | `bc93d571-20d6-4b39-9080-29ab99cd41ea` |
| Done | `65a682b5-8eac-45b3-98ba-3684b8f6df3d` |
| Cancelled | `2d9542aa-80c4-41a3-b06b-bbc7c40efcff` |

Work items:

| Item | Work package | Spec | Issue ID |
| --- | --- | --- | --- |
| AOS-1 | AOS-RUNTIME-002 | — (predates specs) | `4cbde625-bef8-47cc-99d9-ecac05be823b` |
| AOS-2 | AOS-PROC-001 | `.archetype/work/AOS-PROC-001.md` | `adc47a82-25d2-4b8c-b667-3dbdf85d0fd4` |
| AOS-3 | AOS-KNOW-001 | `.archetype/work/AOS-KNOW-001.md` | `0933cd27-f4ec-4965-adfa-3880e6597146` |
| AOS-4 | AOS-RUNTIME-003 | `.archetype/work/AOS-RUNTIME-003.md` | `49669cd1-6f40-4899-a36d-b568de86ee54` |
| AOS-5 | AOS-ARCH-001 | `.archetype/work/AOS-ARCH-001.md` | `29211eaa-5e39-42e2-82f5-53f78436936b` |
| AOS-6 | AOS-PRG-002 | TBD | `ca03441d-411c-4055-abc8-7eaf5b65c52b` |
| AOS-7 | AOS-LOCAL-001 | TBD | `1de85361-4cf9-48a2-ab7e-191419c9cdd3` |
| AOS-8 | AOS-CTRL-001 | `.archetype/work/AOS-CTRL-001.md` | `0f61f00b-98bd-45cd-bc59-045666b0a7b8` |
| AOS-9 | AOS-PLANE-001 | `.archetype/work/AOS-PLANE-001.md` | `4e0f1c47-4635-4da5-bc8f-68a03e922635` |

Modules (epics): Foundation Runtime `b317c890-f4f2-4727-9822-18cd5f9672e4`; CI/Verification/PR Guardian `70e4eb8e-9d30-4b46-82d6-e06ab35760d7`; Orchestration Engine `437f8047-4ce4-473c-be45-dc4b88fa141d`; Agent Communication Bus `9ad33657-48cd-4d79-a328-dfccd8569232`; Repository Intelligence `05555846-09af-416e-9aa6-1d0b5e8a4209`; Knowledge Vault `1a2b4283-eab9-44c1-a770-441da89892e4`; App Creation Loop `c36805ee-c8eb-48bc-b285-392c3eee86fd`; Dashboard/Operator Console `a0ca9524-38e5-43e1-bff9-e5ad3f79b04d`; Plane Integration `5eb27dc4-5922-4757-8f83-5df0e4fabab5`; Local Agent Runtime/Worktrees `3ae85f73-5f95-4a4f-bc59-e64465bfc804`.

## Rule

Every Plane issue should map to a work package and a branch.