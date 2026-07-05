# RFC-0004 — Learning Feedback Loop

## Status

Accepted (operator-directed, 2026-07-05: "every PR and every learning moment and every failure should tie back into our loops … if we can evolve CI guardian to get better as we go that's huge … it's partially a point of the system")

## Problem

ArchetypeOS accumulates learning events constantly — guardian BLOCKs, CI failures, review remediations, operator corrections, live defects it finds in itself — but through Sprint 3 those events lived only in PR threads and session context. The Alpha Review (PR #37) made the cost concrete: the one Phase 10 question answered "NO by machine" was staleness/lesson detection, and the guardian's real catches (secret fixtures, metadata format, capability map) had no durable record a future loop could consume. A learning moment that only exists in a merged PR's comments is a learning moment the system will repeat.

## Decision

Every learning event becomes a durable, structured **lesson page** in `knowledge/wiki/lessons/`, registered in `knowledge/wiki/lessons/index.md`, in the same change set as the work that surfaced it (or the next reconciliation for post-merge events). Lessons are the substrate the improvement loops consume.

### What counts as a learning event

1. Every PR Guardian **BLOCK** on a real PR (true positive or false positive — both teach).
2. Every **CI failure** whose cause was not already a recorded lesson.
3. Every **review remediation** — a defect the Orchestrator or a reviewer catches that the builder missed.
4. Every **live defect** the system finds in itself (alpha-review style findings).
5. Every **operator correction** of agent behavior worth keeping.

### Lesson page contract

Follows the vault page template (`knowledge/templates/page-template.md`) with a fixed Content block:

- **Event** — what happened, verbatim where possible (finding code, error line)
- **Source** — PR number(s), CI run, or session date
- **Category** — one of: `guardian-catch`, `guardian-gap`, `ci-failure`, `review-remediation`, `self-found-defect`, `process`
- **Lesson** — the transferable rule, stated so a future agent can apply it without this context
- **Loop feed** — which loop consumes it: guardian rule candidate (AOS-PRG-003 log), work-package candidate, spec/checklist change, or "validated existing rule"
- **Status** — `open` (not yet fed into a loop) or `closed` (consumed: cite the PR/rule/package that consumed it)

IDs are sequential (`LES-001`, …). The index table is the single registry; on conflict the index wins.

### How lessons feed the loops

- **Guardian evolution (AOS-PRG-003)**: `guardian-catch` and `guardian-gap` lessons are the guardian's miss/false-positive log. Every guardian rule change must cite at least one lesson by ID — rules evolve from logged reality, never speculation, and are never silenced in place.
- **Work packages**: `self-found-defect` and recurring lessons become spec'd packages (precedent: LES-005 → AOS-RUNTIME-004).
- **Specs and PR discipline**: `process` lessons amend the work-package template, PR body conventions, or CLAUDE.md operating rules.
- **Nightly digest (deferred)**: repo lessons are meta-plane artifacts; the digest aggregates product-plane DB state. Surfacing lesson counts in the digest requires an API-visible lessons representation — explicitly deferred until a package gives lessons a read path (candidate pairing: the deferred KnowledgePage API). The guardian, which already reads the repo, is the near-term machine consumer.

### Enforcement path

Phase 1 (this RFC): convention, enforced by Orchestrator review — CLAUDE.md gains the operating rule "record a lesson for every guardian BLOCK, CI failure, and review remediation in the same change set."
Phase 2 (AOS-PRG-003): deterministic guardian support — e.g., a PR that changes `tools/pr_guardian.py` rules must also touch `knowledge/wiki/lessons/` (evidence-cited evolution), and override tokens must cite a lesson ID.

## Alternatives considered

- **DB-backed lessons via the existing API** (ResearchNote/Decision rows): digest-visible immediately, but splits truth between repo and per-deployment databases; process lessons must survive database resets and travel with the repo. Rejected for phase 1.
- **Guardian-run artifacts as the log** (persist every guardian report): captures events but not lessons — raw findings without the transferable rule or loop assignment. AOS-PRG-003 may add this as supporting evidence, not as the registry.
- **Keep using PR threads + state docs**: status quo; demonstrated insufficient by the Alpha Review.

## Risks

- Lesson rot (pages never closed): mitigated by the `open`/`closed` status in a single index — open lessons are a visible queue, and reconciliation PRs review it.
- Ceremony creep: the contract is one small page per event; if an event teaches nothing new, it cites the existing lesson instead of duplicating (index check first).

## Acceptance criteria

- Lessons directory seeded with the real Sprint 3–4 events (no invented examples), each following the contract.
- Registry index with status queue exists.
- CLAUDE.md operating rule added.
- AOS-PRG-003 spec consumes `guardian-catch`/`guardian-gap` lessons by ID.

## Effort

Phase 1: docs-only, one package (AOS-LEARN-002). Phase 2: inside AOS-PRG-003.

## Dependencies

- RFC-0002 (Knowledge System) — vault structure and lint dimensions
- AOS-PRG-003 — machine enforcement and guardian consumption
