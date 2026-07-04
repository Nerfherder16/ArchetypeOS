# Engineering Control Tower

## Purpose

The Engineering Control Tower is the operational view for ArchetypeOS.

It is not just a dashboard. It is the command view for projects, agents, work packages, PRs, verification, risks, and roadmap health.

## Core Panels

- Current State
- Active Work
- Sprint Progress
- Agent Queue
- PR Queue
- Verification Queue
- CI Health
- Risk Register
- Knowledge Updates
- Roadmap Dependencies
- Next Recommended Task

## v0.1 Panels

Start with:

1. Current State
2. Active Work
3. PR Queue
4. Verification Queue
5. Next Recommended Task

## Data Sources

- docs/CURRENT_STATE.md
- docs/ACTIVE_WORK.md
- docs/HANDOFF.md
- docs/RECENT_CHANGES.md
- GitHub PRs
- GitHub Actions
- PR Guardian output
- future Plane sync
- future Postgres runtime records

## Operating Rule

The Control Tower should display the same truth that agents use.

If a user can see a task as ready, an agent should be able to consume that same task as a work package.

## Final Judgment

The Control Tower is the user interface for orchestration. It should come before advanced app generation features.