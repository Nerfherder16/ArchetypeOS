# PR Guardian

## Purpose

PR Guardian reviews changes before pull request or merge.

It is a release gate and engineering reviewer, not a replacement for human judgment.

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

## Verdicts

- Approve
- Approve with warnings
- Block
- Research further
- Human review required

## Required Output

- verdict
- risk score
- required fixes
- suggested fixes
- evidence
- affected files
- affected architecture nodes
- missing tests
- missing docs
- confidence

## Local First Use

PR Guardian should run locally before PR creation and later as GitHub CI.

The RTX 3090 local LLM node can perform first-pass triage. Complex or high-risk issues can escalate to premium models or Final Judge.

## Safety

PR Guardian should not modify files by default. It creates review reports, warnings, and draft issues.

## Principle

No PR should merge without understanding its risk, documentation impact, and architecture impact.
