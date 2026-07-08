---
name: aos-ship-pr
description: Use to ship an ArchetypeOS change end to end as a reviewable PR — the recurring sync-main → cut-branch → commit → local Guardian gate → push → open PR → watch checks → merge-on-green ritual. Triggers on "ship this", "open a PR for this", "cut a branch and PR it", or when finishing a task that needs to reach main. Encodes the guardrails the manual flow relies on: never open a PR without explicit approval, never merge without CI green + Guardian PASS + the head-SHA-pinned Manual Merge Gate. (Meaning of a specific Guardian finding: aos-change-control. Running the tools: aos-diagnostics-and-tooling. Writing the test evidence: aos-validation-and-qa.)
---

# AOS Ship-PR Loop

## 1. What this captures

Every change to ArchetypeOS reaches `main` by hand-running the same sequence, once
per PR. The toil harvester (`tools/toil_digest.py`) surfaced it from the reflog as
the recurring ritual `checkout -> pull -> checkout -> commit`, repeated for every
ticket (PRs #114 through #119 all share the shape). Read end to end against the
reflog and `docs/` gate stack, the full ritual is:

1. Sync `main` to `origin/main` (fast-forward only).
2. Cut a feature branch off the fresh `main`.
3. Do the work and commit it (conventional / ticket-prefixed message).
4. Run the local gate (`scripts/pre_pr_guardian.sh`): Guardian + compile + tests +
   web build + compose validation.
5. Write the PR body with the required verification metadata.
6. Push and open the PR (base `main`) — only with explicit approval.
7. Watch CI, then merge only on green + Guardian PASS + Manual Merge Gate.

This skill turns that whole sequence into one guided command. It does not invent a
new process; it captures the existing gate stack (see aos-change-control) as a
single repeatable flow so the steps and their guardrails are never skipped.

## 2. When to use / when NOT to use

Use this skill when:

- You have finished (or are about to finish) a change and it needs to reach `main`.
- The user says "ship it", "open a PR", "branch and PR this", or similar.
- You are resuming a half-shipped change (branch exists, PR not yet open or not yet
  merged) and need to complete the remaining steps in order.

Do NOT use this skill for:

- The meaning of a specific Guardian finding code or override policy: aos-change-control.
- Deciding what counts as sufficient test evidence, or adding tests: aos-validation-and-qa.
- Diagnosing why tests or services fail: aos-debugging-playbook.
- Reconciling state docs or authoring the lesson page after merge: aos-docs-and-lessons.

## 3. Guardrails (never weaken these)

- Never open a PR without explicit approval. `gh pr create` runs only after the
  operator says "open the PR" (or equivalent) in that instruction. Finishing the
  work, or pushing the branch, does NOT imply PR approval.
- Never auto-merge. A PR merges only when ALL of these hold: CI is green, Guardian
  is PASS or PASS_WITH_WARNINGS, and the head-SHA-pinned Manual Merge Gate comment
  is posted for the exact head SHA. The human operator performs the merge; this
  skill never runs `gh pr merge` on its own.
- Builder is not verifier. The agent that wrote the code does not certify it. The
  local gate and CI re-run the suite independently (docs/ORCHESTRATOR_PLAYBOOK.md).
- Guardian BLOCKs are fixed in code, not overridden. If Guardian BLOCKs, fix the
  cause. Do not reach for a `PR_GUARDIAN_OVERRIDE_*` token to get past it.
- Record a lesson under `knowledge/wiki/lessons/` (RFC-0004) in the same change set
  for any Guardian BLOCK, CI failure, or review remediation you hit while shipping.
- No force-push, no history rewrite on a branch that already has an open PR unless
  the operator asks for it.

## 4. The loop, step by step

### Step 0 — Preconditions

```bash
git status --porcelain   # must reflect only the changes you intend to ship
git rev-parse --abbrev-ref HEAD
```

If the working tree has unrelated local changes, stop and resolve that first — do
not ship over someone else's uncommitted work.

### Step 1 — Sync main (fast-forward only)

```bash
git checkout main
git pull --ff-only origin main
```

`--ff-only` is deliberate: a non-fast-forward means `main` diverged and you must
reconcile before branching, not merge blindly.

### Step 2 — Cut the feature branch

Branch naming follows the repo convention `laptop/<ticket-slug>` (e.g.
`laptop/aos-voice-005-promote-drafts`).

```bash
git checkout -b laptop/<ticket-slug>
```

If the branch already exists (resuming), `git checkout laptop/<ticket-slug>` and
`git rebase origin/main` only if it is safe (no open PR, or operator approved).

### Step 3 — Commit the work

Make the change, then commit with a conventional / ticket-prefixed message:

```bash
git add -A
git commit -m "<type>(<scope>): <TICKET-ID> — <summary>"
```

Commit only after the change is complete for this PR. One logical change per PR.

### Step 4 — Local gate (run before opening anything)

```bash
scripts/pre_pr_guardian.sh origin/main HEAD <pr-body-file>
```

This runs Guardian (`tools/pr_guardian.py`), `compileall`, both pytest suites, the
web build, and `docker compose config`. It must finish clean and Guardian must
report PASS or PASS_WITH_WARNINGS. If Guardian BLOCKs, fix the cause (Step 3) and
re-run — do not proceed.

If you only need Guardian (not the full suite), run it directly:

```bash
python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file <pr-body-file>
```

### Step 5 — Write the PR body

The PR body must carry the verification metadata Guardian checks for, as plain
`Field: value` lines:

```
Verification Status: Verified
Verification Level: Level 1
Verification Method: <how you verified — commands run>
Evidence: <concrete output / results>
Limitations: <what was not covered>
Required Next Verifier: <who / what verifies next>
```

See aos-change-control for the meaning of each level and finding code.

### Step 6 — Push and open the PR (explicit approval required)

Only after the operator has said to open the PR:

```bash
git push -u origin laptop/<ticket-slug>
gh pr create --base main --title "<TICKET-ID>: <summary>" --body-file <pr-body-file>
```

Never run `gh pr create` on your own initiative. If approval has not been given,
stop after Step 5 and report that the branch is ready to push.

### Step 7 — Watch checks

```bash
gh pr checks --watch
gh pr view --json state,mergeable,mergeStateStatus,statusCheckRollup
```

Always read merge state fresh from `gh` — never assert it from memory. Other
sessions commit to the same repos and `main` moves. If CI fails, fix the cause,
record a lesson (Step 3 guardrail), push, and re-watch.

### Step 8 — Merge gate (human merges; this skill does not)

When CI is green AND Guardian is PASS/PASS_WITH_WARNINGS, post the Manual Merge
Gate comment pinned to the exact head SHA (the private free-plan repo cannot
enforce required status checks — docs/BRANCH_PROTECTION.md), then hand off to the
operator to merge:

```bash
HEAD_SHA="$(git rev-parse HEAD)"
gh pr comment <pr#> --body "Manual Merge Gate — verified at ${HEAD_SHA}: CI green, Guardian PASS."
```

Do NOT run `gh pr merge`. The human operator performs the merge.

### Step 9 — Post-merge

After the operator merges:

```bash
git checkout main
git pull --ff-only origin main
scripts/post_merge_validation.sh origin/main
```

Reconcile state docs and lessons per aos-docs-and-lessons.

## 5. One-line summary

Sync main → branch → commit → `scripts/pre_pr_guardian.sh` → (on approval) push +
`gh pr create` → watch checks → post the SHA-pinned Manual Merge Gate → operator
merges → `post_merge_validation.sh`. Never open a PR without approval; never merge
without green + Guardian PASS + the gate comment.
