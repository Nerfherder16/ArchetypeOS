# Work Package Protocol

## Purpose

A Work Package is the standard handoff artifact for assigning work to agents.

It replaces vague prompts with structured, auditable task definitions.

## Required Fields

- ID
- Title
- Parent
- Owner
- Requested By
- Priority
- Status
- Objective
- Inputs
- Acceptance Criteria
- Authority
- Deliverables
- Verification Requirements
- On Success
- On Failure
- Dependencies
- Blocking
- Estimated Effort

## Example

ID: AOS-CI-003

Title: Babysit Runtime PR #5

Parent: AOS-RUNTIME-001

Owner: CI / DevOps Agent

Requested By: Chief Architect

Priority: High

Status: Assigned

Objective: Verify PR #5 until it reaches a merge-ready state.

Inputs:

- PR #5
- docs/VERIFICATION_PROTOCOL.md
- docs/PR_GUARDIAN.md

Acceptance Criteria:

- Branch is current with main
- All CI passes
- PR Guardian passes
- Verification report produced
- Merge recommendation issued

Authority:

- May inspect repository and CI
- May request changes
- May not merge

Deliverables:

- Verification report
- Updated handoff if required

On Success: Return control to Chief Architect.

On Failure: Create remediation tasks for owning domain agent.

Dependencies: PR #6 merged.

Blocking: Yes

Estimated Effort: 15-30 minutes

## Status Values

- Proposed
- Assigned
- In Progress
- Blocked
- Verification Pending
- Verified
- In Review
- Complete
- Deferred

## Work Package Lifecycle

Created -> Assigned -> Accepted by Agent -> In Progress -> Verification Requested -> Verified or Returned for Patch -> Handoff Produced -> Closed by Orchestrator

## Principle

A good work package lets a new agent start safely without reading a long conversation.