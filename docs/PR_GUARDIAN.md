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

## Warning Rules

The current implementation warns when:

- web source changes without UI tests available yet
- high-risk files such as workflows, compose config, environment example, auth, or secrets-related files change
- verification status is `Verification pending`
- verification metadata uses weak placeholders such as `TBD`, `TODO`, `none`, or `n/a`

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
```

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
