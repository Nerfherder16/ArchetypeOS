# App Creation Loop

## Purpose

This document defines the first design for the ArchetypeOS application creation loop.

The goal is not to let an agent write code immediately. The goal is to create a governed engineering loop that can turn an idea into a verified product increment.

## Loop

```text
Idea
-> Intake
-> Research
-> Architecture
-> Technology Fitness
-> Plan
-> Work Packages
-> Branch Isolation
-> Build
-> Verification
-> PR Monitoring
-> Merge
-> Knowledge Update
-> Roadmap Update
```

## Required Gates

Before build:

- scope is clear
- acceptance criteria exist
- risks are known
- owner agent is assigned
- branch/worktree is isolated

Before merge:

- verification status is valid
- CI is current for the head SHA
- PR Guardian passes
- state files are updated
- handoff is durable

After merge:

- lessons are captured
- knowledge artifacts are updated
- next task is generated

## Minimum Viable Loop

For v0.1, the minimum loop is:

```text
Work Package -> Branch -> PR -> CI -> Verification Handoff -> Merge -> State Update
```

## Do Not Implement Yet

Do not implement full application creation until repository scanning, knowledge vault, and the control tower are usable.

## Final Judgment

The loop is the product. Code generation is only one stage inside the loop.