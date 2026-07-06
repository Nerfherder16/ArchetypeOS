# ArchetypeOS Machine Roadmap

> Machine-readable roadmap. Keep this reconciled with `docs/CURRENT_STATE.md` (the durable state checkpoint) and `docs/ACTIVE_WORK.md` (the execution board). If they disagree, the markdown state files under `docs/` win.

## Current phase

Post-v0.1 — Intelligence layer maturing. v0.1 shipped 2026-07-05 (runtime foundation, scanner, architecture graph, Control Tower, learning loop, PR Guardian evolution). Since then: the Agent Council + Final Judge (RFC-0005), the decision→ADR loop, and the **founding "feed a repo → extract what's useful → surface what's useful *for* a target" loop is now mature end-to-end** — Knowledge Distillation (RFC-0008: deterministic floor + framework evidence + reasoned `DNA.purpose`) feeding the Knowledge Transfer Engine (RFC-0009: portfolio reuse recommendations by calibrated need-coverage). Validated by a full end-to-end reality test over a real 6-repo portfolio.

## Operating rule (2026-07-06)

**Design to the mature-state target — why build things twice?** Define a subsystem's mature-state architecture first; make every work package a strict *subset* of that target (a permanent layer later work extends, never scaffolding you tear out). See `docs/ORCHESTRATOR_PLAYBOOK.md`.

## Immediate objectives (RFC-0009 and adjacent)

1. Embeddings / semantic relevance for the Transfer Engine (local-first, behind the `score_relevance` seam; keep reported confidence coverage-calibrated per LES-023).
2. A Control Tower "Reuse" view surfacing transfer recommendations for a selected project (now unblocked by calibrated confidence).
3. Doc-staleness detection (AOS-20) — catch drifts like a stale roadmap/CURRENT_STATE automatically (the Phase-10 Alpha "NO by machine"; LES-007).
4. Scanner precision — LES-016 (manifest/ecosystem breadth: dotnet/jvm/cargo), LES-017 (secret-signal test-fixture awareness), LES-014 (manifest/import architecture edges).
5. Standalone Council dashboard (AOS-COUNCIL-002); backups (AOS-22).

## Boot order for any session

`CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → the active spec in `.archetype/work/`.

## Non-negotiables

Builder ≠ verifier (independently re-run everything). Never weaken the PR Guardian. Head-SHA-pinned Manual Merge Gates. Markdown state files under `docs/` win over Plane. Lessons recorded in the same change set. No scope expansion without an RFC. One PR = one work package.
