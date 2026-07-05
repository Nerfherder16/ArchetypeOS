# AOS-PRG-003 — Guardian Evolution: Lessons Become Rules (RFC-0004 Phase 2)

## Status

In Progress

## Origin

Sprint 4 finale (Plane AOS-15). Operator directive: "if we can evolve CI guardian to get better as we go that's huge." RFC-0004 Phase 2: deterministic guardian support for the lessons discipline. Every change in this package consumes a lesson **by ID** — rules evolve from logged reality, never speculation.

## Verified Baseline

Confirmed by inspection of `tools/pr_guardian.py` (post-PR #40 main):

- `missing-verification-metadata` (line ~306) lists missing fields but not the required line format — the exact failure of PR #37 (LES-003: bold-bullet fields didn't parse and the message didn't say why).
- `web-tests-not-enforced` WARN (line ~191) fires on every `apps/web/src/` change with no escalation or acceptance mechanism (LES-006: fired on PRs #27/#34/#36, never actioned — "silent repetition is the worst state").
- `has_override` (line ~143) accepts any `PR_GUARDIAN_OVERRIDE_<KEY>` substring with no required justification linkage; RFC-0004 requires overrides to cite a lesson ID.
- No rule ties guardian changes to the lessons registry; RFC-0004 Phase 2 requires guardian rule changes to cite lessons.
- Guardian tests live in `apps/api/tests/test_guardian_scanner.py` (8 tests, importing guardian functions directly); guardian must stay stdlib-only (CI runs it bare).

## In-Scope Files

- `tools/pr_guardian.py`
- `.archetype/guardian/accepted_warnings.json` (new)
- `apps/api/tests/test_guardian_evolution.py` (new; keep test_guardian_scanner.py untouched)
- `docs/PR_GUARDIAN.md` (evolution + acceptance registry section)
- `knowledge/wiki/lessons/` (LES-003, LES-006 → closed; index table rows updated)
- state docs + this spec (folding in PR #40 reconciliation)

## Out-of-Scope

- weakening or removing ANY existing check (hard rule)
- new dependencies (stdlib-only stands)
- warning-history persistence across runs (acceptance registry is the stateless mechanism chosen; a run-artifact log remains a future candidate)
- web tests themselves (separate package, Alpha guidance #5)

## Design

Three evolutions, each citing its lesson:

1. **LES-003 — errors teach their fix.** `missing-verification-metadata` message gains the format contract: fields must be plain `Field: value` lines at line start; markdown bold/bullet wrappers do not parse. (Message-only change; matching logic untouched.)
2. **LES-006 — accepted warnings are conscious and expiring.** New `.archetype/guardian/accepted_warnings.json`: entries `{code, lesson, rationale, review_by}`. Guardian loads it (missing/invalid file → empty, graceful note). For each WARN finding whose code has an acceptance: unexpired → message annotated "accepted per <lesson> until <review_by>: <rationale>" (stays WARN, but now cited, never silent); expired → escalate to BLOCK `accepted-warning-expired` forcing a re-decision. Seed entry: `web-tests-not-enforced`, lesson LES-006, review_by 2026-08-01, rationale "UI verified per-package by Orchestrator browser drives; web test framework is a scheduled candidate (Alpha guidance #5)".
3. **RFC-0004 enforcement — evolution is evidence-bound.**
   - `guardian-change-without-lesson` BLOCK: diff touches `tools/pr_guardian.py` without touching `knowledge/wiki/lessons/` (override: `PR_GUARDIAN_OVERRIDE_LESSON` with rationale, for non-rule refactors).
   - `override-without-lesson-citation` BLOCK: PR body uses any `PR_GUARDIAN_OVERRIDE_*` token but contains no `LES-<n>` reference.

This PR must satisfy its own new rules (it touches the guardian AND closes two lessons).

## Acceptance Criteria

- LES-003 consumed — evidence: metadata BLOCK message includes the `Field: value` format hint; `test_metadata_message_teaches_format`.
- LES-006 consumed — evidence: unexpired acceptance annotates the web WARN with lesson + expiry (`test_accepted_warning_annotated`); expired acceptance escalates to BLOCK (`test_expired_acceptance_blocks`); missing registry degrades gracefully (`test_missing_registry_graceful`).
- Guardian changes require lessons — evidence: `test_guardian_change_requires_lesson` (blocks without, passes with, override works).
- Overrides require lesson citations — evidence: `test_override_requires_lesson_citation`.
- Nothing weakened — evidence: all 8 existing guardian tests pass unchanged; full suite green.
- Lessons closed by ID — evidence: LES-003 and LES-006 status → closed citing this package; index updated.
- Self-application — evidence: this PR's own guardian run passes the new rules live.

## Verification Plan

Level 2: ruff/compileall/pytest (55 existing + new). Level 3 with live self-test: the CI guardian job executes the evolved code on this very PR (precedent: PR #33). Orchestrator additionally runs the evolved guardian locally against this branch before push. Merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): guardian code + registry + tests + PR_GUARDIAN.md section. Orchestrator (Fable): spec, lesson closures, independent re-verification including live self-run, PR, merge gate.

## Board Linkage

- Plane: AOS-15 (In Progress), Sprint 4 cycle `b0547f2d-1d11-4fc4-a21b-a0169fd9d92b`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
