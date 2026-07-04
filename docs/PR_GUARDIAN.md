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

This first version intentionally avoids LLM judgment. It blocks obvious hygiene, scope, documentation, and safety failures before a human review.

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

## Deterministic Blocking Rules

The current implementation blocks when:

- required foundation files are missing
- potential secrets are added to the diff
- runtime/build artifacts are committed
- API code changes without API test changes
- worker code changes without worker test changes
- implementation/runtime files change without documentation changes
- new capability docs are added without updating `docs/CAPABILITY_MAP.md`

## Warning Rules

The current implementation warns when:

- web source changes without UI tests available yet
- high-risk files such as workflows, compose config, environment example, auth, or secrets-related files change

## Override Protocol

Overrides are allowed only with rationale in the PR body.

Supported override markers:

```text
PR_GUARDIAN_OVERRIDE_TESTS
PR_GUARDIAN_OVERRIDE_WEB_TESTS
PR_GUARDIAN_OVERRIDE_DOCS
PR_GUARDIAN_OVERRIDE_CAPABILITY_MAP
PR_GUARDIAN_OVERRIDE_HIGH_RISK_ACK
```

Overrides should be used sparingly. They are audit markers, not a way to bypass review casually.

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

## Local First Use

PR Guardian should run locally before PR creation and later as GitHub CI.

The local command is:

```bash
scripts/pre_pr_guardian.sh
```

The RTX 3090 local LLM node may later perform first-pass semantic review, but deterministic checks remain the base gate.

## Safety

PR Guardian must not modify files by default. It creates reports, warnings, and blockers only.

## Principle

No PR should merge without understanding its risk, documentation impact, test impact, and architecture impact.
