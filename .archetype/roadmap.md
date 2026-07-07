# ArchetypeOS Machine Roadmap

> Machine-readable roadmap. Keep this reconciled with `docs/CURRENT_STATE.md` (the durable state checkpoint) and `docs/ACTIVE_WORK.md` (the execution board). If they disagree, the markdown state files under `docs/` win.

## Current phase

Post-v0.1 — Intelligence layer maturing. v0.1 shipped 2026-07-05 (runtime foundation, scanner, architecture graph, Control Tower, learning loop, PR Guardian evolution). Since then: the Agent Council + Final Judge (RFC-0005), the decision→ADR loop, and the **founding "feed a repo → extract what's useful → surface what's useful *for* a target" loop is now mature end-to-end** — Knowledge Distillation (RFC-0008: deterministic floor + framework evidence + reasoned `DNA.purpose`) feeding the Knowledge Transfer Engine (RFC-0009: portfolio reuse recommendations by calibrated need-coverage). Validated by a full end-to-end reality test over a real 6-repo portfolio.

## Operating rule (2026-07-06)

**Design to the mature-state target — why build things twice?** Define a subsystem's mature-state architecture first; make every work package a strict *subset* of that target (a permanent layer later work extends, never scaffolding you tear out). See `docs/ORCHESTRATOR_PLAYBOOK.md`.

## Immediate objectives (RFC-0009 and adjacent)

1. Embeddings / semantic relevance for the Transfer Engine (local-first, behind the `score_relevance` seam; keep reported confidence coverage-calibrated per LES-023).
2. **Design and User Experience — done / next.** A scoped `.aos-*` ops-deck **design system** (tokens, self-hosted Bebas Neue, HUD/neumorphic/signal-meter primitives, both themes, inert under `.aos-surface`) + the first view built on it — the Control Tower **"Reuse" view** wired live to the Transfer Engine (`POST /projects/{id}/transfer`) — **shipped (AOS-UI-001, PR #76)**. The **WebGL radar instrument** — the Control Tower's **first WebGL surface** on the `.aos-*` design system (react-three-fiber; distance-from-center = reuse strength = `1 − confidence`; the radar drives the cards: click a blip → expand its card, hover a card → highlight its blip; WebGL-probe/reduced-motion fallbacks) — **shipped (AOS-UI-002, PR #79)**. Next UI increment: the **full rail-shell migration** (AOS-UI-003 — a generic reusable `<Radar>` + move the stacked Control Tower sections onto the `.aos-*` system behind a rail shell + view routing), a strict superset of AOS-UI-001/002.

   In flight (ops): **AOS-OPS-001 — CI-green signal** (branch `claude/aos-ci-green-signal`): a `ci-green` fan-in job in `.github/workflows/ci.yml` that comments `✅ CI green @ <sha>` on all-green so a watching session is event-woken by the webhook-delivered comment instead of timed polling.
3. Doc-staleness detection (AOS-20) — **shipped (PR #68)**: catches drifts like a stale roadmap/CURRENT_STATE automatically (the Phase-10 Alpha "NO by machine"; LES-007 closed).
4. Scanner precision — LES-016 (manifest/ecosystem breadth: dotnet/jvm/cargo) + LES-017 (secret-signal test-fixture awareness) **shipped (AOS-SCAN-PRECISION-001, PR #75; both closed)**; LES-014 (manifest/import architecture edges) remains.
5. Standalone Council dashboard (AOS-COUNCIL-002) **shipped (PR #74)**; backups (AOS-22) remain.

## Boot order for any session

`CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → the active spec in `.archetype/work/`.

## Non-negotiables

Builder ≠ verifier (independently re-run everything). Never weaken the PR Guardian. Head-SHA-pinned Manual Merge Gates. Markdown state files under `docs/` win over Plane. Lessons recorded in the same change set. No scope expansion without an RFC. One PR = one work package.
