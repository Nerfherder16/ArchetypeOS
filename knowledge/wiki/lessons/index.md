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
| [[LES-012]] | 2026-07-06 | ci-failure | Local ruff must use CI's exact scope (`apps/api`, not `apps/api/app`) or alembic migration lint errors slip through | AOS-KNOW-002 (PR #51) CI | closed | Migration fix + Orchestrator lint-scope-parity practice |
| [[LES-013]] | 2026-07-06 | self-found-defect | File-count `language_mix` misreads a library's primary language on config/docs-heavy repos (pydantic-ai: Python only 28% by file count) | AOS-21 reality test | closed | AOS-ARCH-SEMANTICS-001: source-classified language weighting + `primary_language`/`language_classes` in the scan summary |
| [[LES-014]] | 2026-07-06 | self-found-defect | Architecture graph is directory-tree-only (`contains` edges); dependency/manifest-derived edges are the missing signal on a real monorepo | AOS-21 reality test | open | compose/service edges shipped (AOS-ARCH-SEMANTICS-001); manifest/import edges remain |
| [[LES-015]] | 2026-07-06 | self-found-defect | Playwright dynamic-count assertions must use retrying web-first matchers, not one-shot `await locator.count()` (races async refetch) | AOS-21 verification, self-caught | closed | knowledge.spec.ts rewritten to presence/absence assertions |
| [[LES-016]] | 2026-07-06 | self-found-defect | Manifest/ecosystem detection stops at python/node/go; `.csproj` (.NET) missed on a polyglot repo — likely Java/Rust too | AOS-21 diverse batch | open | AOS-DISTILL-003 added framework detection from manifest BODIES (python/node/go deps → curated `frameworks`); still open for the dotnet/jvm/cargo ecosystem breadth (`.csproj`/`pom.xml`/`Cargo.toml`) not yet covered |
| [[LES-017]] | 2026-07-06 | self-found-defect | `SECRET_LIKE_FILENAME` flags legitimate test-cert fixtures (gin `testdata/*.pem`); signal lacks test-fixture-path context | AOS-21 diverse batch | open | Test-fixture-path awareness for the secret heuristic |
| [[LES-018]] | 2026-07-06 | self-found-defect | Real `claude -p --output-format json` wraps agent JSON in a Markdown fence (3 of 4 agents); a bare `json.loads` drops it to the prose fallback (findings/confidence lost) | AOS-COUNCIL-PHASEA first real Council run | closed | `_loads_tolerant` fence/prose stripping + 4 parser tests, same change set |
| [[LES-019]] | 2026-07-06 | design-insight | A structural repo scan is the wrong evidence class for a technology-*adoption* question; the Council rightly abstained and requested research/decision evidence (Constitution working) | AOS-COUNCIL-PHASEA first real Council run | open | Phase C decision loop feeds the Council a research/decision corpus, not a target-repo scan |
| [[LES-020]] | 2026-07-06 | guardian-catch | A core (`aos_core`) change needs a test in the same change set even for a small infra tweak (a sqlite PRAGMA listener); an e2e that covers it does not satisfy `missing-core-tests` | AOS-COUNCIL-PHASEC2B guardian BLOCK | closed | `test_database_pragma.py` pins `_is_file_sqlite` in the same change set |
| [[LES-021]] | 2026-07-06 | self-found-defect | `ClaudeCodeProvider` shells `claude -p` in the repo cwd, so an agent inherits `CLAUDE.md`/filesystem and reasoned about ArchetypeOS instead of the target repo — provider must run isolated (empty cwd, no ambient context) | free-llm-api-resources reality test | closed | AOS-LLM-ISOLATION-001: empty-temp-cwd + `--disallowedTools` + `--strict-mcp-config`; regression test + live-validated |
| [[LES-022]] | 2026-07-06 | self-found-defect | Distillation's deterministic summary floor emitted badge/analogy noise as `DNA.purpose` AND `DNA.frameworks` was never populated — the Transfer Engine was starved (kubernetes missed on "container orchestration"; gin ranked 3rd on "HTTP routing"; pydantic-ai false-matched `web` via a FastAPI analogy) | first end-to-end reality test 2026-07-06 | closed | AOS-DISTILL-003: cleaned summary floor (badge/heading strip + declarative-sentence preference + honest fallback) + framework detection from manifest bodies + `run_scan` stamps `DNA.frameworks`; `scripts/reality_test_distillation.py` regression gate |
| [[LES-023]] | 2026-07-06 | design-insight | A Jaccard over the candidate's whole vocabulary collapses transfer confidence to near-zero even for the correct #1 match (union dominated by the candidate's own tokens); a retrieval score should be *need coverage* — the fraction of the query satisfied | full end-to-end reality test 2026-07-06 | closed | AOS-TRANSFER-002: `score_relevance` = `\|covered\| / \|need\|` (tech-only matches counted; tie-break on tech-match count); confidences became meaningful (k8s 0.333, gin 0.800) with rankings intact/improved |

## Update rule

Add the row and page in the same change set as the work that surfaced the event (or the next reconciliation PR for post-merge events). Check this index before adding: if the event repeats an existing lesson, cite it there instead of duplicating.
