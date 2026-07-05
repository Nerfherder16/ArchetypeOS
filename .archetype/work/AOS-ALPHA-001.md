# AOS-ALPHA-001 — Phase 10 Alpha Review: ArchetypeOS Evaluates ArchetypeOS

## Status

In Progress

## Verified Baseline

Confirmed by inspection:

- Phase 10 is defined in `docs/CONCRETE_BUILD_PATH.md` (lines 214-229): "Before expanding, run ArchetypeOS on its own repo." Five questions — did it understand itself, find stale docs, generate useful decisions, did PR Guardian find real risks, did nightly learning produce useful recommendations. Acceptance: "ArchetypeOS can evaluate ArchetypeOS" and "Output is useful enough to guide next development."
- Every capability the review exercises is merged on `main` (commit `8b39e67`): scanner + DNA (PR #14/#29), architecture graph (PR #25), scanner-informed PR Guardian (PR #2/#33), decisions/research (PR #34), nightly digest (PR #36), dashboard (PR #27), `/guardian` command (PR #35).
- `safe_repo_path` (`apps/api/app/repository_scanner.py:114`) accepts any directory under `REPOSITORY_ROOT`, so `REPOSITORY_ROOT=/home/user` + `local_path=ArchetypeOS` scans this working tree through the ordinary API path — no special-casing needed.
- Sprint 3 state: AOS-6, AOS-10, AOS-11 all Done; AOS-12 is the only open Sprint 3 item. PR #36 state reconciliation is folded into this package (state files still say AOS-LEARN-001 "In Review").

## In-Scope Files

- `docs/ALPHA_REVIEW_V0_1.md` (new — the review artifact)
- `.archetype/alpha/` (new — captured evidence: scan report, DNA, architecture graph, digest, guardian output as committed JSON/text snapshots)
- state docs (`docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`) — PR #36 reconciliation + Sprint 3 close-out
- this spec

## Out-of-Scope

- ANY code change to `apps/` or `tools/` — this package runs the system, it does not modify it. Findings become recorded decisions and next-sprint candidates, not in-package fixes.
- LLM-driven evaluation (deterministic outputs + Orchestrator interpretation only)
- new endpoints, models, migrations, UI changes

## Design

Execution (Orchestrator-run, live local stack, sqlite, `REPOSITORY_ROOT=/home/user`):

1. Boot the API; register project "ArchetypeOS" and repository `local_path=ArchetypeOS` via the API.
2. `POST /repositories/{id}/scan` — self-scan; capture the stored scan artifact and `GET /repositories/{id}/dna`.
3. `GET /projects/{id}/architecture` — self architecture graph.
4. Run `tools/pr_guardian.py` in in-repo scan mode against the current tree (read-only) and capture findings.
5. Record real decisions via `POST` decisions/research-notes from the review findings (e.g. stale docs found), exercising the evidence-link rules.
6. `POST /projects/{id}/digests` — nightly digest over the accumulated self-evaluation state; verify draft-only recommendations.
7. Write `docs/ALPHA_REVIEW_V0_1.md`: one section per Phase 10 question, each answered YES/PARTIAL/NO with pointers to captured evidence in `.archetype/alpha/`, plus a "next development guidance" section (the Phase 10 usefulness criterion) and a v0.1 scope-lock conformance table.
8. Reconcile state files: AOS-LEARN-001 → Merged (PR #36, merge commit `8b39e67`); Sprint 3 / v0.1 close-out pending this PR's merge.

## Acceptance Criteria

- ArchetypeOS scanned itself through the public API — evidence: `.archetype/alpha/self-scan.json` (stored artifact copy) + `.archetype/alpha/self-dna.json` with non-empty ecosystems/languages matching this repo (Python + TypeScript, docker + CI files present).
- Architecture graph produced for itself — evidence: `.archetype/alpha/self-architecture.json` (nodes/edges > 0).
- Guardian ran on itself and its findings were reviewed — evidence: `.archetype/alpha/self-guardian.txt` verbatim output + interpretation in the review artifact.
- Decisions generated from real findings with linked research — evidence: `.archetype/alpha/self-decisions.json` (≥2 decisions, ≥1 with a typed `research_note` evidence entry).
- Digest produced draft-only recommendations over the self-evaluation state — evidence: `.archetype/alpha/self-digest.json` (every recommendation `status == "draft"`).
- All five Phase 10 questions answered with evidence pointers — evidence: `docs/ALPHA_REVIEW_V0_1.md` sections 1-5.
- Output guides next development — evidence: review artifact "Next Development Guidance" section listing concrete, evidence-backed candidates.
- PR #36 reconciliation folded in — evidence: state docs show AOS-LEARN-001 Merged.

## Verification Plan

Level 2: full local suite unchanged and green (no code changes — 52/52 must still pass). Level 4 (local): the review itself IS the verification run — every artifact in `.archetype/alpha/` is produced by live API calls, not hand-written. Level 3: GitHub CI on the PR; merge under the Manual Merge Gate.

## Suggested Delegation

Orchestrator (Fable) end-to-end: this package is execution + interpretation of the system's own outputs — the Orchestrator's verification role — with no code to build. No builder delegation.

## Board Linkage

- Plane: AOS-12 (In Progress), Sprint 3 cycle `9d9c2fd6-3305-419a-a5e8-0c6d4d3c058b`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
