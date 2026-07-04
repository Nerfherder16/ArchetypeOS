# Branch Isolation / Worktree Protocol

## Purpose

The Branch Isolation / Worktree Protocol defines how ArchetypeOS agents isolate work so parallel tasks do not corrupt each other, overwrite state, or create avoidable rebase conflicts.

The governing rule is:

```text
One work package = one branch = one isolated worktree.
```

A work package is any discrete assigned task, PR, RFC, implementation slice, documentation change, verification pass, or remediation package.

## Core Rule

Agents must not perform unrelated work on the same branch.

Agents must not reuse a dirty working tree for a different task.

Agents must not force-reset a branch without preserving the previous head.

Agents must not mark a PR ready-for-review until branch freshness and verification metadata are current.

## Why This Exists

ArchetypeOS is intended to support multiple agents working in parallel. Parallel work fails when agents share mutable state without isolation.

Common failure modes:

- one agent rebases another agent's work unexpectedly
- state docs conflict because multiple tasks edited the same files from stale bases
- a connector force-reset temporarily closes a PR because the branch has no diff
- CI verifies an old merge ref instead of the current branch head
- review agents rely on stale PR metadata
- runtime agents modify governance docs while implementation agents are still testing

This protocol converts those risks into mandatory branch, worktree, and connector handling rules.

## Local Agent Protocol

When local Git access is available, each work package must use its own worktree.

Recommended layout:

```text
repo/
  ArchetypeOS/                         # main checkout, usually clean
  worktrees/
    aos-runtime-001-registry/
    aos-orch-002-branch-isolation/
    aos-ci-001-verification-protocol/
```

Recommended commands:

```bash
git fetch origin

git worktree add ../worktrees/aos-orch-002-branch-isolation -b docs/branch-isolation-worktree-protocol origin/main
cd ../worktrees/aos-orch-002-branch-isolation
```

Before starting work:

```bash
git status --short
git branch --show-current
git log --oneline --decorate -5
```

Before opening or marking a PR ready:

```bash
git fetch origin
git status --short
git rev-list --left-right --count origin/main...HEAD
git merge-base HEAD origin/main
```

Expected result:

- working tree clean except intended changes
- branch name matches task
- branch is not behind `origin/main`
- PR body contains Verification Protocol metadata
- CI/PR Guardian evidence is current for the final head SHA

## Required Branch Rules

Every work package must have exactly one active task branch.

Branch naming should encode the owner/domain and task:

```text
docs/branch-isolation-worktree-protocol
codex/repository-registry-mvp
ci/verification-protocol
runtime/repository-scanner-mvp
knowledge/vault-seed
```

Allowed branch reuse:

- continue the same unfinished work package
- patch review feedback for the same PR
- rerun verification or CI fixes for the same PR

Disallowed branch reuse:

- starting a new task on an old branch
- mixing runtime implementation with unrelated governance changes
- adding opportunistic features while fixing CI
- using `main` as a working branch

## Required Worktree Rules

Each local worktree must map to one branch and one work package.

A local agent may keep multiple worktrees, but each worktree must stay scoped.

Do not switch unrelated branches inside a task worktree unless explicitly repairing that worktree.

Do not run broad cleanup commands from a shared checkout when another task is in progress.

Do not copy untracked runtime artifacts between worktrees.

## State File Discipline

State files are high-conflict files. Treat them as coordination artifacts, not scratchpads.

Common state files:

- `docs/CURRENT_STATE.md`
- `docs/ACTIVE_WORK.md`
- `docs/HANDOFF.md`
- `docs/RECENT_CHANGES.md`
- `docs/SESSION_BOOTSTRAP.md`
- `docs/CAPABILITY_MAP.md`

Rules:

1. Update state files only for the current task.
2. Preserve newer merged state when rebasing.
3. Do not revert another merged PR's state updates.
4. If a state file is stale after another PR merges, reconcile it intentionally.
5. Record verification metadata after every meaningful state transition.

## Connector Fallback Protocol

Some agents, including ChatGPT connector sessions, may not have local Git execution or filesystem worktrees.

When local worktrees are unavailable, the connector fallback is:

```text
one work package = one branch = one logical worktree
```

The branch is the isolation boundary.

### Connector Rule 1: One Branch Per Task

Create or reuse only the branch assigned to the work package.

Do not patch unrelated open PR branches.

Do not use a connector session as a general-purpose shared worktree.

### Connector Rule 2: Preserve Backup Head Before Force/Reset

Before any connector-backed force reset, preserve the prior branch head.

Required backup naming pattern:

```text
<original-branch>-backup-<short-sha>
```

Example:

```text
codex/repository-registry-mvp-backup-d811534
```

Record the backup branch in:

- the PR body
- `docs/HANDOFF.md`
- verification evidence

Never force-reset without a recovery reference.

### Connector Rule 3: Prefer Reapply Over Blind Merge When Conflicts Are Likely

If the connector cannot perform a real local rebase and conflicts are likely, use this sequence:

1. preserve backup head
2. reset task branch to current `main`
3. reapply only the intended task files
4. inspect diff against `main`
5. update PR body and state docs
6. wait for fresh CI

This is a connector-backed rebase substitute, not a normal local rebase.

### Connector Rule 4: Expect Temporary PR Closure Risk

If a connector resets a branch to `main`, GitHub may temporarily close the PR because the branch has no diff.

Mitigation:

1. reapply task changes immediately
2. reopen the PR if GitHub closed it
3. verify the PR head SHA
4. record the event in the handoff if it occurred

### Connector Rule 5: Verify Branch Freshness Before Ready-for-Review

Before marking any PR ready-for-review, verify:

```text
base: main
head: task branch
behind_by: 0
merge base: current main or expected base
CI run: current head SHA
PR body: active Verification Protocol metadata
```

If the branch is behind `main`, it is not ready-for-review.

If CI passed on an older head SHA, it is not verified.

### Connector Rule 6: Use Local Agents for Heavy Edits

Use local agents for:

- large refactors
- multi-file implementation work
- conflict-heavy rebases
- generated code
- dependency changes
- migrations
- Docker/runtime debugging
- test-driven implementation loops

Connector sessions should prefer:

- orchestration
- review
- PR metadata repair
- documentation edits
- state reconciliation
- CI observation
- verification handoffs

### Connector Rule 7: Use ChatGPT Connector for Review and Orchestration

The ChatGPT connector is strongest as an orchestration and review layer.

Preferred connector responsibilities:

- read current repository state
- inspect PR diffs and comments
- verify CI/PR Guardian status
- update PR descriptions and handoff metadata
- open documentation/governance PRs
- assign remediation to local/runtime agents
- preserve audit trail through PR comments

Do not use connector-only editing for heavy implementation when a local worktree agent can do safer deterministic execution.

## Ready-for-Review Gate

A PR may be marked ready-for-review only when all are true:

- branch is not behind `main`
- PR body contains required Verification Protocol metadata
- intended files match the work package scope
- no unrelated opportunistic changes are present
- fresh CI has been started or completed for the current head SHA
- stale verification evidence has been removed or replaced
- Required Next Verifier is accurate

## Merge Gate

A PR may merge only when:

- Verification Status is `Verified`, or
- Verification Status is `Verified with warnings` and warnings are explicitly accepted by the Orchestrator
- PR Guardian and required CI jobs pass for the current head SHA
- branch isolation evidence is sufficient for the risk level

`Verification pending`, `Verification unavailable`, and `Verification blocked` must not merge.

## Handoff Requirements

Every handoff for branch/worktree activity must include:

```text
Work package:
Branch:
Worktree or connector fallback used:
Base ref:
Head SHA:
Backup head, if any:
Freshness check:
Verification Status:
Verification Level:
Verification Method:
Evidence:
Limitations:
Required Next Verifier:
```

## Agent Responsibilities

### Orchestrator

Owns sequencing, dependency order, and whether a PR may proceed when multiple open branches touch state files.

### Runtime Agent

Uses local worktrees for implementation-heavy API, worker, database, Docker, and runtime tasks.

### CI / DevOps Agent

Verifies branch freshness, CI status, PR Guardian output, backup-head preservation, and merge readiness.

### Knowledge Agent

Uses isolated branches for vault/schema changes and avoids mixing knowledge updates with runtime edits.

### ChatGPT Connector Agent

Coordinates and reviews through GitHub connector actions, preserving audit trail and escalating heavy edits to local agents.

## Principle

Branch isolation is the minimum viable operating system for multi-agent engineering.

Worktrees are the local safety mechanism. Branches are the connector safety mechanism. Verification is the release safety mechanism.
