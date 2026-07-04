# System Architecture

## Overview

ArchetypeOS is designed as a local-first distributed engineering intelligence system.

## Primary layers

### 1. Control Plane

The control plane owns the dashboard, API, project registry, job routing, agent registry, reports, release gates, and audit logs.

### 2. Intelligence Layer

The intelligence layer contains the engines that research, compare, evaluate, recommend, and explain.

### 3. Council Layer

The council layer contains specialized agents such as Research Librarian, Architecture Cartographer, Technology Fitness Judge, Security Agent, Compliance Agent, Design Intelligence Agent, External Repo Scout, PR Guardian, Builder, and Final Judge.

### 4. Execution Layer

The execution layer runs tools and models. Examples include Claude Code, local LLMs, deterministic scanners, GitHub tools, test runners, and report generators.

## Recommended local deployment

- Docker Compose
- CasaOS or Portainer
- Web dashboard
- FastAPI backend
- Python worker
- Postgres
- Redis
- Local volumes for data, reports, repositories, and knowledge cache

## Distributed nodes

ArchetypeOS should support remote nodes:

- GPU inference node on a gaming PC with RTX 3090
- Developer workstation node running WSL Ubuntu
- GitHub PR Guardian node
- Research worker node

Nodes should register capabilities and default to read-only operation.

## Safety model

- Read-only by default
- Explicit approval for writes
- Audit log for every job
- Path validation for repository access
- No committed secrets
- Human approval for destructive or production-impacting actions
