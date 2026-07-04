# Nightly Self Learning Loop

## Purpose

The Nightly Self Learning Loop is the eval, learning, and healing cycle for ArchetypeOS.

It runs on a schedule through cron, n8n, or the ArchetypeOS job scheduler.

## Mission

At the end of each day, ArchetypeOS should consume the day's engineering activity, detect friction, compare code changes, and recommend improvements.

## Inputs

- Conversation summaries
- Voice inbox items
- Git diffs
- Pull requests
- Issues
- Commit messages
- Test results
- Build logs
- PR Guardian reports
- Agent outputs
- Research notes
- New documentation
- User gripes and repeated hardships
- Repeated manual tasks

## Analysis Tasks

- Summarize daily engineering activity
- Detect repeated pain points
- Detect repeated tasks
- Compare repository diffs
- Identify undocumented changes
- Identify stale decisions
- Identify missing tests
- Identify missing docs
- Identify possible skills to create
- Identify possible MCPs to add
- Identify workflow automations
- Identify reusable modules
- Identify risks introduced during the day

## Outputs

- Daily engineering digest
- Recommended skills
- Recommended agents
- Recommended MCPs
- Recommended docs updates
- Recommended tests
- Recommended refactors
- Recommended research tasks
- Recommended automations
- PR Guardian follow-up
- Knowledge graph updates

## Skill Recommendation Examples

If the same task repeats multiple times, recommend a skill.

Examples:

- GitHub PR review skill
- Docker Compose debug skill
- FastAPI scaffold skill
- Architecture graph update skill
- Documentation freshness skill
- Voice note triage skill
- MCP evaluation skill

## Safety

The nightly loop should not directly modify code by default.

Allowed by default:

- create reports
- create drafts
- create recommendations
- create issue candidates
- update internal knowledge queue

Requires approval:

- file writes
- commits
- PRs
- dependency changes
- infrastructure changes
- external messages

## Cadence

Recommended schedule:

- nightly local review
- weekly portfolio review
- monthly evolution review

## Final Principle

Every day of work should make the portfolio smarter than it was yesterday.
