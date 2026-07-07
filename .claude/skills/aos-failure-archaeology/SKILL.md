---
name: aos-failure-archaeology
description: Use when a failure, PR Guardian BLOCK, CI error, or design idea in ArchetypeOS looks familiar and may already be a settled battle. Triggers, checking whether a LES lesson is open or closed, being tempted to retry a rejected approach (Jaccard relevance scoring, one-shot Playwright counts, default-port down-tests, pinned open lesson IDs, worktrees for shared-log conflicts), asking why dead branches like stop, really-stop, backup/pr9-*, or codex/* exist, or hunting for revert history.
---

# AOS Failure Archaeology

## 1. Overview

This skill is the settled-battles chronicle of ArchetypeOS: every recorded lesson (LES-001 through LES-031 plus the laptop-band LES-L01/LES-L02, 33 pages as of 2026-07-07), the major investigations grouped by workstream, the dead-branch graveyard, and the explicit DO NOT RETRY list. Its purpose is to stop anyone from re-fighting a closed battle or re-proposing a rejected approach.

Terms used once, defined here:

- **Lessons vault**: `knowledge/wiki/lessons/` (one page per lesson plus `index.md`), the learning-feedback registry mandated by RFC-0004 (`docs/rfc/RFC-0004-Learning-Feedback-Loop.md`).
- **PR Guardian**: the deterministic review gate (`tools/pr_guardian.py`) with verdicts PASS, PASS_WITH_WARNINGS, BLOCK.
- **Index-wins rule**: `knowledge/wiki/lessons/index.md` states "On conflict between a lesson page and this table, this table wins." Always read status from the index table, not the page's `## Status` header.
- **Tandem sessions**: two concurrent Orchestrator sessions (laptop and cloud/remote) working the same repo on different branches.

This skill is the archive. For "something is broken right now, what do I check first", use the operational front door: **aos-debugging-playbook**. For how to author a new lesson, use **aos-docs-and-lessons**.

## 2. When to use / When NOT to use

Use this skill when:

- A symptom, BLOCK, or CI failure feels like it happened before and you want the prior root cause and prescription.
- You are about to propose an approach and need to check it was not already rejected (see the DO NOT RETRY list, section 7).
- You need the status or evidence trail of a specific LES ID.
- You are wondering what a strange remote branch (`stop`, `tmp-noop`, `backup/pr9-*`, `codex/*`) is and whether it holds recoverable work.
- You are writing a new lesson and must check for an existing row first (the index Update rule requires it).

Do NOT use this skill when:

- You need live triage of an active failure: use **aos-debugging-playbook**.
- You need lesson or RFC authoring mechanics and house style: use **aos-docs-and-lessons**.
- You need the change-gating rules themselves (Guardian rules, merge gate): use **aos-change-control**.
- You need current scanner heuristics or transfer scoring as they exist today: use **aos-scanner-dna-reference** and **aos-knowledge-transfer-reference** (this skill records how they got that way).
- You are running the LES-019 evidence campaign: use **aos-evidence-loop-campaign**.

## 3. Complete lesson index

Status column is taken from `knowledge/wiki/lessons/index.md` (the index-wins rule) as of 2026-07-07. Open lessons as of 2026-07-07: **LES-019** and **LES-029**. LES-L01 and LES-L02 landed via the AOS-SELFHEAL-001 branch, merged as PR #80.

| ID | Category | Symptom | Root cause | Prescription | Status | Evidence |
|----|----------|---------|------------|--------------|--------|----------|
| LES-001 | guardian-catch | Guardian BLOCK `possible-secret` on test fixtures | Credential-shaped marker strings; the diff cannot prove they are fake | Use lexically un-secret-like markers (`fake-...-do-not-leak`); fix the string, never the rule | closed | PRs #33, #36 prep |
| LES-002 | guardian-catch | BLOCK `invalid-verification-level` on `Level 4 (local)` | Metadata literals are machine-parsed enums; annotation appended to the literal | Exact literals `Level 0`..`Level 5`; qualifiers go in the Method text | closed | AOS-DEC-001 prep |
| LES-003 | guardian-catch | Double BLOCK on the Alpha Review PR (metadata + capability map) | Fields written as bold bullets, not `Field: value` lines; new doc without a capability-map update | Plain `Field: value` at line start; doc-adding PRs touch `docs/CAPABILITY_MAP.md` | closed | PR #37 first pass |
| LES-004 | review-remediation | Degraded-Redis test green in CI, red on machines running a local Redis | Test relied on default port 6379 being refused | Pin a guaranteed-dead resource (port 9999, invalid host) for down-state tests | closed | PR #39 review |
| LES-005 | self-found-defect | `GET /health` returned 500 exactly when Redis was absent | Probe exception propagated instead of degrading | Guard each probe independently; report partial failure in the body | closed | Alpha Review, fix PR #39 |
| LES-006 | guardian-gap | `MISSING_TESTS` WARN for `apps/web` fired on every UI PR, never actioned | A warning with no escalation path is functionally invisible | Accepted-warnings registry with dated expiry that escalates to BLOCK | closed | PRs #27, #34, #36; AOS-PRG-003 |
| LES-007 | process | Doc staleness caught only by human review (the one Phase 10 "NO by machine") | v0.1 recorded that docs exist, not whether they are current | Deterministic staleness detection from git cross-checks | closed | Alpha Review Q2; consumed by LES-024/AOS-20 |
| LES-008 | review-remediation | A plausible but fabricated UUID nearly entered the Board ID Registry | Opaque identifier reconstructed from memory | Copy IDs from tool output or fetch at write time; if not in view, fetch or omit | closed | PR #42 prep, self-caught |
| LES-009 | process | Dated warning acceptance (`review_by: 2026-08-01`) drove AOS-WEB-001 on schedule | Positive finding: the expiry is a scheduling commitment | Treat every `review_by` as a real deadline; honor or consciously renew | closed | PR #42 to AOS-WEB-001 |
| LES-010 | process | Guardian went blind to code extracted into `packages/aos_core/` | Test enforcement is path-keyed; gates do not follow moved code | Extend gates in the same change set as any relocation (`missing-core-tests` rule) | closed | AOS-CORE-001 |
| LES-011 | review-remediation | New `scheduler` compose service would have shipped CI-unverified | compose-smoke builds an explicit service list; `compose config` validates but does not build | Add every new compose service to both the build and up steps in ci.yml | closed | AOS-SCHED-001 review |
| LES-012 | ci-failure | CI ruff failed F401 on a migration; local ruff was green | Local scope `apps/api/app` narrower than CI's `apps/api` (which lints `alembic/`) | Lint at CI's exact scope (`ruff check apps/api` and `ruff check apps/worker`; `apps/api` includes `alembic/`); widening locally to `packages/aos_core` and `tools` is a stricter superset, not the CI scope. CI lint scopes home: aos-debugging-playbook 5.2 | closed | PR #51, run 28760110922 |
| LES-013 | self-found-defect | pydantic-ai read as 28% Python by file count (YAML ranked first) | `language_mix` counts files; config/docs/CI dominate real repos | Source-classified language weighting; `primary_language` from top source language | closed | AOS-21; AOS-ARCH-SEMANTICS-001 |
| LES-014 | self-found-defect | Real monorepo produced 14 architecture edges, all `contains` | Graph was directory-tree only; no dependency or manifest edges | Compose/service edges plus manifest-derived `depends_on` edges | closed (import-graph edges are a separate follow-up) | AOS-ARCH-SEMANTICS-001 + AOS-ARCH-EDGES-001 (PR #78) |
| LES-015 | self-found-defect | e2e filter assertion failed (`14 < 14`) | One-shot `await locator.count()` raced the async refetch | Retrying web-first matchers; prove filters by presence/absence of specific rows | closed | AOS-21, self-caught pre-CI |
| LES-016 | self-found-defect | `Worker.csproj` missed on a polyglot repo; C# had no ecosystem record | Manifest detection stopped at python/node/go | JVM and .NET manifests added; `dotnet`/`jvm` in `ECOSYSTEM_KINDS` | closed | AOS-SCAN-PRECISION-001 |
| LES-017 | self-found-defect | 71 `SECRET_LIKE_FILENAME` warnings on kubernetes test certs | Signal had no test-fixture-path context | Downgrade to `severity="info"` under fixture dirs; Guardian secret-block intentionally unchanged | closed | AOS-SCAN-PRECISION-001 |
| LES-018 | self-found-defect | 3 of 4 real Council agents fell to the prose fallback (findings lost, conf 0.05) | `claude -p --output-format json` wraps agent JSON in a Markdown fence; bare `json.loads` throws | `_loads_tolerant` layered recovery (as-is, strip fence, brace-slice) plus fenced-payload regression tests | closed | First real Council run |
| LES-019 | design-insight | Council abstained on the pydantic-ai adoption question (conf 0.0375) | Structural scan of the target repo is the wrong evidence class for an adoption question | Match evidence class to question class; feed the Council a research/decision corpus | **open** | First real Council run; feeds aos-evidence-loop-campaign |
| LES-020 | guardian-catch | BLOCK `missing-core-tests` on a one-line sqlite PRAGMA listener | Any `aos_core` change needs a unit test in the same set; a covering e2e does not count | Extract a testable predicate (`_is_file_sqlite`) and pin it; never override to get green | closed | AOS-COUNCIL-PHASEC2B |
| LES-021 | self-found-defect | A Council agent described ArchetypeOS instead of the target repo | `claude -p` subprocess inherited the repo cwd, `CLAUDE.md`, and filesystem | Empty temp cwd + `--disallowedTools` + `--strict-mcp-config`; output must be a pure function of the prompt | closed | AOS-LLM-ISOLATION-001, live-validated |
| LES-022 | self-found-defect | kubernetes missed on "container orchestration"; gin ranked 3rd on "HTTP routing" | Badge/analogy noise emitted as `DNA.purpose`; `DNA.frameworks` never populated | `_clean_summary` (honest deterministic floor) + framework detection from manifest bodies; `run_scan` stamps frameworks | closed | AOS-DISTILL-003; `scripts/reality_test_distillation.py` |
| LES-023 | design-insight | Correct #1 matches scored 0.01 to 0.13 confidence | Jaccard denominator dominated by the candidate's own vocabulary | Need coverage: fraction of the query satisfied, bounded 0..1 (k8s 0.333, gin 0.800) | closed | AOS-TRANSFER-002 |
| LES-024 | process | Live roadmap drift ('Foundation' vs 'v0.1 COMPLETE') caught by machine | Consumes LES-007; two-tier HARD/SOFT detector tuned to never cry wolf | `tools/doc_staleness.py` + non-blocking Guardian WARN; 12 hermetic tests | closed | AOS-20 |
| LES-025 | ci-failure | Closing LES-007 broke two test suites (api + web e2e) | Tests hardcoded LES-007 as the perpetually open lesson | Derive the open set live (`OPEN_IDS`, generic open badge); closed lessons are the only stable anchors | closed | PR #68 CI, run 28816052971 |
| LES-026 | process | PR #68 re-synced onto main 3 times (the "tandem treadmill") | Concurrent appends to shared coordination logs conflict on every merge | `.gitattributes merge=union` for the shared logs; worktrees do NOT help (they isolate working dirs, not the merge graph) | closed | AOS-20 tandem run |
| LES-027 | ci-failure | CI run "completed/failure" with 0 jobs and 0 PR check-runs | Unquoted single-line `run:` scalar containing colon-space parsed as a YAML mapping | Block-scalar `run:` steps; verify workflow YAML parses on any `.github/workflows/` edit; treat 0-jobs failure as a parse smell | closed | PR #73 CI, run 28822124340 |
| LES-028 | ci-failure | Playwright strict-mode violation: a locator matched 2 listitems | New "Agent Council" surface rendered the same entities a page-global locator assumed unique | Scope locators to the owning section, or key off a section-unique `data-testid` | closed | PR #74 CI, run 28823519364 |
| LES-029 | process | Every cycle's push became a non-fast-forward that auto-mode blocks | One env-pinned branch reused across PRs and hard-reset to `origin/main` after each merge | One fresh branch per PR off latest main; enable auto-delete head branches; resolve the Decision 2a pin | **open** | Remote session on `claude/aos-runtime-002-scanner-1egyjw` |
| LES-L01 | process | Doc-staleness WARN fired repeatedly; remediation always deferred; state docs 5 PRs behind | A detector without a remediation trigger is not self-learning (Article XX) | Encode the correction: `doc_staleness.py --fix`, post-merge hook, `/reconcile-state` skill | closed (merged via PR #80) | Operator correction; AOS-SELFHEAL-001 |
| LES-L02 | process | The second-to-merge session always got an add/add collision on the new LES file | Two concurrent sessions raced a shared sequential ID counter | Partition the namespace: laptop uses `LES-L##`, cloud keeps `LES-NNN`; never optimistic first-come on shared monotonic IDs | closed (merged via PR #80) | Operator observation; collisions on PRs #74 and #80 |
| LES-030 | ci-failure | Section-scoped e2e locator still matched 2 rows (strict-mode) | Section scoping (LES-028) is not sufficient when one section renders TWO lists of the same entity | Prefer a stable `data-testid` on the specific rows over structural `getByRole` filters | closed | PR #81 CI (run 28835431046); `data-testid="decision-row"` in `main.tsx` |
| LES-031 | ci-failure | Editing the PR body after push did not change the CI Guardian verdict | CI Guardian reads the body from the `pull_request` event payload captured at push time; re-runs re-read the stale body | Finalize the PR body BEFORE the push that trips a body-dependent gate; if edited after, re-trigger with a NEW push | closed | PR #81 CI (run 28835761476); re-triggered with a fresh commit |

## 4. Chronicle by workstream

### 4.1 Guardian hardening (LES-001, 002, 003, 006, 009, 010, 020)

- Symptom: a stream of BLOCKs and unactioned WARNs in the first sprint of Guardian operation.
- Root cause: three distinct classes. (a) True positives on sloppy inputs (fixture secrets, malformed metadata): the rule was right, the input was wrong. (b) Warnings with no escalation path (web MISSING_TESTS) that repeated silently. (c) Path-keyed enforcement going blind when code moved (`packages/aos_core` extraction).
- Evidence: PRs #27, #33, #34, #36, #37, #39, #42; AOS-PRG-003 and AOS-CORE-001 work packages.
- Status: all closed. The durable outputs are the accepted-warnings registry with dated `review_by` expiry, the `missing-core-tests` rule, and the house norm: **fix the input, never weaken the rule**. The machine-verified record: no substantive code BLOCK (tests, secrets, verification metadata, acceptance evidence) has ever been overridden; override tokens do appear in merged PR bodies as high-risk warn acknowledgments and prophylactic no-ops. The exact audit lives in **aos-change-control** section 8. Every BLOCK in the vault was resolved in code.

### 4.2 Scanner precision (LES-013, 014, 016, 017)

- Symptom: the first scans of real external repos (the AOS-21 six-repo portfolio) produced misleading DNA: Python library read as 28% Python, a monorepo graph with only `contains` edges, a .NET service invisible to `package_managers`, 71 secret warnings on kubernetes test certs.
- Root cause: heuristics built and tested only against ArchetypeOS's own repo shape; file-count weighting, directory-only edges, a three-ecosystem manifest table, and no fixture-path awareness.
- Evidence: `.archetype/portfolio/*/scan.json`, `docs/PORTFOLIO_PYDANTIC_AI.md`; fixes in AOS-ARCH-SEMANTICS-001, AOS-ARCH-EDGES-001 (PR #78), AOS-SCAN-PRECISION-001.
- Status: all four closed per the index. Source import-graph edges remain a separately scoped follow-up (not covered by any lesson row).

### 4.3 Distillation and transfer calibration (LES-022, 023)

- Symptom: the first end-to-end intelligence-loop run ranked mostly right but with garbage inputs and meaningless confidences: kubernetes dropped entirely on "container orchestration", gin ranked third on "HTTP routing", correct #1 matches scored 0.01 to 0.13.
- Root cause: two independent defects. The deterministic summary floor emitted badge markdown and analogy prose as `DNA.purpose` while `DNA.frameworks` was never stamped (right engine, wrong evidence); and `score_relevance` was a Jaccard whose union was dominated by the candidate's own vocabulary, so magnitude measured candidate verbosity, not match quality.
- Evidence: AOS-DISTILL-003 and AOS-TRANSFER-002; regression gate `scripts/reality_test_distillation.py` (manual, needs the cloned portfolio).
- Status: both closed. Post-fix reference numbers: kubernetes #1 at 0.333, gin #1 at 0.800.

### 4.4 Council evidence and provider isolation (LES-018, 019, 021)

- Symptom: the first real (non-deterministic-provider) Council runs degraded silently: three agents lost their findings to a prose fallback, and one agent described ArchetypeOS itself while reviewing an external repo.
- Root cause: the live model fences its JSON in Markdown (the hermetic test provider never does), and the shelled `claude -p` subprocess inherited the host repo's cwd, `CLAUDE.md`, and filesystem.
- Evidence: `.archetype/council/pydantic-ai-review.json`; fixes in the same change sets plus AOS-LLM-ISOLATION-001.
- Status: LES-018 and LES-021 closed. LES-019 (evidence class mismatch: a structural scan cannot answer an adoption question) remains **open** and is the seed of **aos-evidence-loop-campaign**. Note LES-019 is a design insight, not a defect: the constitutional abstention worked as intended.

### 4.5 e2e and CI discipline (LES-004, 011, 012, 015, 025, 027, 028)

- Symptom: recurring "green locally, red in CI" and "red for the wrong reason" failures across the test estate.
- Root cause: one meta-pattern in several costumes: **the local check did not exercise what CI exercises, or the assertion coupled to something mutable**. Default-port down-tests, a narrower ruff scope than CI, an explicit compose-smoke service list, one-shot Playwright counts racing refetches, a pinned "perpetually open" lesson ID, workflow YAML no local gate parses, and page-global locators broken by a new surface.
- Evidence: PR #39, AOS-SCHED-001, PR #51, AOS-21, PR #68, PR #73, PR #74 (runs cited in the table above).
- Status: all closed. The prescriptions are additive checklist items: exact-CI-scope lint, YAML-parse check on workflow edits, retrying matchers, section-scoped locators, live-derived open sets.

### 4.6 Doc-staleness loop (LES-007, 024, L01)

- Symptom: state docs (`docs/CURRENT_STATE.md`, `docs/ACTIVE_WORK.md`, `docs/RECENT_CHANGES.md`) drifted behind git reality; first invisible to machines, then detected but never remediated (5 PRs behind at worst).
- Root cause: v0.1 had no detector (LES-007); AOS-20 shipped a detector but no remediation trigger, so every WARN was deferred (LES-L01, "a smoke alarm with no sprinkler").
- Evidence: Alpha Review Q2; AOS-20 (`tools/doc_staleness.py`, HARD/SOFT tiers, Guardian WARN); operator correction 2026-07-06; AOS-SELFHEAL-001 (`--fix` reconciliation draft, post-merge hook via `scripts/install-hooks.sh`, `/reconcile-state` skill).
- Status: LES-007 and LES-024 closed on main; LES-L01 closed via AOS-SELFHEAL-001, merged as PR #80. See **aos-docs-and-lessons** for operating the reconciliation loop.

### 4.7 Tandem-session coordination (LES-008, 026, 029, L02)

- Symptom: two concurrent sessions generated merge conflicts on every cycle: shared-log conflicts (the tandem treadmill), add/add collisions on new lesson files, and non-fast-forward pushes on a reused branch.
- Root cause: shared mutable resources under concurrent authorship with no partitioning: append-only logs merged textually, a sequential LES counter claimed optimistically, one env-pinned branch name reused across PRs.
- Evidence: AOS-20 tandem run (PR #68 re-synced 3x); collisions on PRs #74 and #80; the remote session's pinned branch `claude/aos-runtime-002-scanner-1egyjw`.
- Status: LES-026 closed (union merge driver in `.gitattributes`), LES-L02 closed (namespace partition, merged via PR #80), **LES-029 open** (the Decision 2a env-pin vs fresh-branch tension is unresolved as of 2026-07-06).

## 5. Dead and abandoned branch graveyard

Verified with `git branch -a` and `git log --oneline -1 <branch>` on 2026-07-06. None of these hold unmerged work worth recovering; do not base new work on them.

| Branch(es) | Last commit | Explanation |
|------------|-------------|-------------|
| `origin/stop`, `origin/really-stop`, `origin/stop3`, `origin/noop-conflict`, `origin/tmp-check`, `origin/tmp-noop`, `origin/test-branch-do-not-use`, `origin/do-not-use-final`, `origin/__ignore` | All nine point at the identical commit `bfe6f63` (merge of PR #11, 2026-07-04) with zero unique commits | Workflow-debug artifacts from the 2026-07-04 session-tooling debugging. Confirmed: no content of their own, pure pointer noise. Safe to ignore |
| `origin/backup/pr9-before-conflict-fix-69003f3`, `origin/backup/pr9-operating-loop-roadmap-69003f3` | Both at `69003f3` (2026-07-04) | Safety snapshots taken before a PR #9 conflict fix; the SHA is embedded in the branch name. Superseded by the merged history |
| `origin/docs/operating-loop-roadmap`, `-recovered`, `-recovered2` | `bfe6f63` / `52bd4c3` / `e2c4f25` (2026-07-04) | The PR #9 recovery saga: successive attempts to reconstruct the operating-loop roadmap doc. Final content merged via other PRs |
| `origin/codex/repository-registry-mvp`, `origin/codex/repository-registry-mvp-backup-d811534`, `origin/codex/verification-protocol` | 2026-07-04 | Early Codex-agent-authored branches from day one; their content landed through the normal PR flow and the heads were never deleted |
| `origin/ci/*`, `origin/docs/*` (remaining), `origin/build/v0.1-runtime-foundation`, `origin/claude/archetypeos-architecture-review-36n2kd` | 2026-07-04 | Merged v0.1-era feature branches whose remote heads linger because auto-delete-on-merge is not enabled (an explicit LES-029 follow-up) |
| `origin/claude/aos-runtime-002-scanner-1egyjw` | 2026-07-06 | NOT dead: the remote session's env-pinned reused branch, the live subject of open lesson LES-029. Do not treat its head as a feature branch |
| `origin/laptop/*` | 2026-07-06 | Merged (or in-review) laptop-session feature branches; heads persist for the same auto-delete reason |

## 6. The no-revert record

Verified on 2026-07-06: `git log --all --oneline -i --grep=revert` returns **zero commits** across the entire history (origin/main alone has 352 commits). The repo has never reverted; it uses a **commit-and-fix pattern**: defects ship forward as targeted fix commits in the next change set (example: `67a8d75 fix(ci): ci.yml YAML parse error in the Embedder tests job (LES-027)`), each paired with a lesson per RFC-0004.

Read this correctly: it is NOT evidence of an absence of failures (the vault above documents 31 of them). It reflects the head-SHA-pinned manual merge gate plus Guardian keeping broken states off main long enough that roll-forward was always cheaper than roll-back. If you ever believe a revert is genuinely needed, that is an unprecedented event: escalate to the operator, do not just do it.

## 7. DO NOT RETRY: explicitly rejected approaches

These were tried or seriously considered, and rejected with recorded evidence. Re-proposing one without new evidence re-fights a settled battle.

| Rejected approach | Why it fails | Lesson | What to do instead |
|-------------------|--------------|--------|--------------------|
| Raw Jaccard for transfer relevance/confidence | Union dominated by the candidate's own vocabulary; correct #1 matches score near zero; penalizes descriptive distillations | LES-023 | Need coverage (fraction of the query satisfied, 0..1); keep any future embeddings-tier confidence coverage-like, never a raw similarity |
| One-shot `await locator.count()` for dynamic lists | Races the async refetch; reads the pre-filter list | LES-015 | Retrying web-first matchers (`toHaveCount`, `toBeVisible`); assert presence/absence of specific rows |
| Tests asserting a service is down via its default port | True in CI, false on any machine actually running that service | LES-004 | Pin a guaranteed-dead resource (reserved port such as 9999, invalid host) |
| Hardcoding a specific open lesson ID in tests | Lesson statuses flip when a loop consumes them; that is the whole point of the loop | LES-025 | Derive the open set live (`OPEN_IDS`); use closed lessons as stable anchors |
| Worktrees to fix shared-log merge conflicts | Worktrees isolate working directories, not the merge graph; the sessions were already on separate branches | LES-026 | `.gitattributes merge=union` for the shared additive logs; single-writer protocol for status flips |
| (Bonus) LoC-based language weighting | Rejected during LES-013: the scanner does not read source bodies; classification fixes the misread without new I/O | LES-013 | Source-class weighting (`LANGUAGE_CLASS`) |
| (Bonus) Moving the live board to Plane, or per-item fragment files, for coordination conflicts | Deferred behind YAGNI; Plane also trades against local-first and git-as-source-of-truth, so it is an RFC-level decision | LES-026 | Union driver first; escalate only if residual conflicts prove painful, via RFC |

Also settled, from the other direction (approaches that must NOT be weakened): the Guardian secret-pattern rule (LES-001, fix the string), `missing-core-tests` strictness (LES-020, add the test, never override), and the scanner-vs-guardian split in LES-017 (scanner signal downgraded for fixtures, Guardian block intentionally untouched). Never suggest bypassing PR Guardian, the manual merge gate, or the RFC process.

## 8. Task tier guide

Tier labels are operator guidance and candidate status; **aos-model-routing** is the routing home.

| Task in this skill's scope | Tier |
|----------------------------|------|
| Look up a LES ID's status, symptom, or evidence | Haiku |
| Check whether a proposed approach appears in the DO NOT RETRY list | Haiku |
| Re-run the provenance verification commands (section 10) | Haiku |
| Map a new symptom onto a workstream and its prior root causes | Sonnet |
| Draft a new lesson page and index row (with aos-docs-and-lessons) | Sonnet |
| Decide a battle is NOT settled and argue for reopening a closed lesson | Opus |
| Challenge a DO NOT RETRY entry with new evidence (RFC-level) | Opus |

## 9. Common mistakes

1. **Trusting a lesson page's `## Status` header over the index.** LES-014, LES-016, and LES-017 pages still carry `open` in their Status header while the index (and the page's own bottom Status line) say closed. The index wins, by its own stated rule.
2. **Assuming today's open set is stable.** LES-025 exists because tests pinned an open lesson. Always re-derive: `grep '| open |' knowledge/wiki/lessons/index.md`.
3. **Reconstructing PR numbers, run IDs, or LES IDs from memory.** That is LES-008 itself. Copy from tool output or the live index.
4. **Duplicating a lesson.** The index Update rule requires checking for an existing row first; repeats get cited on the existing row, not a new one.
5. **Reading the no-revert record as "nothing ever broke".** The lesson vault (33 pages as of 2026-07-07, growing) says otherwise; it means roll-forward under the merge gate, not perfection.
6. **Mining dead branches for work.** The graveyard branches (section 5) hold zero unique unmerged content except the live pinned branch, which is not a feature branch.
7. **Allocating the next sequential `LES-NNN` from a laptop/second session.** LES-L02 partitioned the namespace: laptop sessions use `LES-L##` (convention merged via PR #80, recorded in the index's ID-allocation section).

## 10. Provenance and maintenance

- Written: 2026-07-06, on branch `laptop/aos-selfheal-doc-loop` (HEAD = AOS-SELFHEAL-001, since merged as PR #80; LES-L01/LES-L02 and their index rows are on live main).
- Derived from: `knowledge/wiki/lessons/index.md`, `knowledge/wiki/lessons/LES-001.md` through `LES-029.md`, `LES-L01.md`, `LES-L02.md`, `git branch -a`, `git log` (origin/main and all refs), `docs/rfc/RFC-0004-Learning-Feedback-Loop.md` references inside the vault.
- Override record: machine-verified from merged PR bodies via `gh` (not from commit messages alone). No substantive code BLOCK has ever been overridden; the audited per-PR breakdown, including the token-bearing PR bodies, lives in **aos-change-control** section 8.

Re-verification commands (run from the repo root; all read-only). Kept in a code block, not a table, because several contain literal pipe characters, which break markdown table rows (the LES-027 sibling failure):

```bash
# Which lessons are open (status column of the index)
grep -n '| open |' knowledge/wiki/lessons/index.md

# Total lesson count / new IDs
ls knowledge/wiki/lessons/ | grep -c '^LES-'

# LES-L01/L02 merged to main (empty output = stale local origin/main ref; fetch first. Merged via PR #80)
git ls-tree origin/main knowledge/wiki/lessons/ | grep 'LES-L'

# No-revert record still holds (expect empty output)
git log --all --oneline -i --grep=revert

# Branch graveyard unchanged
git branch -a
git log --oneline -1 origin/stop   # repeat per branch of interest

# Workflow-debug branches still content-free (expect all bfe6f63...)
for b in stop really-stop stop3 noop-conflict tmp-check tmp-noop; do git rev-parse "origin/$b"; done

# LES-029 still open / branch tension resolved
grep -n 'LES-029' knowledge/wiki/lessons/index.md

# AOS-SELFHEAL-001 merge status (merged via PR #80; empty output = stale local origin/main ref, fetch first)
git log origin/main --oneline --grep='AOS-SELFHEAL-001'

# Index-wins rule still stated
grep -n 'this table wins' knowledge/wiki/lessons/index.md
```

When a lesson's status flips or a new LES lands, update the index table (section 3), the affected workstream entry (section 4), and, if an approach was newly rejected, the DO NOT RETRY list (section 7), in the same change set.
