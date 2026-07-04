# Post-Merge Validation

## Purpose

Post-merge validation confirms that `main` remains healthy after a PR lands. It complements branch protection and PR Guardian.

## Required Main Branch State

After every merge into `main`, confirm:

- the CI workflow completed successfully for the merge commit or latest `main` commit
- API tests and lint passed
- Worker tests and lint passed
- Web typecheck and build passed
- Docker Compose smoke test passed
- no emergency follow-up PR is required

## Exact CI Job Names

GitHub reports these job names from `.github/workflows/ci.yml`:

```text
PR Guardian
API tests and lint
Worker tests and lint
Web typecheck and build
Docker Compose smoke test
```

Note: `PR Guardian` runs on pull request events. The post-merge `main` push run validates the non-PR jobs.

## Local Validation Command

Run:

```bash
scripts/post_merge_validation.sh
```

This script runs local compile/test/build checks and Docker Compose validation where the required tools are available.

## Optional GitHub CLI Check

If `gh` is authenticated, inspect the latest `main` workflow run:

```bash
gh run list --branch main --workflow CI --limit 1
gh run view --log
```

Expected result:

```text
conclusion: success
```

## Manual Checklist

1. Open the repository Actions tab.
2. Select the latest `CI` run on `main`.
3. Confirm these jobs passed:
   - API tests and lint
   - Worker tests and lint
   - Web typecheck and build
   - Docker Compose smoke test
4. Confirm the merge commit is the expected commit.
5. Record any failure as a fix-forward PR unless the failure is clearly external and transient.

## Failure Protocol

If post-merge validation fails:

1. Do not weaken CI.
2. Identify the failing job and first failing step.
3. Patch the root cause in a follow-up PR.
4. Keep the same required checks active.
5. Re-run validation after the fix lands.

## Acceptance Standard

`main` is considered validated only when the latest relevant CI run is successful and the local validation command does not reveal a reproducible runtime issue.
