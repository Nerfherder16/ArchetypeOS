# Plane Project Blueprint

## Purpose

This document defines the Plane structure for ArchetypeOS and records its live status.

The `ArchetypeOS` Plane project is live and is the working board; this document and the other markdown state files remain the durable fallback and win on conflict per the Sync Discipline below (AOS-PLANE-001, merged PR #30).

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

- AOS-1 — Repository Scanner MVP — Done (PR #14)
- AOS-2 — Build process hardening — Done (PR #21)
- AOS-3 — Knowledge Vault Seed — Done (PR #23)
- AOS-4 — Scan persistence/history — Done (PR #29)
- AOS-5 — Architecture Spine Graph API — Done (PR #25)
- AOS-6 — PR Guardian reads scanner output — Backlog
- AOS-7 — WSL Win11 local verification — executed on `teevee-1` 2026-07-05; Done when the handoff PR merges
- AOS-8 — Control Tower first dashboard surface — Done (PR #27)
- AOS-9 — Plane board sync discipline — Done (PR #30)

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
Sprint 3 cycle: `9d9c2fd6-3305-419a-a5e8-0c6d4d3c058b` (v0.1 Completion — complete)
Sprint 4 cycle: `b0547f2d-1d11-4fc4-a21b-a0169fd9d92b` (Self-Healing & Learning Loop — complete)
Sprint 5 cycle: `8bc59801-82c5-4550-b188-9f15323a1ddc` (Enforcement & Foundations — active)

States:

| State | ID |
| --- | --- |
| Backlog | `24b8392d-2fac-48d0-bbaa-08eabe21f4e6` |
| Todo | `6b9f3eba-2b23-4438-b643-2b557dcff313` |
| In Progress | `bc93d571-20d6-4b39-9080-29ab99cd41ea` |
| Done | `65a682b5-8eac-45b3-98ba-3684b8f6df3d` |
| Cancelled | `2d9542aa-80c4-41a3-b06b-bbc7c40efcff` |

> **Board reconciliation 2026-07-06:** the board had drifted (tracked through ~AOS-24 / PR #52; the entire Council + Distillation + Transfer intelligence arc, PRs #54–#66, was tracked only in the markdown state files). Backfilled as **Done** (board seq #27–#39): Council PhaseA/C/C2A/C2B, RFC-0008, Phase B, LLM isolation, Distill 001–004, Transfer 001–002. **Now current through PR #66.** Live items: **AOS-20** (doc-staleness, In Progress — laptop session) and **AOS-25** (RFC-0009 embeddings, In Progress — remote session). Going forward both tandem sessions maintain the board (item → In Progress on claim, → Done on merge); markdown still wins on conflict. A duplicate doc-staleness issue (seq #26) was Cancelled in favour of the canonical AOS-20 (seq #20).

Work items:

| Item | Work package | Spec | Issue ID |
| --- | --- | --- | --- |
| AOS-1 | AOS-RUNTIME-002 | — (predates specs) | `4cbde625-bef8-47cc-99d9-ecac05be823b` |
| AOS-2 | AOS-PROC-001 | `.archetype/work/AOS-PROC-001.md` | `adc47a82-25d2-4b8c-b667-3dbdf85d0fd4` |
| AOS-3 | AOS-KNOW-001 | `.archetype/work/AOS-KNOW-001.md` | `0933cd27-f4ec-4965-adfa-3880e6597146` |
| AOS-4 | AOS-RUNTIME-003 | `.archetype/work/AOS-RUNTIME-003.md` | `49669cd1-6f40-4899-a36d-b568de86ee54` |
| AOS-5 | AOS-ARCH-001 | `.archetype/work/AOS-ARCH-001.md` | `29211eaa-5e39-42e2-82f5-53f78436936b` |
| AOS-6 | AOS-PRG-002 | TBD | `ca03441d-411c-4055-abc8-7eaf5b65c52b` |
| AOS-7 | AOS-LOCAL-001 | `.archetype/work/AOS-LOCAL-001.md` | `1de85361-4cf9-48a2-ab7e-191419c9cdd3` |
| AOS-8 | AOS-CTRL-001 | `.archetype/work/AOS-CTRL-001.md` | `0f61f00b-98bd-45cd-bc59-045666b0a7b8` |
| AOS-9 | AOS-PLANE-001 | `.archetype/work/AOS-PLANE-001.md` | `4e0f1c47-4635-4da5-bc8f-68a03e922635` |
| AOS-10 | AOS-DEC-001 | `.archetype/work/AOS-DEC-001.md` | `4cfe76e8-2475-4d5f-be23-e0eb6479dd85` |
| AOS-11 | AOS-LEARN-001 | `.archetype/work/AOS-LEARN-001.md` | `c0e934ce-272d-4e62-a14e-8beae1afb01d` |
| AOS-12 | AOS-ALPHA-001 | `.archetype/work/AOS-ALPHA-001.md` | `a59b81eb-f3a4-46ad-a1a0-b42989a10c6c` |
| AOS-13 | AOS-RUNTIME-004 | `.archetype/work/AOS-RUNTIME-004.md` | `661b98e5-4fed-4fce-b893-daac85801005` |
| AOS-14 | AOS-LEARN-002 | `.archetype/work/AOS-LEARN-002.md` | `6f232f60-ae61-46bb-9e81-f0829017c6fd` |
| AOS-15 | AOS-PRG-003 | `.archetype/work/AOS-PRG-003.md` | `7dcfda25-eb2b-4937-8b6d-717d09f34d80` |
| AOS-16 | AOS-WEB-001 | `.archetype/work/AOS-WEB-001.md` | `a55bbffc-71cc-4d38-8056-804b56e77cef` |
| AOS-17 | AOS-ALEMBIC-001 | `.archetype/work/AOS-ALEMBIC-001.md` | `af8e70b1-7e7d-496c-a417-5d06ca35e053` |
| AOS-18 | Worker pipeline | TBD | `94fd1aa3-d627-4b19-836c-63060e6aaf99` |
| AOS-19 | RFC-0005 provider + council | TBD (RFC first) | `005d11e8-6dec-4e16-909a-31d219c087da` |
| AOS-20 | Doc-staleness (LES-007) | TBD | `c0e4680f-a097-4df5-b42b-3ae36c0364d2` |
| AOS-21 | Second repository | TBD | `6e472195-6781-4dcf-8eff-ccf1ff11d7de` |
| AOS-22 | teevee-1 backups | TBD | `50d7bc1c-4f06-4187-b8fa-7a7d8bc10810` |
| AOS-23 | Knowledge read path | TBD | `5ebbd32a-3bda-4440-9de2-caea817ab7cc` |
| AOS-59 | Evaluate: claude-obsidian (Done) | `knowledge/wiki/repositories/claude-obsidian.md` | `7abe5f84-62a6-4908-beae-e1caa4f624ea` |
| AOS-60 | Borrow BM25 retrieval scripts → RFC-0010 | `knowledge/wiki/repositories/claude-obsidian.md` | `8b17cd5f-1c77-4ba6-8b1e-c34a75f8b5f9` |
| AOS-61 | Evaluate: claude-video (Done) | `knowledge/wiki/repositories/claude-video.md` | `23ef7c9a-809b-4fde-9b63-e36ae86414ac` |
| AOS-62 | Adopt claude-video pipeline as AOS video-ingestion capability | `knowledge/wiki/repositories/claude-video.md` (RFC-first) | `0eebbdec-3b87-4a70-9633-7024bb2ac1a2` |
| AOS-63 | Evaluate: T3MP3ST (Done) | `knowledge/wiki/repositories/T3MP3ST.md` | `221efb2a-fa76-405e-a12c-04e43a4e28b3` |
| AOS-64 | T3MP3ST recon as AGPL-isolated external security service (EES) | `knowledge/wiki/repositories/T3MP3ST.md` (RFC-first) | `6394ecb0-6984-4965-9990-7fa1e746f4fc` |

Modules (epics): Foundation Runtime `b317c890-f4f2-4727-9822-18cd5f9672e4`; CI/Verification/PR Guardian `70e4eb8e-9d30-4b46-82d6-e06ab35760d7`; Orchestration Engine `437f8047-4ce4-473c-be45-dc4b88fa141d`; Agent Communication Bus `9ad33657-48cd-4d79-a328-dfccd8569232`; Repository Intelligence `05555846-09af-416e-9aa6-1d0b5e8a4209`; Knowledge Vault `1a2b4283-eab9-44c1-a770-441da89892e4`; App Creation Loop `c36805ee-c8eb-48bc-b285-392c3eee86fd`; Dashboard/Operator Console `a0ca9524-38e5-43e1-bff9-e5ad3f79b04d`; Plane Integration `5eb27dc4-5922-4757-8f83-5df0e4fabab5`; Local Agent Runtime/Worktrees `3ae85f73-5f95-4a4f-bc59-e64465bfc804`; External Repo Evaluation & Adoption Pipeline `c8c0dadf-1922-4a37-8742-55df5fd7bf5e`.

## Rule

Every Plane issue should map to a work package and a branch.