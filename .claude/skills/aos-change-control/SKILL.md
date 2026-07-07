---
name: aos-change-control
description: Use when classifying an ArchetypeOS change or deciding the gate and override policy, when PR Guardian (tools/pr_guardian.py) returns BLOCK or PASS_WITH_WARNINGS and you need the meaning of a finding, when findings such as missing-verification-metadata, missing-docs, capability-map-not-updated, or accepted-warning-expired fire, when a PR_GUARDIAN_OVERRIDE_* token is being considered, when an RFC or .archetype/work spec is needed, or when posting the manual merge gate. (Writing the tests or evidence that clears a finding is aos-validation-and-qa; running the tools is aos-diagnostics-and-tooling.)
---

# AOS Change Control

## 1. Overview

Every change to ArchetypeOS passes through a deterministic gate stack before it reaches `main`:

1. A work package spec in `.archetype/work/<TASK-ID>.md` (RFC-0003) defines scope before code exists.
2. PR Guardian (`tools/pr_guardian.py`), a deterministic, no-LLM, read-only script, checks the diff and the PR body and returns PASS, PASS_WITH_WARNINGS, or BLOCK.
3. The local gate `scripts/pre_pr_guardian.sh` runs Guardian plus compile, tests, web build, and compose validation before a PR is opened.
4. GitHub Actions CI runs the same Guardian plus the full job matrix.
5. The head-SHA-pinned Manual Merge Gate: a human or babysitting agent posts a verification comment pinned to the exact head SHA before the human operator merges. This exists because the private free-plan repo cannot enforce required status checks (docs/BRANCH_PROTECTION.md).

Two doctrines sit on top of the mechanics:

- Builder is not verifier: the agent that wrote the code never certifies it. The Orchestrator independently re-runs the suite and reads the diff (docs/ORCHESTRATOR_PLAYBOOK.md, Role contract).
- Guardian BLOCKs are fixed in code, not overridden. The override tokens exist as audit markers, but the practical record is that substantive blocks always get fixed (see section 8 for the exact, verified record).

Definitions used below: "Guardian" means `tools/pr_guardian.py`; "state docs" means docs/CURRENT_STATE.md, docs/ACTIVE_WORK.md, docs/RECENT_CHANGES.md; "lesson" means a page under `knowledge/wiki/lessons/` per RFC-0004.

## 2. When to use / When NOT to use

Use this skill when:

- Classifying a change (docs-only vs code vs aos_core vs governance) and deciding which gates apply.
- Guardian returned BLOCK or PASS_WITH_WARNINGS and you need the meaning of a finding code.
- Writing or reviewing a PR body (verification metadata, Acceptance Evidence).
- Deciding whether an RFC or a work package spec is required.
- Preparing or checking the Manual Merge Gate comment.
- Anyone proposes using an override token.

Do NOT use this skill for:

- Diagnosing why tests or services fail: see aos-debugging-playbook.
- Authoring the lesson page or reconciling state docs after a merge: see aos-docs-and-lessons.
- Deciding what counts as sufficient test evidence or adding tests: see aos-validation-and-qa.
- Running the environment or CI locally end to end: see aos-build-run-and-operate.
- The history of why each rule exists in narrative form: see aos-failure-archaeology.
- Choosing which model tier executes a task: see aos-model-routing (the table in section 13 is scoped guidance only).

## 3. Change classification and required gates

Guardian classifies by path prefix (constants in tools/pr_guardian.py):

- Code prefixes: `apps/api/app/`, `apps/worker/app/`, `apps/web/src/`
- Test prefixes: `apps/api/tests/`, `apps/worker/tests/` (web: `apps/web/e2e/`; core: `packages/aos_core/tests/` or `apps/api/tests/`)
- Doc prefixes: `docs/`, `README.md`, `CLAUDE.md`, `.archetype/`

| Change class | Example paths | Gates that fire on top of the always-on set |
|---|---|---|
| Docs-only | `docs/*.md`, `.archetype/work/*.md` | `capability-map-not-updated` BLOCK if a new non-allowlisted `docs/*.md` is added without touching `docs/CAPABILITY_MAP.md` |
| App code | `apps/api/app/`, `apps/worker/app/`, `apps/web/src/` | test-coverage BLOCKs (api, worker) or WARN (web), `missing-docs` BLOCK, Acceptance Evidence BLOCKs |
| aos_core | `packages/aos_core/` | `missing-core-tests` BLOCK unless tests change under `packages/aos_core/tests/` or `apps/api/tests/`. Note: core-only changes do NOT trigger `missing-docs` or the Acceptance Evidence check (those key on the code prefixes only) |
| Infra / high-risk | `docker-compose.yml`, `.env.example`, `.github/workflows/`, any path containing `auth` or `secret` | `high-risk-files` WARN; compose and workflow changes also count as code for `missing-docs` |
| Governance / Guardian | `tools/pr_guardian.py` | `guardian-change-without-lesson` BLOCK unless a `knowledge/wiki/lessons/` path also changes. Governance changes also require an RFC (docs/RFC_PROCESS.md) |

Always-on for every PR regardless of class: verification metadata BLOCKs, secret-pattern BLOCK, runtime-junk BLOCK, required-foundation-files BLOCK, scanner-informed checks, accepted-warnings post-processing, doc-staleness WARNs.

## 4. PR Guardian verdict anatomy

Run from the repo root (relative paths break from subdirectories):

```bash
cd /home/nerfherder/Dev/ArchetypeOS
git fetch origin main
python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file /tmp/pr_body.md
```

Optional: `--scan-report <path>` supplies a scanner JSON report; without it Guardian imports `aos_core.repository_scanner` from `packages/aos_core` and scans the working tree itself (graceful degradation to skipping scanner checks if that fails).

Output is a `# PR Guardian Report` with the changed-file list, then a verdict:

| Verdict | Meaning | Exit code |
|---|---|---|
| PASS | No findings at all | 0 |
| PASS_WITH_WARNINGS | Only warn-severity findings | 0 |
| BLOCK | At least one block-severity finding | 1 |

Each finding prints as `- [BLOCK|WARN] <code>: <message>`. The `/guardian` Claude Code command (`.claude/commands/guardian.md`) wraps this; pass `full` for the complete local gate.

## 5. Every rule as implemented (codes exactly as coded)

Source of truth: `tools/pr_guardian.py` at 653 lines, verified as of 2026-07-06 (identical on live main and HEAD by blob SHA).

### Blocking rules

| Code | Fires when | Override token |
|---|---|---|
| `missing-required-file` | Any of the 12 REQUIRED_FILES foundation files is absent from the working tree | none |
| `possible-secret` | An added diff line matches a secret regex (AKIA keys, `api_key/secret/token/password = <20+ chars>`, PEM private key headers) | none |
| `runtime-junk` | A changed path contains `__pycache__`, `.pytest_cache`, `node_modules`, `.venv`, `dist/`, or ends `.pyc` | none |
| `missing-api-tests` | `apps/api/app/` changed without `apps/api/tests/` changes | `PR_GUARDIAN_OVERRIDE_TESTS` |
| `missing-worker-tests` | `apps/worker/app/` changed without `apps/worker/tests/` changes | `PR_GUARDIAN_OVERRIDE_TESTS` |
| `missing-core-tests` | `packages/aos_core/` changed without `packages/aos_core/tests/` or `apps/api/tests/` changes (LES-020: even a one-line infra tweak needs a unit test) | `PR_GUARDIAN_OVERRIDE_TESTS` |
| `missing-docs` | Code prefixes, `docker-compose.yml`, or `.github/workflows/` changed without any doc-prefix change | `PR_GUARDIAN_OVERRIDE_DOCS` |
| `capability-map-not-updated` | A new `docs/*.md` was added (git status A, outside the governance allowlist and `docs/rfc/`) without touching `docs/CAPABILITY_MAP.md` | `PR_GUARDIAN_OVERRIDE_CAPABILITY_MAP` |
| `missing-acceptance-evidence` | Code prefixes changed and the PR body has no `## Acceptance Evidence` heading | `PR_GUARDIAN_OVERRIDE_ACCEPTANCE` |
| `empty-acceptance-evidence` | The heading exists but no bullet under it contains `evidence:` (case-insensitive) | `PR_GUARDIAN_OVERRIDE_ACCEPTANCE` |
| `missing-verification-metadata` | Any of the six required `Field: value` lines is absent (section 6) | none (by design) |
| `invalid-verification-status` | Status is not one of the five allowed literals | none |
| `verification-not-mergeable` | Status is `Verification unavailable` or `Verification blocked` | none |
| `invalid-verification-level` | Level is not exactly `Level 0` through `Level 5` | none |
| `scanner-secret-path` | A changed path matches a scanner `SECRET_LIKE_FILENAME` risk signal | `PR_GUARDIAN_OVERRIDE_SCANNER` |
| `scanner-env-committed` | A changed path matches a scanner `ENV_FILE_PRESENT` risk signal (a real `.env` is being committed) | `PR_GUARDIAN_OVERRIDE_SCANNER` |
| `guardian-change-without-lesson` | `tools/pr_guardian.py` changed with no `knowledge/wiki/lessons/` path in the diff (RFC-0004: rules evolve only from logged lessons) | `PR_GUARDIAN_OVERRIDE_LESSON` (for non-rule refactors) |
| `override-without-lesson-citation` | The body contains any `PR_GUARDIAN_OVERRIDE_` string but no `LES-<n>` reference | none |
| `accepted-warning-expired` | A warn finding matches an accepted-warnings entry whose `review_by` date has passed (section 7) | renew the registry entry or fix the gap |

### Warning rules

| Code | Fires when | Override token |
|---|---|---|
| `web-tests-not-enforced` | `apps/web/src/` changed without `apps/web/e2e/` changes | `PR_GUARDIAN_OVERRIDE_WEB_TESTS` |
| `high-risk-files` | `docker-compose.yml`, `.env.example`, `.github/workflows/`, or any path containing `auth` or `secret` changed | `PR_GUARDIAN_OVERRIDE_HIGH_RISK_ACK` (this token's designed purpose is acknowledging the risk) |
| `verification-pending` | Status is `Verification pending` (PR may stay open, must not merge until a stronger status is recorded) | none |
| `weak-verification-metadata` | Method, Evidence, Limitations, or Required Next Verifier is empty, `n/a`, `none`, `tbd`, or `todo` | none |
| `scanner-missing-tests` | Scanner reports `MISSING_TESTS` while the PR adds app code (`.py/.ts/.tsx/.js/.jsx` under code prefixes) | `PR_GUARDIAN_OVERRIDE_SCANNER` |
| `scanner-new-ecosystem` | Scanner reports `MULTIPLE_ECOSYSTEMS` and the PR touches a package manifest (pyproject.toml, package.json, Cargo.toml, go.mod, lockfiles, etc.) | `PR_GUARDIAN_OVERRIDE_SCANNER` |
| `doc-staleness:<signal>` | The doc-staleness detector (`tools/doc_staleness.py`, AOS-20) reports a HARD drift signal between state docs and git reality. Advisory only, never blocks, fails open | none needed |

Gotcha, verified in source: `has_override` is a plain substring test over the whole PR body. Writing a full token anywhere, including inside prose, backticks, or an HTML comment, functionally activates the override AND triggers `override-without-lesson-citation` if no `LES-<n>` appears. When discussing tokens in a PR body, split the string (write `PR_GUARDIAN_OVERRIDE_` and the suffix separately) or cite a lesson.

## 6. Verification metadata: the exact format

Every PR body must contain these six lines, as plain `Field: value` lines starting at column 0. Markdown wrappers do not parse: `- **Verification Status:** Verified` is invisible to the `^Field:` regex.

```text
Verification Status: Verified
Verification Level: Level 4
Verification Method: <how it was verified>
Evidence: <commands run, tests, CI links>
Limitations: <what was not verified>
Required Next Verifier: <who or what verifies next>
```

Allowed statuses (exact literals): `Verified`, `Verified with warnings`, `Verification pending`, `Verification unavailable`, `Verification blocked`. Allowed levels (exact literals): `Level 0` to `Level 5` (0 Static Reasoning, 1 Repository Verification, 2 Local Execution, 3 GitHub CI Verification, 4 Runtime Verification, 5 Human Verification; docs/VERIFICATION_PROTOCOL.md).

Incident history, why this is strict:

- LES-002: a body declared `Verification Level: Level 4 (local)`. BLOCK `invalid-verification-level`. Qualifiers belong in the Method text, never appended to the enum literal.
- LES-003: PR #37 wrote the fields as `- **Field:** value` bullets. Double BLOCK (`missing-verification-metadata` plus `capability-map-not-updated`). Both were fixed, not overridden; the BLOCK message now states the plain-line requirement.

There is no bypass marker for verification metadata. If verification cannot be completed, say so with `Verification pending` (open but unmergeable) or the two blocking statuses.

## 7. Accepted-warnings registry

File: `.archetype/guardian/accepted_warnings.json`, a JSON list of entries:

```json
{"code": "web-tests-not-enforced", "lesson": "LES-006", "rationale": "why accepted", "review_by": "YYYY-MM-DD"}
```

After all findings are collected, each warn-severity finding whose code matches an entry is post-processed:

- Today on or before `review_by`: stays a WARN, message annotated `[accepted per <lesson> until <review_by>: <rationale>]`. Acceptance is cited and dated, never silent.
- Today after `review_by`: escalates to BLOCK `accepted-warning-expired`, forcing a re-decision (renew with a new date, or fix the gap).

Only warns are eligible; blocks are never softened by the registry. A missing or invalid registry degrades to an empty list with a stdout note.

Incident history: LES-006 (the same web `MISSING_TESTS` warning fired on PRs #27, #34, #36 without ever producing a work item; a warning that never changes behavior is invisible) motivated the mechanism. LES-009 validated it: the dated `review_by: 2026-08-01` acceptance acted as a forcing function that scheduled AOS-WEB-001 (the Playwright suite), after which the entry was retired. The registry is `[]` as of 2026-07-06: every acceptance has been resolved in code, none renewed.

## 8. Override tokens: mechanism and the real record

Mechanism: eight documented tokens (docs/PR_GUARDIAN.md Override Protocol): `PR_GUARDIAN_OVERRIDE_TESTS`, `_WEB_TESTS`, `_DOCS`, `_CAPABILITY_MAP`, `_HIGH_RISK_ACK`, `_ACCEPTANCE`, `_SCANNER`, `_LESSON`. Any token requires rationale in the body, and since PR #41 any token requires a `LES-<n>` citation (`override-without-lesson-citation`).

The unwritten rule: substantive BLOCKs are never overridden; they are fixed in code. The verified record as of 2026-07-06 (75 merged PRs, PR numbers issued through #81, all merged; audited live via `gh` against merged PR bodies):

- Zero overrides of any test-coverage, secret, verification-metadata, or acceptance-evidence BLOCK on a code PR, ever. LES-003 (metadata plus capability map, PR #37) and LES-020 (`missing-core-tests` on a one-line core change) explicitly record BLOCKs being fixed, not overridden.
- Override tokens appear in 16 merged PR bodies (#2, #4, #5, #6, #7, #8, #10, #11, #12, #13, #21, #32, #33, #41, #70, #81). Breakdown from the bodies themselves: three are prose describing the mechanism the PR was building (#21, #33, #41); most functional uses are `_HIGH_RISK_ACK`, which acknowledges the high-risk WARN and is that token's designed purpose (#2, #5, #6, #8, #32, #70, #81, the last acknowledging the high-risk ci.yml change that added the `ci-green` fan-in job); several `_TESTS` tokens sit on self-described docs-only PRs where the tests rule cannot fire, so they were prophylactic no-ops (#4, #7, #11, #12, #13).
- The only BLOCK-suppressing uses on record are `_CAPABILITY_MAP` on three early docs PRs (#7, #10, #12, all pre-#14, each with written rationale) and `_SCANNER` on #70 (suppressed the `scanner-new-ecosystem` WARN for the RFC-0010 pgvector dependency, with rationale, in an HTML comment).

Operating rule that follows: treat any proposal to override a BLOCK as a design smell. The correct responses to a BLOCK, in order: add the missing artifact (test, doc, capability-map row, lesson), fix the body format, or, only for a demonstrable false positive, use the matching token with a one-line rationale plus a `LES-<n>` citation. Never edit `tools/pr_guardian.py` to silence a finding (that path itself triggers `guardian-change-without-lesson`). Never bypass the Manual Merge Gate.

## 9. RFC process and work packages

RFCs (docs/RFC_PROCESS.md): required for new engines, new agents, new runtime services, new provider integrations, governance changes, security model changes, data model changes, major UI/UX changes, autonomous action capabilities, and external system integrations. Lifecycle: Draft -> Council Review -> Final Judge -> Accepted / Rejected / Deferred -> Implementation -> Validation -> Knowledge. Required sections: Summary, Problem, Goals, Non-goals, Proposal, Alternatives, Evidence, Risks, Security impact, Compliance impact, Migration plan, Acceptance criteria, Open questions, Final Judge verdict. Naming: `docs/rfc/RFC-0000-title.md`. RFC-0000 through RFC-0010 exist as of 2026-07-06.

Work packages (RFC-0003, `docs/rfc/RFC-0003-Work-Package-Specs.md`): every package gets `.archetype/work/<TASK-ID>.md` BEFORE implementation starts, copied from `.archetype/work/TEMPLATE.md`. Required sections: Status (Proposed / Ready / In Progress / Blocked / In Review / Merged / Deferred), Verified Baseline (current state confirmed by inspection, with file:line pointers, never assumed from a board description), In-Scope Files (exact paths), Out-of-Scope, Acceptance Criteria (checkable assertions, each with an `evidence:` pointer to a test name, command, or CI job), Verification Plan, Suggested Delegation, Board Linkage (Plane item plus branch).

Conventions enforced by practice (docs/ORCHESTRATOR_PLAYBOOK.md package loop): one PR = exactly one work package (each package restarts the branch from `origin/main`); delegation prompts are generated from the spec, not written ad hoc; scope expansion beyond the spec's In-Scope Files means a new package, and any change in an RFC-required category means an RFC first.

## 10. The local gate: scripts/pre_pr_guardian.sh

Exactly what it runs, in order (verified against the 49-line script as of 2026-07-06):

1. Validates the base ref exists (`git rev-parse --verify`, default base `origin/main`, default head `HEAD`); exits 2 with a "Run: git fetch origin main" hint if not.
2. If no body file was passed as arg 3, writes a temp placeholder body with compliant `Verification pending` / `Level 2` metadata so the deterministic checks can run.
3. `python tools/pr_guardian.py --base <base> --head <head> --body-file <body>` (note: `python`, not `python3`; the script runs under `set -euo pipefail`, so a BLOCK exit 1 stops the gate here).
4. `python -m compileall apps/api/app apps/api/tests apps/worker/app apps/worker/tests`
5. `PYTHONPATH=apps/api pytest apps/api/tests`
6. `PYTHONPATH=apps/worker pytest apps/worker/tests`
7. `(cd apps/web && npm run build)` if npm is available, else a skip note.
8. `docker compose config >/dev/null` if docker is available, else a skip note.

Invocation:

```bash
cd /home/nerfherder/Dev/ArchetypeOS
bash scripts/pre_pr_guardian.sh                                  # defaults
bash scripts/pre_pr_guardian.sh origin/main HEAD /tmp/pr_body.md # explicit
```

The placeholder body is not a substitute for real PR evidence: the author must replace it with concrete verification metadata in the actual PR body. The script does not run ruff; the Orchestrator's independent verification adds `python3 -m ruff check apps/api apps/worker tools`.

## 11. The head-SHA-pinned Manual Merge Gate

Required status checks are not enforceable on this repository's current GitHub plan (private, free tier; docs/BRANCH_PROTECTION.md). The compensating control (docs/PR_GUARDIAN.md, Manual Merge Gate):

- Before merge, a verification comment is posted on the PR, pinned to the exact head SHA, reporting CI green: the workflow run id and the conclusion of every CI job.
- Merging when the merged head SHA does not match the SHA in that comment is a protocol violation, even if CI looked green earlier in the PR's history. A new push voids the gate; re-verify and re-post.
- The human operator performs the merge. Agents never merge.

CI job names defined in `.github/workflows/ci.yml` on live main as of 2026-07-06 (nine jobs): `PR Guardian`, `API tests and lint`, `Worker tests and lint`, `Vector store tests`, `Embedder tests`, `Web typecheck and build`, `Web e2e (Playwright)`, `Docker Compose smoke test`, `CI green`. The ninth, `CI green` (job id `ci-green`, added by AOS-OPS-001, PR #81), is an additive fan-in job that runs only after every other job succeeds and posts a CI-green comment on the PR; it feeds the Manual Merge Gate but does not replace it: the gate comment must still be pinned to the exact head SHA and report every job on that SHA. Note a known doc drift: docs/PR_GUARDIAN.md and docs/BRANCH_PROTECTION.md still list only the original five names; the workflow file is ground truth.

After merge: `scripts/post_merge_validation.sh` (docs/POST_MERGE_VALIDATION.md).

## 12. The two unwritten rules

1. Never override Guardian on substance. Covered in section 8. BLOCKs are information about a missing artifact; produce the artifact.
2. Mature-state only (operator rule, 2026-07-06, docs/ORCHESTRATOR_PLAYBOOK.md "Design to the mature-state target"): define the mature-state architecture of a subsystem first, then make every work package a strict subset of that target, a permanent layer that later work extends, never scaffolding that gets torn out. The test for every spec step: will this design be extended or torn out by the mature system? If torn out, do not build it, or reduce it to the honest minimum that survives. Shipping small verified packages is correct; shipping an approach that gets replaced is "building twice". The ratified canonical pattern is the two-tier evidence pipeline (deterministic floor plus reasoned tier) where the floor stays honest and conservative: when unsure it emits nothing, because empty beats wrong.

Builder-is-not-verifier doctrine (docs/ORCHESTRATOR_PLAYBOOK.md Role contract): builders implement inside exact file boundaries and return raw command output; they never commit, never push, never self-certify. The Orchestrator re-runs the full suite itself, reads the actual diff, and probes live behavior before claiming any verification status. A builder's "tests pass" is input, not evidence.

## 13. Pre-PR checklist

Work through in order; each line is a gate that has actually fired on a past PR.

- [ ] Work package spec exists at `.archetype/work/<TASK-ID>.md` with Verified Baseline and evidence-pointed Acceptance Criteria (RFC-0003).
- [ ] Change is a strict subset of the subsystem's mature-state target; nothing in it is scaffolding.
- [ ] If the change is in an RFC-required category (section 9), the RFC is Accepted first.
- [ ] Code change carries its tests in the same diff (api, worker, core; web e2e for `apps/web/src/`). Even a one-line `aos_core` tweak needs a unit test (LES-020).
- [ ] Code, compose, or workflow change touches at least one doc-prefix path; new `docs/*.md` files also touch `docs/CAPABILITY_MAP.md` (LES-003).
- [ ] State docs (ACTIVE_WORK, CURRENT_STATE, HANDOFF, RECENT_CHANGES) updated in the same PR.
- [ ] Every Guardian BLOCK, CI failure, or review remediation encountered has a lesson page plus index row in the same change set (CLAUDE.md, RFC-0004).
- [ ] PR body: six plain `Field: value` metadata lines, exact status and level literals (LES-002, LES-003).
- [ ] PR body: `## Acceptance Evidence` heading with at least one `evidence:` bullet if any code prefix changed.
- [ ] No full `PR_GUARDIAN_OVERRIDE_` token appears in the body unless intended, with rationale plus a `LES-<n>` citation.
- [ ] `bash scripts/pre_pr_guardian.sh` passes locally from the repo root.
- [ ] PR title format `<ID>: <what> (<context>)`; one PR = one work package.
- [ ] After CI green: Manual Merge Gate comment pinned to the head SHA; human merges; never merge on a stale SHA.

## 14. Task tier guide

Routing home is aos-model-routing; these labels are operator guidance with candidate status, scoped to change-control tasks only.

| Task in this skill's scope | Tier |
|---|---|
| Run Guardian or the local gate and report the verdict verbatim | Haiku |
| Format the six-line verification metadata block for a PR body | Haiku |
| Check accepted_warnings.json entries against today's date | Haiku |
| Fix a BLOCK by adding the missing artifact (test, doc, capability-map row) | Sonnet |
| Author a work package spec from TEMPLATE.md with a real Verified Baseline | Sonnet |
| Write the lesson page for a Guardian catch | Sonnet |
| Change a Guardian rule (requires a lesson, RFC-0004 discipline) | Opus |
| Draft or review an RFC; classify a borderline governance change | Opus |
| Adjudicate a scope dispute or a proposed override of a BLOCK | Opus |

## 15. Common mistakes

| Mistake | Consequence | Correct move |
|---|---|---|
| Writing metadata as `- **Field:** value` bullets | BLOCK `missing-verification-metadata` (LES-003) | Plain `Field: value` at line start |
| Appending qualifiers to enum literals (`Level 4 (local)`) | BLOCK `invalid-verification-level` (LES-002) | Qualifiers go in the Method text |
| Mentioning a full override token in PR prose | Silently activates the override and triggers `override-without-lesson-citation` | Split the token string or cite a `LES-<n>` |
| Leaning on an e2e to cover an `aos_core` change | BLOCK `missing-core-tests`; e2e paths are outside the test globs (LES-020) | Hermetic unit test in `packages/aos_core/tests/` or `apps/api/tests/` |
| Adding a doc without touching the capability map | BLOCK `capability-map-not-updated` | Add the map row in the same diff |
| Editing `tools/pr_guardian.py` to silence a finding | BLOCK `guardian-change-without-lesson`, and it violates the evolution discipline | Fix the artifact; rule changes only consume logged lessons |
| Letting a warning repeat silently across PRs | The LES-006 failure mode; invisible debt | Accept it in the registry with a `review_by` date, or fix it |
| Merging on a green run from an older SHA | Protocol violation of the Manual Merge Gate | Re-verify and re-post the gate comment on the current head SHA |
| Running Guardian from a subdirectory | Relative required-file paths break | Always run from the repo root |
| Treating a builder's reported test run as verification | Violates builder-is-not-verifier | Orchestrator re-runs the suite and reads the diff |

## 16. Provenance and maintenance

Written 2026-07-06 on branch `laptop/aos-selfheal-doc-loop` (HEAD = AOS-SELFHEAL-001, merged as PR #80; `tools/pr_guardian.py` is identical on live main and HEAD, verified by blob SHA, so all rule descriptions reflect merged state; the `tools/doc_staleness.py --fix` reconciliation-draft flag is merged via PR #80 as well). The local `origin/main` ref may lag live GitHub; re-verify PR-level facts with `gh`, not the stale local ref.

Derived from: `tools/pr_guardian.py`, `docs/PR_GUARDIAN.md`, `docs/RFC_PROCESS.md`, `docs/rfc/RFC-0003-Work-Package-Specs.md`, `docs/BRANCH_PROTECTION.md`, `docs/ORCHESTRATOR_PLAYBOOK.md`, `docs/ENGINEERING_CONSTITUTION.md`, `docs/VERIFICATION_PROTOCOL.md`, `scripts/pre_pr_guardian.sh`, `.archetype/guardian/accepted_warnings.json`, `.archetype/work/TEMPLATE.md`, `.claude/commands/guardian.md`, `.github/workflows/ci.yml`, `knowledge/wiki/lessons/LES-002.md`, `LES-003.md`, `LES-006.md`, `LES-009.md`, `LES-020.md`, plus merged-PR body inspection via `gh`.

Re-verification commands for facts that may drift:

| Fact | Re-verify with |
|---|---|
| Rule codes and severities | `grep -n -A3 'Finding(' tools/pr_guardian.py` (many findings are multi-line constructions; a bare `Finding("` grep misses most codes) |
| Required metadata fields and literals | `grep -n -A8 'REQUIRED_VERIFICATION_FIELDS\|ALLOWED_VERIFICATION_STATUSES' tools/pr_guardian.py` |
| Override token list | `grep -n 'has_override' tools/pr_guardian.py` and `grep -n 'PR_GUARDIAN_OVERRIDE' docs/PR_GUARDIAN.md` |
| Accepted-warnings registry contents (was `[]`) | `cat .archetype/guardian/accepted_warnings.json` |
| Merged-PR count (was 75) | `gh pr list --state merged --limit 200 --json number --jq length` (the local `git log origin/main` count lags live GitHub when the ref is stale) |
| Override usage in merged PR bodies (was 16 PRs, none suppressing a substantive code BLOCK) | `gh pr list --state merged --limit 200 --json number,body --jq '[.[] \| select(.body \| test("PR_GUARDIAN_OVERRIDE_[A-Z]"))] \| map(.number)'` |
| CI job names (were 9) | `grep -n '^    name:' .github/workflows/ci.yml` (fetch main first; a stale checkout shows 8, missing `CI green`) |
| Local gate step order | `cat scripts/pre_pr_guardian.sh` |
| RFC inventory (was RFC-0000..0010) | `ls docs/rfc/` |
| Work package template sections | `cat .archetype/work/TEMPLATE.md` |
| doc_staleness --fix status (merged via PR #80) | `git log origin/main --oneline --grep SELFHEAL` (shows the AOS-SELFHEAL-001 commit once origin/main is fetched; `gh pr view 80 --json state` confirms MERGED) |
| Mature-state rule wording | `grep -n -A6 'mature-state target' docs/ORCHESTRATOR_PLAYBOOK.md` |
