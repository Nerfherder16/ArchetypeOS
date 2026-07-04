# Branch Protection Setup

## Purpose

ArchetypeOS CI must be required before changes enter `main`. This document records the required GitHub settings and the exact check names used by the current workflow.

## Tooling Note

The GitHub connector available in this session can inspect repositories, files, pull requests, commits, and workflow runs. It does not expose branch protection or ruleset edit actions. Apply the settings below in GitHub repository settings unless a future authorized API path is added.

## Protected Branch Pattern

```text
main
```

## Required Settings

For `main`, enable these repository settings:

- pull request required before merge
- approvals required before merge
- stale approvals dismissed when new commits are pushed
- status checks required before merge
- branch must be up to date before merge
- direct commits to `main` disabled
- force pushes disabled
- branch deletion disabled
- conversation resolution required when available

## Required Status Check Names

The required check names must match GitHub's CI job names exactly:

```text
PR Guardian
API tests and lint
Worker tests and lint
Web typecheck and build
Docker Compose smoke test
```

These names are defined in `.github/workflows/ci.yml`.

## Manual Setup: Classic Branch Rule

1. Open the repository on GitHub.
2. Open **Settings**.
3. Open **Branches**.
4. Choose **Add branch protection rule**.
5. Set the branch pattern to `main`.
6. Enable pull request requirement.
7. Enable approval requirement.
8. Enable stale approval dismissal.
9. Enable required status checks.
10. Enable up-to-date branch requirement.
11. Select the required checks listed above, exactly as written.
12. Enable conversation resolution if available.
13. Keep force pushes disabled.
14. Keep branch deletion disabled.
15. Save the rule.

## Manual Setup: Repository Ruleset

1. Open the repository on GitHub.
2. Open **Settings**.
3. Open **Rules**.
4. Open **Rulesets**.
5. Create a branch ruleset named `main-required-ci`.
6. Set the ruleset status to active.
7. Target branch `main`.
8. Enable pull request requirement.
9. Enable required status checks.
10. Enable up-to-date branch requirement.
11. Add the required checks listed above, exactly as written.
12. Keep force pushes and branch deletion disabled.
13. Save the ruleset.

## Verification Checklist

After setup, verify with a small PR:

- GitHub lists all required checks on the PR.
- The merge button waits for all required checks.
- Pushing a new commit refreshes the required checks.
- Stale approvals are dismissed after a new commit.
- The PR cannot merge until required checks pass.

## Local Pre-PR Command

Run before opening or updating a PR:

```bash
scripts/pre_pr_guardian.sh
```

With explicit refs and PR body file:

```bash
scripts/pre_pr_guardian.sh origin/main HEAD /tmp/pr_body.md
```

## Post-Merge Command

Run after merging to `main`:

```bash
scripts/post_merge_validation.sh
```

See `docs/POST_MERGE_VALIDATION.md`.

## Acceptance Standard

A change is not ready for `main` until the required checks pass and GitHub settings require those checks for merge.
