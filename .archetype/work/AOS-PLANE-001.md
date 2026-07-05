# AOS-PLANE-001 — Plane Board Sync Discipline

## Status

In Review

## Verified Baseline

Confirmed by inspection and this session's operating history:

- The `ArchetypeOS` Plane project is live (project, 12 labels, default states, 9 work items, 10 epic modules, Sprint 2 cycle) and has been operated through five work-package cycles (AOS-RUNTIME-002 through AOS-RUNTIME-003).
- The precedence rule (markdown wins on conflict) exists in `docs/PLANE_PROJECT_BLUEPRINT.md` and `docs/ACTIVE_WORK.md`, but the operational mechanics are undocumented: when agents update Plane vs markdown, how outages are handled (two real outages occurred on 2026-07-05 and were handled via ad-hoc "pending updates" notes), and no id mapping exists — agents in fresh sessions cannot update the board idempotently without rediscovering UUIDs via API calls.
- Plane AOS-9 criteria: blueprint reflects live project (done for structure), update rule in ACTIVE_WORK (exists, needs pointing at the full discipline), Modules + Cycles enabled (done 2026-07-05).

## In-Scope Files

- `docs/PLANE_PROJECT_BLUEPRINT.md` (new Sync Discipline section + board id registry)
- `docs/ACTIVE_WORK.md` (update rule references the discipline; PR #29 reconciliation folded in)
- `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md` (state + reconciliation)
- `.archetype/work/AOS-RUNTIME-003.md` (→ Merged), this spec

## Out-of-Scope

- two-way sync automation / sync code of any kind (explicitly deferred; this is protocol only)
- Plane webhooks, API tokens in repo, or any credentials
- restructuring the Plane project

## Acceptance Criteria

- Sync discipline documented: who updates what, when, precedence, and outage handling — evidence: Sync Discipline section in `docs/PLANE_PROJECT_BLUEPRINT.md`.
- Board id registry recorded so any future session can update Plane idempotently without discovery calls — evidence: id tables (project, states, items↔work packages↔specs) in the blueprint.
- `docs/ACTIVE_WORK.md` update rule points at the discipline — evidence: rule text in the file.
- PR #29 reconciliation folded in (AOS-RUNTIME-003 → Merged everywhere) — evidence: state file diffs.

## Verification Plan

Level 1/2: repository inspection + local PR Guardian on the docs diff; Level 3 GitHub CI on the PR; merge under the Manual Merge Gate.

## Suggested Delegation

Orchestrator (Fable) directly — the id registry and outage history are session-held context.

## Board Linkage

- Plane: AOS-9 (In Progress)
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
