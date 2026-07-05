# RFC-0003 — Work Package Specs

## Status

Accepted for v0.1 foundation.

## Summary

Every work package gets a spec file in `.archetype/work/<TASK-ID>.md` before implementation starts.

## Problem

AOS-RUNTIME-002 was assigned as "add a repository scanner" while a scanner already existed on `main`. Nothing forced an agent to confirm current repository state before starting, so board language and code state drifted. There was also no standard place to record acceptance criteria before a PR is opened, so PR bodies varied in how they described evidence.

## Proposal

Before implementation starts, create `.archetype/work/<TASK-ID>.md` containing:

- Task ID / title
- Status
- Verified Baseline — current state of the code/docs the package touches, confirmed by inspection, not assumption
- In-Scope Files
- Out-of-Scope list
- Acceptance Criteria — checkable assertions, each with an `evidence:` pointer (test name, command, or CI job)
- Verification Plan
- Suggested Delegation

Delegation prompts handed to implementing agents are generated from the spec, not written ad hoc.

PR bodies must carry an `## Acceptance Evidence` section mapping each acceptance criterion to its evidence. For PRs touching code paths (`apps/api/app/`, `apps/worker/app/`, `apps/web/src/`), this section is enforced deterministically by PR Guardian (see `docs/PR_GUARDIAN.md`).

Each spec maps to a Plane work item (the live board) and a branch.

## Goals

- Force baseline verification before implementation starts.
- Give every task a single durable spec file agents and reviewers can read.
- Make acceptance criteria checkable, not aspirational.
- Let PR Guardian enforce evidence deterministically for code changes.

## Non-Goals

- replace Plane or the markdown fallback boards
- replace the Verification Protocol's handoff metadata
- generate delegation prompts automatically (future work)

## Acceptance Criteria

- `.archetype/work/TEMPLATE.md` exists with the required sections.
- At least one dogfood spec exists (`AOS-PROC-001`).
- `docs/PR_GUARDIAN.md` documents the acceptance-evidence check.

## Final Judge Verdict

Accepted.
