# AOS-LEARN-002 — Learning Feedback Loop, Phase 1 (RFC-0004)

## Status

In Review

## Origin

Direct operator directive (2026-07-05): "every PR and every learning moment and every failure should tie back into our loops … if we can evolve CI guardian to get better as we go that's huge … it's partially a point of the system." Sprint 4 package 2 (Plane AOS-14).

## Verified Baseline

Confirmed by inspection:

- `knowledge/wiki/lessons/` existed but was empty (`.gitkeep` only) since the AOS-KNOW-001 vault seed — the domain was planned, never populated.
- Learning events through Sprint 3–4 live only in PR threads and session context: guardian BLOCKs on PRs #33/#36/#37 prep, the PR #39 conftest review catch, the /health self-found defect, recurring web `MISSING_TESTS` warnings — none durably recorded.
- The Alpha Review (PR #37) answered Phase 10 question 2 "NO by machine": no staleness/lesson detection exists.
- The digest aggregates product-plane DB state only; repo lessons have no API-visible representation (constraint honored — see Design).

## In-Scope Files

- `docs/rfc/RFC-0004-Learning-Feedback-Loop.md` (new)
- `knowledge/wiki/lessons/index.md` + `LES-001.md`..`LES-007.md` (new)
- `knowledge/wiki/index.md` (lessons domain linked), `knowledge/wiki/log.md` (entry)
- `CLAUDE.md` (one operating rule)
- `docs/CAPABILITY_MAP.md` (Layer 8 entry)
- state docs + this spec (folding in PR #39 reconciliation)

## Out-of-Scope

- guardian code changes (Phase 2, AOS-PRG-003 — that spec must consume lessons by ID)
- digest/API integration of lessons (deferred in RFC-0004 until lessons have an API read path; candidate pairing with the deferred KnowledgePage API)
- any `apps/` or `tools/` change

## Design

Phase 1 per RFC-0004: lessons are durable vault pages with a fixed contract (Event / Source / Category / Lesson / Loop feed / Status) registered in a single index table with an `open`/`closed` queue. Seeded exclusively with real Sprint 3–4 events — no invented examples. Enforcement is convention (CLAUDE.md rule + Orchestrator review) until AOS-PRG-003 adds deterministic guardian support.

## Acceptance Criteria

- RFC-0004 exists with problem/decision/alternatives/risks/acceptance — evidence: `docs/rfc/RFC-0004-Learning-Feedback-Loop.md`.
- Registry + 7 real-event lessons following the contract — evidence: `knowledge/wiki/lessons/` (LES-001..003 guardian catches, LES-004 review remediation, LES-005 self-found defect closed by PR #39, LES-006/007 open gaps feeding package candidates).
- Open-lesson queue visible — evidence: index table shows 3 open (LES-003, LES-006, LES-007) with named loop feeds.
- CLAUDE.md operating rule added — evidence: Operating rules list.
- Vault lint dimensions respected — evidence: pages have aliases/owner/evidence/links; registry linked from `wiki/index.md`.
- No code changed; suite stays green — evidence: pytest 55/55, ruff clean.
- PR #39 reconciliation folded in — evidence: state docs show AOS-RUNTIME-004 Merged (PR #39, merge `2b8febf`).

## Verification Plan

Level 2: ruff/compileall/pytest unchanged-green (docs-only). Level 3: GitHub CI; merge under the Manual Merge Gate. Content verification: every lesson row cites a checkable source (PR number / captured artifact).

## Suggested Delegation

Orchestrator (Fable) direct: the lessons ARE this session's events — delegation would launder first-hand evidence through an agent without access to it.

## Board Linkage

- Plane: AOS-14 (In Progress, high), Sprint 4 cycle `b0547f2d-1d11-4fc4-a21b-a0169fd9d92b`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
