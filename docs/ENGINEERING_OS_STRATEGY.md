# Engineering OS Strategy

## Status

Accepted direction for v0.1 planning.

## Purpose

This document clarifies what ArchetypeOS means by operating system.

ArchetypeOS should not replace Linux, Windows, GitHub, Docker, Plane, Obsidian, or Claude Code.

ArchetypeOS should coordinate them as an Engineering Intelligence Platform.

## Three OS Layers

### Platform OS

The platform OS is the real operating system.

For the first target, this is:

- Windows 11 host
- WSL 2 Ubuntu runtime
- Docker Desktop or Docker Engine integration

Linux remains responsible for processes, filesystems, networking, drivers, and containers.

### Runtime OS

The ArchetypeOS runtime is the application and service layer.

It owns:

- API
- worker
- database
- verification providers
- repository registry
- repository scanner
- knowledge store
- orchestration state
- provider adapters

### Engineering OS

The Engineering OS is the product thesis.

It schedules and governs engineering work:

- ideas
- research
- decisions
- work packages
- agents
- branches
- pull requests
- verification
- knowledge
- releases

## What ArchetypeOS Owns

ArchetypeOS should own the intelligence and governance layer:

- Repository Intelligence
- Research Intelligence
- Architecture Intelligence
- Decision Intelligence
- Verification Intelligence
- Knowledge Intelligence
- Agent Orchestration
- Engineering Memory
- Engineering Control Tower

## What ArchetypeOS Should Integrate

ArchetypeOS should integrate mature execution systems instead of rebuilding them prematurely:

- GitHub for repository, pull request, issue, and CI substrate
- Docker for runtime isolation
- WSL for local Linux development on Windows
- Claude Code or similar tools for coding execution
- Plane or GitHub Projects for PMO workflow
- Obsidian for optional human knowledge browsing
- local and cloud LLM providers for intelligence

## Engineering Compiler

The strategic core is the Engineering Compiler.

It transforms:

```text
Idea -> Research -> Requirements -> Architecture -> Roadmap -> Work Package -> Agent Assignment -> Branch -> Verification -> PR -> Merge -> Knowledge Update
```

Code generation is only one stage.

## Near-Term Implication

The next implementation should not attempt to become a Linux distribution, desktop shell, or replacement PMO.

The first runtime target is WSL on Windows 11. The first product proof is a local, verifiable engineering loop running inside WSL.

## Principle

ArchetypeOS is not a new kernel. It is an operating system for engineering work.