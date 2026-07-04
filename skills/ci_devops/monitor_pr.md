# Skill: PR Monitoring

## Purpose

PR Monitoring is a reusable CI / DevOps skill for independently verifying a pull request until it is ready for merge, returned for patching, or escalated.

## Owner

CI / DevOps Agent

## Inputs

- repository
- PR number
- current state docs
- verification protocol
- PR Guardian rules

## Steps

1. Read current state and active work.
2. Inspect PR metadata.
3. Inspect changed files.
4. Confirm the PR branch is current with `main`.
5. Inspect workflow runs for the PR head commit.
6. Inspect PR Guardian output.
7. Classify failures.
8. Produce a verification handoff.
9. Recommend one verdict: merge-ready, patch-required, blocked, or escalate.

## Required Output

- Verification Status
- Verification Method
- Evidence
- Limitations
- Required Next Verifier
- Merge Recommendation
- Assigned Follow-up Agent

## Authority

The CI / DevOps Agent may inspect, verify, rerun checks when permitted, and request changes.

The CI / DevOps Agent may not merge unless explicitly authorized by the Human Owner or Orchestrator.

## Principle

Builder agents should not self-certify. Independent verification protects the system.