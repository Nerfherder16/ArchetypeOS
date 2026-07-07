# AOS-CI-AUTOREBASE-001 — Auto-update open PRs when main advances (LES-L03)

- Status: In Review
- Owner: laptop session (parallel Orchestrator)
- Branch: `laptop/aos-ci-autorebase` (fresh, from `origin/main`)
- Motivated by: LES-L03 — operator hit "as soon as I merged #88, #89 went red… I can't have this happen every time."

## Root cause (LES-L03)

`.gitattributes merge=union` (LES-026) is honored **only by local git**. GitHub's
server-side mergeability probe does **not** run custom merge drivers, so it uses
the default merge, sees two appends in the same region of the union-marked
coordination logs, and flags the second serialized PR CONFLICTING after every
merge — even though a local rebase resolves it in one no-touch pass. The union
driver fixed *local* rebase pain but never the *GitHub-side* red flag.
`CAPABILITY_MAP.md` (not union) genuinely conflicts on top when two PRs edit the
same layer bullet.

## Design

`.github/workflows/auto-rebase-prs.yml`, on `push: main`:
1. Checkout main (`fetch-depth: 0`).
2. List open, non-draft, **same-repo** PRs targeting main (`gh pr list`).
3. For each: if it already contains main, skip. Else **merge main INTO the PR
   branch** — in the runner the `.gitattributes` union driver DOES apply — and
   push. This is a normal fast-forwarding push, **not a force-push**.
4. On a genuine (non-union) conflict the driver can't resolve: `git merge
   --abort` and leave a PR comment naming the conflicting files; move on.

`permissions: { contents: write, pull-requests: write }`. Pushing a PR branch
fires `pull_request:synchronize` (re-runs that PR's CI) but **not** `push: main`,
so there is no loop. `concurrency` cancels superseded runs.

## Why merge-into (not rebase + force-push)

Merging main into the branch adds one commit and pushes without `--force`, so it
never races a contributor's local history the way a force-push would. History is
slightly noisier, but squash-on-merge collapses it. Safety over tidiness.

## In-Scope Files
- `.github/workflows/auto-rebase-prs.yml` (new)
- `knowledge/wiki/lessons/LES-L03.md` + index row (union-safe)
- `.archetype/work/AOS-CI-AUTOREBASE-001.md`
- `docs/CAPABILITY_MAP.md` (Layer 7 note — deliberately NOT Layer 8, to stay
  non-adjacent to the in-flight self-heal PRs; LES-L03's own guidance) ·
  `docs/ACTIVE_WORK.md` + `docs/RECENT_CHANGES.md` (own entries — union-safe)

## Out-of-Scope
- Fork PRs (GITHUB_TOKEN can't push to fork branches) — they log-skip.
- Auto-resolving genuine non-union conflicts (a human still fixes those; the bot
  only comments).
- Structural fragment-files for the coordination logs (a larger follow-up that
  would shrink the collision surface further; LES-L03 generalization).

## Acceptance Criteria
1. Workflow YAML parses (`yaml.safe_load`), one job `update`; no LES-027
   inline-colon trap. — evidence: lint + grep.
2. `ci.yml` untouched (still gating jobs intact). — evidence: separate file.
3. Guardian PASS / PASS_WITH_WARNINGS (a high-risk-files WARN for the workflow is
   expected + acknowledged in the PR body).

## Verification Plan
- Level 2 (local): YAML lint + LES-027 grep; logic reviewed against the union +
  non-union cases.
- Level 3 (dogfoods immediately): on merge to main, the next open-PR set gets
  auto-updated — watch the first run and confirm a previously-red union-file PR
  goes green with no hand-rebase.

## Board Linkage
- Plane: AOS-CI-AUTOREBASE-001 (create Done on merge). Reduces tandem merge toil.
