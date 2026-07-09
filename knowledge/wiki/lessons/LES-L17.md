# LES-L17 — the auto-rebase bot pushed PR branches with GITHUB_TOKEN, so GitHub gated the resulting CI run as `action_required` (0 jobs) and PR Guardian silently never ran on the current head

## Aliases

- PR looks mergeable but has no CI on its latest commit
- CI run stuck in `action_required` with zero jobs
- Guardian check "missing" / not reviewing a PR
- workflow does not run on commits pushed by GITHUB_TOKEN
- auto-rebase silently un-verifies every open PR

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Three open PRs (#159, #161, #163) showed **no PR Guardian result** on their current heads;
  `gh pr checks` returned empty and `mergeStateStatus` was `UNSTABLE`.
- The heads had been updated at 19:26 by `.github/workflows/auto-rebase-prs.yml`
  (commit author `aos-autorebase[bot]`, run triggered by `github-actions[bot]`).
- `gh api /actions/runs/<id>` on those runs: `event=pull_request`, `status=completed`,
  `conclusion=action_required`, **`jobs: []`** — the workflow was created but never executed.
- The *earlier* commits pushed by a human (me) had run CI + Guardian normally and passed
  (`completed/success`). Only the bot-pushed heads were gated.
- Root cause: `auto-rebase-prs.yml` pushed the rebased branch with
  `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`. GitHub does **not** run workflows on commits
  pushed by the default `GITHUB_TOKEN` (recursion/abuse guard), so the `pull_request`
  `synchronize` run is created but parked as `action_required` and never runs.
- The REST "approve a workflow run" endpoint is **fork-only** (`/actions/runs/<id>/approve`
  → HTTP 403 "This run is not from a fork pull request"), so it cannot clear a
  `GITHUB_TOKEN`-gated same-repo run.

## Linked Decisions / Projects

- `.github/workflows/auto-rebase-prs.yml` (AOS-CI-AUTOREBASE-001 → -002 fix)
- [[LES-L03]] — the auto-rebase workflow itself (why main-advance re-flags union-merged PRs)

## Content

- Event: an automation that keeps PRs current (auto-rebase) simultaneously and silently
  **removed CI/Guardian verification** from every PR it touched, because it pushed with the
  default `GITHUB_TOKEN`. The PRs looked mergeable and "green-ish" while their current commit
  had never been checked.
- Rules:
  1. Any bot/automation that pushes commits you expect CI to verify must push with a token
     that triggers workflows — a **GitHub App installation token** (`actions/create-github-app-token`)
     or a PAT — NOT the default `GITHUB_TOKEN`. `GITHUB_TOKEN` pushes are intentionally inert.
  2. A CI run with `conclusion=action_required` and `jobs: []` means it was created but never
     ran — treat it as UNVERIFIED, not "pending". A green-looking PR whose latest head has such
     a run has not actually been checked.
  3. `/actions/runs/<id>/approve` only clears fork-PR gates. To force CI onto a
     `GITHUB_TOKEN`-gated same-repo head, push a fresh `pull_request` event under a trusted
     actor (e.g. a labeled empty commit) — that runs CI normally.
  4. Make the token upgrade resilient: gate the App-token step on the secret being present and
     fall back to `GITHUB_TOKEN`, so the workflow keeps working before the secret exists and
     auto-upgrades once it is added (no window where the rebase itself breaks).
