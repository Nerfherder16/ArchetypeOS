# LES-L18 — the `secrets` context is NOT allowed in a step/job `if:` condition; using it fails workflow validation at startup (the run completes as `failure` with zero jobs)

## Aliases

- "This run likely failed because of a workflow file issue"
- workflow run failed with `jobs: []` / 0 jobs executed
- `if: ${{ secrets.X != '' }}` breaks the workflow
- conditionally use a secret in an Actions step
- local `yaml.safe_load` passes but GitHub rejects the workflow

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- After AOS-CI-AUTOREBASE-002 (#166) merged, every `push:main` auto-rebase run
  completed as `conclusion=failure` with **zero jobs** (`/actions/runs/<id>/jobs` →
  empty). `gh run view <id>` reported: "This run likely failed because of a
  workflow file issue." No step logs existed because no job ever started.
- The only unusual expression added was a step-level
  `if: ${{ secrets.AUTOREBASE_APP_ID != '' }}`. GitHub's context-availability table
  does not list `secrets` among the contexts allowed in `if:` — so the expression
  fails workflow compilation and the run never starts.
- `python3 -c "yaml.safe_load(...)"` passed locally: YAML is well-formed. The rule
  is a GitHub Actions *expression-context* constraint, invisible to a YAML parser.

## Linked Decisions / Projects

- `.github/workflows/auto-rebase-prs.yml` (AOS-CI-AUTOREBASE-002 introduced it; the
  if-fix restores it)
- [[LES-L17]] — the sibling lesson (GITHUB_TOKEN-pushed commits skip CI) that this
  workflow change was made to fix; this is the bug in that fix

## Content

- Event: a workflow change that gated a step on `if: ${{ secrets.* != '' }}` took
  the whole workflow down — it failed at startup with no jobs, so the auto-rebase
  capability silently stopped working on every `main` advance.
- Root cause: `secrets` is not an allowed context in `if:` conditions (it is only
  available in `env`, `with`, `run`, and a few others). An invalid context in an
  expression is a *compile-time* error → the run is created but no job runs.
- Rules:
  1. Never reference `secrets.*` directly in an `if:`. To gate a step on a secret's
     presence, surface it through a job-level `env` (where `secrets` IS allowed) and
     test the env: `env: { HAS_X: ${{ secrets.X != '' }} }` then `if: ${{ env.HAS_X == 'true' }}`.
  2. A workflow run with `conclusion=failure` and **0 jobs** = a workflow-file /
     expression error, not a step failure. Read `gh run view <id>` (it says so) and
     fix the YAML/expression, do not hunt for a failing step.
  3. `yaml.safe_load` passing is necessary but NOT sufficient — it does not validate
     GitHub expression contexts. For workflow-expression changes, the only real
     verification is a live run (or `act`/actionlint), so treat the first post-merge
     run as the verification and watch it.
