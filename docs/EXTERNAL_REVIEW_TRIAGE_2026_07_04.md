# External Review Triage — 2026-07-04

## Status

Draft triage for PR #10 external architecture review.

## Purpose

This document converts the independent architecture review into actionable decisions.

The review is an assessment artifact, not automatic canon.

## Triage Categories

- Accept now
- Accept later
- Reject
- Already addressed
- Blocked by outage/resources

## Accepted Now

### State Reconciliation

Finding: state files can drift from git.

Decision: accept.

Action: reconcile state docs after each merge and later generate state from database and git instead of hand-editing.

### Local Verification Gap

Finding: local Level 2 verification is not yet proven.

Decision: accept with context.

Context: current blocker is power outage and unavailable local workstation.

Action: make WSL Windows 11 the first runtime target and record a local verification run when access returns.

### Security Defaults

Finding: default compose/security posture needs tightening before autonomy.

Decision: accept.

Action: add a security hardening work package before write-capable agents.

### Sandboxing Before Write-Capable Agents

Finding: autonomy requires process and credential isolation.

Decision: accept.

Action: add sandbox design before any write-capable autonomous agent.

### Close One Visible Loop

Finding: one working loop matters more than more design.

Decision: accept.

Action: prioritize repository scanner, graph/read endpoint, UI display, worker-backed scan, and verification handoff.

## Accepted Later

### Replace Markdown Coordination With Database

Decision: accept later.

Reason: markdown remains necessary while runtime is early and local systems are unavailable.

Future direction: database is canonical; markdown becomes generated recovery view.

### Thin OS Versus Full Runtime RFC

Decision: accept later.

Reason: the strategic question is real, but WSL runtime target and one visible loop come first.

### Provider Gateway And Eval Harness

Decision: accept later.

Reason: important before model-backed autonomy, but not before repository scanner and local runtime verification.

## Already Addressed Or Partially Addressed

### Branch Isolation

PR #8 added Branch Isolation / Worktree Protocol.

### PR Monitoring Skill

PR #7 added PR Monitoring skill.

### Operating Loop Planning

PR #9 added operating loop and Control Tower planning.

## Blocked By Outage Or Resources

### Plane Sync

Blocked until local Plane instance is available.

### Local Docker Verification

Blocked until Windows 11 workstation and local power return.

## Rejected For Now

### Stop All Documentation

Decision: reject as absolute rule.

Reason: documentation is still needed to record accepted course correction and runtime target.

Modified rule: no new aspirational engine docs until one visible loop is implemented.

## Course Correction

For the next build phase, prioritize:

1. WSL Windows 11 runtime target
2. State reconciliation after each merge
3. Security defaults
4. Repository scanner loop
5. Local Level 2 verification when access returns
6. Sandbox design before write-capable autonomy

## Principle

External review improves the project only after triage. It should not directly rewrite the roadmap without human and architectural judgment.