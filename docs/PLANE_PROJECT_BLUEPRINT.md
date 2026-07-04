# Plane Project Blueprint

## Purpose

This document defines the intended Plane structure for ArchetypeOS.

Plane is currently unavailable because the local instance is offline during a power outage. Until it returns, this document and the markdown state files are the fallback planning system.

## Project

Name: ArchetypeOS

## Epics

1. Foundation Runtime
2. CI / Verification / PR Guardian
3. Orchestration Engine
4. Agent Communication Bus
5. Repository Intelligence
6. Knowledge Vault
7. App Creation Loop
8. Dashboard / Operator Console
9. Plane Integration
10. Local Agent Runtime / Worktrees

## Sprint 2

Name: Operating Loop

Goal: prove that ArchetypeOS can manage work, agents, branches, verification, PRs, state, and the WSL runtime target before broader product expansion.

## Suggested Issues

- AOS-PMO-001 — Reconcile State Files
- AOS-RESEARCH-001 — Claude Code Workflow Research
- AOS-LOOP-001 — App Creation Loop Design
- AOS-CTRL-001 — Engineering Control Tower Design
- AOS-RUNTIME-002 — Repository Scanner MVP
- AOS-LOCAL-001 — WSL Windows 11 Local Verification

## Labels

- area/runtime
- area/frontend
- area/knowledge
- area/ci
- area/orchestration
- area/research
- area/local-runtime
- type/docs
- type/implementation
- type/verification
- status/blocked
- status/ready

## Rule

Every Plane issue should map to a work package and a branch.