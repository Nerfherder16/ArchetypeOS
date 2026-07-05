# Lessons Index

## Aliases

- lessons log
- learning feedback registry
- miss and false-positive log

## Status

validated

## Owner

Chief Architect / Orchestrator

## Evidence

- RFC-0004 (`docs/rfc/RFC-0004-Learning-Feedback-Loop.md`) defines the contract this index implements
- Every row cites its source PR/run

## Linked Decisions / Projects

- [[../decisions/|decisions]] — lessons feed decision-making per RFC-0004
- `docs/ALPHA_REVIEW_V0_1.md` — the review that motivated this registry

## Content

Single registry for learning events per RFC-0004. Every guardian BLOCK, CI failure, review remediation, self-found defect, and operator correction gets a row and a page. `open` lessons are the improvement queue; a lesson is `closed` only when a loop has consumed it (cite what consumed it). On conflict between a lesson page and this table, this table wins.

| ID | Date | Category | Lesson (short) | Source | Status | Consumed by |
| --- | --- | --- | --- | --- | --- | --- |
| [[LES-001]] | 2026-07-05 | guardian-catch | Credential-shaped strings in test fixtures trip the secret scan — use obviously-fake markers | PRs #33, #36 prep | closed | Validated secret-pattern rule; fixture naming practice |
| [[LES-002]] | 2026-07-05 | guardian-catch | Verification metadata literals are exact — annotations go in Method, not the literal | AOS-DEC-001 prep | closed | Validated metadata rule; PR body convention |
| [[LES-003]] | 2026-07-05 | guardian-catch | PR-body metadata must be plain `Field: value` lines; new docs must update the capability map | PR #37 first guardian pass | closed | AOS-PRG-003: metadata BLOCK message teaches the format |
| [[LES-004]] | 2026-07-05 | review-remediation | Tests asserting service-down states must pin guaranteed-dead resources, not default ports | PR #39 review | closed | conftest fix in PR #39; extends AOS-LOCAL-001 hermeticity lesson |
| [[LES-005]] | 2026-07-05 | self-found-defect | Health/probe endpoints must degrade per-probe, never propagate probe exceptions | Alpha Review (PR #37) → fix PR #39 | closed | AOS-RUNTIME-004 (the loop's reference demonstration) |
| [[LES-006]] | 2026-07-05 | guardian-gap | `MISSING_TESTS` warnings for `apps/web` have fired on every UI package and were never actioned | PRs #27, #34, #36 | closed | AOS-PRG-003: accepted-warnings registry (expires 2026-08-01); web tests still a package candidate |
| [[LES-007]] | 2026-07-05 | process | Doc staleness is only caught by human review — the one Phase 10 "NO by machine" | Alpha Review Q2 | open | Doc-staleness detection package candidate (Alpha guidance #3) |
| [[LES-008]] | 2026-07-05 | review-remediation | Opaque identifiers (UUIDs/SHAs) are copied from tool output or fetched at write time — never reconstructed from memory | PR #42 prep, self-caught | closed | Corrected registry row; registry-verification practice; guardian format-check candidate |
| [[LES-009]] | 2026-07-05 | process | A dated warning-acceptance (`review_by`) is a forcing function — the expiry drove the web-tests package before 2026-08-01 rather than letting the gap persist; the accepted-warnings mechanism (AOS-PRG-003) worked as designed | PR #42 → AOS-WEB-001 | closed | AOS-WEB-001: acceptance retired by real Playwright tests + guardian enforcement |
| [[LES-010]] | 2026-07-05 | process | Moving code across a package boundary must carry its test-enforcement with it — extract to `packages/aos_core/` without extending the guardian and the "code changed without tests" BLOCK goes blind to the moved code | AOS-CORE-001 | closed | AOS-CORE-001: `missing-core-tests` guardian rule + tests added in the same change set |
| [[LES-011]] | 2026-07-05 | review-remediation | compose-smoke builds an explicit service list — a new compose service must be added to its build/up steps or it ships CI-unverified | AOS-SCHED-001 review, self-caught | closed | ci.yml fix; build-all hardening noted |

## Update rule

Add the row and page in the same change set as the work that surfaced the event (or the next reconciliation PR for post-merge events). Check this index before adding: if the event repeats an existing lesson, cite it there instead of duplicating.
