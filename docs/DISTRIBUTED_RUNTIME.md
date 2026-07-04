# Distributed Runtime

## Purpose

The Distributed Runtime lets ArchetypeOS coordinate work across a local control plane, GPU inference nodes, developer workstations, GitHub, and future cloud services.

## Target Topology

```text
Control Plane
├── Web dashboard
├── API
├── Postgres
├── Redis
├── Worker
├── Knowledge graph
└── Agent orchestrator
    ├── Claude Code worker
    ├── RTX 3090 local LLM node
    ├── WSL developer workstation node
    └── GitHub PR Guardian
```

## Node Types

- control_plane
- gpu_inference
- developer_workstation
- github_runner
- research_worker

## Node Capabilities

- local_llm
- embeddings
- repo_scan
- claude_code
- test_runner
- pr_guardian
- report_generator
- graph_builder

## Communication

Start simple:

- HTTPS API
- node registration
- heartbeat
- polling jobs
- log streaming

Later:

- WebSockets
- Tailscale or WireGuard
- remote command sessions

## Safety

Nodes default to read-only. Write access is capability gated and requires explicit approval.

## Principle

The control plane decides and stores. Nodes execute declared capabilities.
