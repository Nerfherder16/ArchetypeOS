# PR Guardian

## Purpose

PR Guardian reviews changes before pull request or merge.

It is a release gate and engineering reviewer, not a replacement for human judgment.

## v0.1 Implementation

The v0.1 PR Guardian is deterministic and runs in GitHub Actions through:

```text
tools/pr_guardian.py
```

It also runs locally through:

```bash
scripts/pre_pr_guardian.sh
```

This first version intentionally avoids LLM judgment. It blocks obvious hygiene, scope, documentation, verification, and safety failures before a human review.

## Checks

- diff scope
- architecture impact
- security impact
- dependency impact
- test coverage
- documentation impact
- migration risk
- secrets exposure
- configuration changes
- release gate status
- capability map drift
- runtime/build junk
- high-risk file changes
- verification metadata
- acceptance evidence
- scanner-informed risk signals

## Deterministic Blocking Rules

The current implementation blocks when:

- required foundation files are missing
- potential secrets are added to the diff
- runtime/build artifacts are committed
- API code changes without API test changes
- worker code changes without worker test changes
- implementation/runtime files change without documentation changes
- new capability docs are added without updating `docs/CAPABILITY_MAP.md`
- PR body verification metadata is missing
- PR body verification status is unsupported
- PR body verification status is `Verification unavailable` or `Verification blocked`
- PR body verification level is unsupported
- any changed file starts with `apps/api/app/`, `apps/worker/app/`, or `apps/web/src/` and the PR body has no `## Acceptance Evidence` heading (code `missing-acceptance-evidence`)
- an `## Acceptance Evidence` section exists but no bullet under it contains `evidence:` (case-insensitive) (code `empty-acceptance-evidence`)
- a changed file path matches a scanner `SECRET_LIKE_FILENAME` signal (code `scanner-secret-path`)
- a changed file path matches a scanner `ENV_FILE_PRESENT` signal (code `scanner-env-committed`)

## Warning Rules

The current implementation warns when:

- web source changes (`apps/web/src/`) without matching web e2e test changes (`apps/web/e2e/`) — web tests are now enforced (code `web-tests-not-enforced`); mirrors the api/worker test-coverage checks but stays a WARN, overridable with `PR_GUARDIAN_OVERRIDE_WEB_TESTS`. The Playwright suite lives in `apps/web/e2e/` and runs as the `Web e2e (Playwright)` CI job. This replaces the earlier unconditional "UI tests not yet available" warning; the `web-tests-not-enforced` accepted-warnings entry was retired once real tests existed (LES-006, LES-009).
- high-risk files such as workflows, compose config, environment example, auth, or secrets-related files change
- verification status is `Verification pending`
- verification metadata uses weak placeholders such as `TBD`, `TODO`, `none`, or `n/a`
- the scanner reports `MISSING_TESTS` and the PR adds app code under `apps/api/app/`, `apps/worker/app/`, or `apps/web/src/` (code `scanner-missing-tests`)
- the scanner reports `MULTIPLE_ECOSYSTEMS` and the PR adds a package manifest (code `scanner-new-ecosystem`)

## Verification Metadata Requirement

Every PR body must include this metadata:

```text
Verification Status: Verified | Verified with warnings | Verification pending | Verification unavailable | Verification blocked
Verification Level: Level 0 | Level 1 | Level 2 | Level 3 | Level 4 | Level 5
Verification Method:
Evidence:
Limitations:
Required Next Verifier:
```

Allowed statuses are defined in `docs/VERIFICATION_PROTOCOL.md`.

Mergeability rules:

- `Verified` may merge when all other gates pass.
- `Verified with warnings` may merge when warnings are acknowledged.
- `Verification pending` may remain open but must not merge until a stronger verifier records final evidence.
- `Verification unavailable` blocks merge.
- `Verification blocked` blocks merge.

## Acceptance Evidence Requirement

When any changed file starts with `apps/api/app/`, `apps/worker/app/`, or `apps/web/src/`, the PR body must also include an `## Acceptance Evidence` heading. Under that heading, at least one bullet must contain `evidence:` (case-insensitive) mapping an acceptance criterion to a test name, command, or CI job. This mirrors the per-criterion `evidence:` pointers required in work package specs (`docs/rfc/RFC-0003-Work-Package-Specs.md`, `.archetype/work/<TASK-ID>.md`).

Blocking codes:

- `missing-acceptance-evidence` — no `## Acceptance Evidence` heading found.
- `empty-acceptance-evidence` — the heading exists but no bullet under it carries an `evidence:` pointer.

This check does not apply to PRs that change only docs, config, or other non-code paths. Override marker: `PR_GUARDIAN_OVERRIDE_ACCEPTANCE`.

## Scanner-Informed Checks

The guardian consults the read-only repository scanner (`apps/api/app/repository_scanner.py`) to add four checks driven by its structured `risk_signals`:

- `scanner-secret-path` (block) — a changed file matches a `SECRET_LIKE_FILENAME` signal, catching committed key files by name that the diff-content regexes miss.
- `scanner-env-committed` (block) — a changed file matches an `ENV_FILE_PRESENT` signal, meaning a real `.env` is being committed.
- `scanner-missing-tests` (warn) — the scan reports `MISSING_TESTS` and the PR adds app code.
- `scanner-new-ecosystem` (warn) — the scan reports `MULTIPLE_ECOSYSTEMS` and the PR adds a package manifest.

The scan comes from the optional `--scan-report <path>` argument (a JSON report). When that argument is absent, the guardian runs an in-repo scan by importing the stdlib-only scanner and scanning the working tree. If the report cannot be loaded, or the scanner cannot be imported or run, all four checks are skipped and the guardian behaves exactly as it did before (graceful degradation). The report prints one line noting whether scanner-informed checks ran and how many signals were consulted.

The four checks are suppressed together by `PR_GUARDIAN_OVERRIDE_SCANNER` with rationale in the PR body.

## Guardian Evolution (RFC-0004 Phase 2)

The guardian evolves from logged reality, never speculation: every rule change consumes a lesson **by ID**. Three mechanisms enforce and support that discipline.

### Guardian changes must cite a lesson

- `guardian-change-without-lesson` (block) — the diff touches `tools/pr_guardian.py` but no changed path starts with `knowledge/wiki/lessons/`. Update the lessons registry to record the reality that motivated the rule change, or include `PR_GUARDIAN_OVERRIDE_LESSON` with rationale (for non-rule refactors).

### Overrides must cite a lesson ID

- `override-without-lesson-citation` (block) — the PR body uses any `PR_GUARDIAN_OVERRIDE_*` token but contains no `LES-<n>` reference. Every override is an exception to a rule; the exception must point at the logged lesson (`LES-<n>`) that justifies it.

### Accepted-warnings registry

Warnings that are consciously accepted (rather than silently repeated) are recorded in `.archetype/guardian/accepted_warnings.json`, a JSON list of entries:

```json
{"code": "web-tests-not-enforced", "lesson": "LES-006", "rationale": "why this warning is accepted", "review_by": "YYYY-MM-DD"}
```

After all findings are collected, each warn-severity finding whose `code` matches an entry is post-processed:

- today `<= review_by` — the finding stays a warning, but its message is annotated ` [accepted per <lesson> until <review_by>: <rationale>]` so the acceptance is cited and dated, never silent.
- today `> review_by` — the finding escalates to a block with code `accepted-warning-expired`, forcing a re-decision: renew the entry (new `review_by`) or fix the underlying gap.

Only warn-severity findings are eligible; blocks are never softened by the registry. A missing, unreadable, or invalid registry is treated as an empty list (graceful degradation, with a stdout note), exactly like the scan report. The registry is stdlib-only (`json`, `datetime`, `pathlib`).

## Override Protocol

Overrides are allowed only with rationale in the PR body.

Supported override markers:

```text
PR_GUARDIAN_OVERRIDE_TESTS
PR_GUARDIAN_OVERRIDE_WEB_TESTS
PR_GUARDIAN_OVERRIDE_DOCS
PR_GUARDIAN_OVERRIDE_CAPABILITY_MAP
PR_GUARDIAN_OVERRIDE_HIGH_RISK_ACK
PR_GUARDIAN_OVERRIDE_ACCEPTANCE
PR_GUARDIAN_OVERRIDE_SCANNER
PR_GUARDIAN_OVERRIDE_LESSON
```

`PR_GUARDIAN_OVERRIDE_LESSON` suppresses `guardian-change-without-lesson` for guardian edits that are not rule changes (refactors). Note that any override token still requires a `LES-<n>` citation in the body (`override-without-lesson-citation`).

`PR_GUARDIAN_OVERRIDE_SCANNER` suppresses all four scanner-informed checks (`scanner-secret-path`, `scanner-env-committed`, `scanner-missing-tests`, `scanner-new-ecosystem`).

`PR_GUARDIAN_OVERRIDE_ACCEPTANCE` suppresses the acceptance-evidence check (`missing-acceptance-evidence`, `empty-acceptance-evidence`). It only applies to that check; it does not suppress the verification metadata requirement below, which has no bypass marker.

Overrides should be used sparingly. They are audit markers, not a way to bypass review casually.

Verification metadata is not optional and has no bypass marker. If verification cannot be completed, use `Verification unavailable`, `Verification blocked`, or `Verification pending` with limitations and required next verifier.

## Verdicts

- PASS
- PASS_WITH_WARNINGS
- BLOCK

Future versions may add:

- Research further
- Human review required
- Final Judge escalation

## Required Output

- verdict
- changed files
- blocking findings
- warning findings
- evidence
- required fixes
- verification metadata findings

## CI Enforcement

GitHub Actions runs these check names:

```text
PR Guardian
API tests and lint
Worker tests and lint
Web typecheck and build
Docker Compose smoke test
```

Branch protection for `main` must require those exact check names. See `docs/BRANCH_PROTECTION.md`.

The local pre-PR command is:

```bash
scripts/pre_pr_guardian.sh
```

The post-merge validation command is:

```bash
scripts/post_merge_validation.sh
```

See `docs/POST_MERGE_VALIDATION.md`.

## Manual Merge Gate

Required status checks are not enforceable as a merge gate on this repository's current plan. Until that changes, merging a PR requires a verification comment posted on the PR, pinned to the exact head SHA, reporting CI green: the workflow run id and the conclusion of every job (PR Guardian, API tests and lint, Worker tests and lint, Web typecheck and build, Docker Compose smoke test). The comment is posted by the babysitting agent or a human reviewer.

Merging without confirming that the head SHA in the merge matches the SHA reported in that comment is a protocol violation, even if CI appeared green at some earlier point in the PR's history.

## Local First Use


The `/guardian` Claude Code command (`.claude/commands/guardian.md`) wraps the invocations below for any session — local, remote, or on the runtime workstation. Pass `full` for the complete pre-PR gate.
PR Guardian should run locally before PR creation and later as GitHub CI.

The local command is:

```bash
scripts/pre_pr_guardian.sh
```

When run without a PR body file, the local script injects temporary `Verification pending` metadata so deterministic checks can run. The PR author must replace that temporary evidence with concrete verification evidence in the PR body.

The RTX 3090 local LLM node may later perform first-pass semantic review, but deterministic checks remain the base gate.

## Safety

PR Guardian must not modify files by default. It creates reports, warnings, and blockers only.

## Principle

No PR should merge without understanding its risk, documentation impact, test impact, verification status, and architecture impact.
