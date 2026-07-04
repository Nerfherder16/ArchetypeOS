# Verification Protocol

## Purpose

The Verification Protocol defines how ArchetypeOS agents prove that work has been checked before it is handed off, reviewed, or merged.

Verification is an engineering artifact. It must be planned, executed when possible, recorded with evidence, and escalated when the available runtime cannot verify the work directly.

## Core Rule

No agent may claim work is complete unless verification has occurred or the absence of verification has been explicitly recorded.

The only allowed verification states are:

- `Verified`
- `Verified with warnings`
- `Verification pending`
- `Verification unavailable`
- `Verification blocked`

Agents must not use informal substitutes such as "done", "looks good", "probably fine", or "validated" without one of the states above.

## Verification Levels

### Level 0: Static Reasoning

Use when the work can only be assessed by reading and reasoning.

Examples:

- documentation
- RFCs
- ADRs
- architecture notes
- governance updates

Evidence examples:

- files inspected
- docs changed
- reasoning summary
- limitations

### Level 1: Repository Verification

Use when repository state can be inspected but commands cannot be executed.

Examples:

- inspect files
- inspect diffs
- inspect commits
- inspect pull requests
- inspect workflow definitions
- inspect PR Guardian rules

Evidence examples:

- changed file list
- PR URL
- commit SHA
- diff summary
- workflow names

### Level 2: Local Execution

Use when the agent can run repository commands in a local or attached execution environment.

Examples:

```bash
scripts/pre_pr_guardian.sh
pytest
npm run build
docker compose config
docker compose up
ruff check
python -m compileall
```

Evidence examples:

- command
- exit code
- relevant output
- environment notes

### Level 3: GitHub CI Verification

Use when GitHub Actions or repository-hosted checks can verify the work.

Examples:

- workflow runs
- status checks
- artifacts
- PR Guardian
- smoke tests

Evidence examples:

- workflow run URL or ID
- check names
- check conclusions
- artifact names
- PR Guardian verdict

### Level 4: Runtime Verification

Use when a running system can prove behavior.

Examples:

- API responds
- Docker service is healthy
- web app loads
- database connection succeeds
- worker processes a job
- repository mount remains read-only

Evidence examples:

- endpoint response
- container health status
- log excerpt
- smoke test result
- runtime URL or local command

### Level 5: Human Verification

Use when judgment, risk acceptance, or product intent cannot be fully automated.

Examples:

- architecture approval
- security approval
- UX approval
- business logic approval
- scope exception approval
- destructive or high-impact action approval

Evidence examples:

- reviewer name or role
- approval note
- issue or PR comment
- decision artifact
- remaining concerns

## Deterministic Decision Tree

Every agent must choose the highest available verification level that fits the work.

```text
Can local verification run?

YES
  -> Run relevant local checks.
  -> Record commands, exit codes, and outputs.
  -> If checks pass, report Verified or Verified with warnings.
  -> If checks fail, report Verification blocked.

NO
  -> Can GitHub CI verify this work?

     YES
       -> Open or update PR.
       -> Wait for CI when the runtime can observe it.
       -> Record workflow/check results.
       -> If CI is still queued or not visible, report Verification pending.
       -> If CI passes, report Verified or Verified with warnings.
       -> If CI fails, report Verification blocked.

     NO
       -> Can repository inspection verify this work?

          YES
            -> Inspect files, diffs, commits, PR metadata, and workflow definitions.
            -> Record evidence and limitations.
            -> Report Verified with warnings when inspection is sufficient but execution was unavailable.
            -> Escalate Required Next Verifier.

          NO
            -> Report Verification unavailable or Verification blocked.
            -> Block merge until a verifier is available.
```

## Handoff Metadata

Every handoff must include:

```text
Verification Status:
Verification Level:
Verification Method:
Evidence:
Limitations:
Required Next Verifier:
```

Field definitions:

- `Verification Status`: one of the allowed states.
- `Verification Level`: highest level reached, from Level 0 through Level 5.
- `Verification Method`: the provider, command, workflow, inspection, or review used.
- `Evidence`: concrete output such as command results, commit SHA, PR URL, workflow status, or inspected files.
- `Limitations`: what could not be verified and why.
- `Required Next Verifier`: who or what must verify next, such as GitHub CI, Runtime Agent, Human Reviewer, Security Reviewer, or none.

## PR Metadata

Every pull request must include verification metadata in the PR body.

Required fields:

```text
Verification Status: Verified | Verified with warnings | Verification pending | Verification unavailable | Verification blocked
Verification Level: Level 0 | Level 1 | Level 2 | Level 3 | Level 4 | Level 5
Verification Method:
Evidence:
Limitations:
Required Next Verifier:
```

PR Guardian must block pull requests that omit required verification metadata or use an unsupported status.

## Merge Rule

A pull request may not merge when verification is `Verification unavailable` or `Verification blocked`.

A pull request with `Verification pending` may remain open but must not merge until the required next verifier records a stronger state.

A pull request with `Verified with warnings` may merge only when warnings are explicitly accepted in the PR body or reviewer comments.

## Verification Provider Interface

Verification providers are pluggable. Each provider must implement the same conceptual interface.

```text
Provider Name:
Capabilities:
Availability Check:
Inputs:
Execution Method:
Evidence Output:
Failure Mode:
Authority Level Required:
```

A provider receives a verification request and returns a standardized result:

```text
status:
level:
method:
evidence:
limitations:
required_next_verifier:
```

## Initial Providers

### Local CLI Provider

Runs local repository commands such as tests, lint, compile, and pre-PR scripts.

Authority requirement: repository read plus approved local command execution.

### GitHub Actions Provider

Uses GitHub workflow runs, required checks, PR Guardian, and artifacts.

Authority requirement: GitHub read for checks; write only when opening or updating PRs.

### Docker Provider

Runs Docker Compose validation, image builds, service startup, health checks, and smoke tests.

Authority requirement: local runtime execution approval.

### Runtime Health Provider

Checks live API, worker, web, database, and service health.

Authority requirement: runtime read access; elevated approval for production-like systems.

### Connector Inspection Provider

Uses repository, PR, commit, and diff inspection through constrained connectors when execution is unavailable.

Authority requirement: repository read access.

### Claude Code Provider

Delegates verification to Claude Code when it has repository and command execution access.

Authority requirement: provider-specific execution approval.

### Codex Provider

Delegates verification to Codex when it has repository and command execution access.

Authority requirement: provider-specific execution approval.

### Cursor Provider

Delegates verification to Cursor or IDE-integrated checks when available.

Authority requirement: local IDE execution approval.

### MCP Provider

Delegates verification to future MCP tools that expose tests, CI, runtime health, or environment inspection.

Authority requirement: tool-specific approval.

### Local GPU Node Provider

Runs heavier semantic checks, model-assisted reviews, or local LLM verification loops.

Authority requirement: local node execution approval; deterministic checks remain the base gate.

### Human Approval Provider

Records human judgment for architecture, security, UX, business logic, and high-impact decisions.

Authority requirement: human reviewer approval.

## Future Verification Engine

The future Verification Engine should automatically choose the best available verifier.

```text
Receive: Verify this work.

Discover available providers.
Rank providers by required level and evidence strength.

If Local CLI is available:
  run local verification.
Else if GitHub Actions is available:
  run or observe CI verification.
Else if Docker is available:
  run runtime/container verification.
Else if Connector Inspection is available:
  inspect repository, diff, PR, and workflows.
Else if Human Approval is required or no automated verifier is available:
  request human verification.
Else:
  return Verification unavailable.

Record standardized evidence.
Return standardized result.
```

Provider ranking should prefer deterministic execution over semantic review, and direct runtime proof over static inspection when behavior is being changed.

## Agent Responsibilities

Every agent must:

1. Identify the verification level required by the assigned work.
2. Attempt the strongest available verification method.
3. Record evidence and limitations.
4. Use only the allowed verification states.
5. Escalate to the required next verifier when it cannot complete verification.
6. Avoid claiming completion without verification metadata.

## Principle

Verification must be portable across local development, constrained runtimes, GitHub Actions, connectors, future MCP tools, and human review. Agents should ask for verification through a common protocol instead of inventing bespoke validation logic for each environment.
