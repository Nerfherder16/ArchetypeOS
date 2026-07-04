# WSL Windows 11 Runtime Target

## Status

Accepted first runtime target.

## Purpose

This document defines the first practical runtime target for ArchetypeOS.

The target is a Windows 11 workstation using WSL 2 with Ubuntu.

## Target Environment

- Host: Windows 11
- Runtime: WSL 2 Ubuntu
- Containers: Docker Desktop with WSL integration, or Docker Engine inside WSL if explicitly chosen later
- Editor: VS Code connected to WSL
- Git: inside WSL
- Repositories: stored inside the WSL Linux filesystem
- Browser: Windows host browser consuming the web dashboard

## Why WSL First

WSL is the right first target because it matches the user's current development environment and avoids premature server operations.

Benefits:

- familiar Windows workstation
- Linux-compatible toolchain
- good Docker workflow
- VS Code support
- lower operational burden than Proxmox or CasaOS for v0.1
- easier local verification once power and workstation access are restored

## Filesystem Rule

Keep active repositories inside the WSL filesystem, not under `/mnt/c`.

Recommended path:

```text
~/code/ArchetypeOS
~/code/worktrees
~/code/repositories
```

Reason: Linux filesystem operations are generally more reliable and performant for Linux development workflows than crossing the Windows filesystem boundary.

## Access Pattern

From Windows, access files through VS Code Remote WSL or the WSL network path when needed.

From ArchetypeOS, treat WSL paths as canonical.

## Docker Rule

Use Docker through WSL integration.

Do not treat Docker Desktop, CasaOS, Portainer, or Proxmox as primary v0.1 dependencies.

They can return later as deployment targets.

## Worktree Layout

Use one work package per branch and one isolated worktree.

Recommended layout:

```text
~/code/ArchetypeOS
~/code/archetypeos-worktrees/aos-runtime-002-repository-scanner
~/code/archetypeos-worktrees/aos-ci-004-guardian-hardening
```

## Repository Mounts

External repositories scanned by ArchetypeOS should be mounted read-only by default.

Suggested local path:

```text
~/code/repositories/<repo-name>
```

## First Local Verification Goal

When local access returns, the first Level 2 verification task is:

```text
git clone https://github.com/Nerfherder16/ArchetypeOS.git
cd ArchetypeOS
cp .env.example .env
docker compose config
docker compose up --build
scripts/pre_pr_guardian.sh
```

Record exact command output in the handoff.

## Deferred Runtime Targets

- CasaOS
- Portainer
- Proxmox VM or LXC
- dedicated GPU node
- cloud deployment
- public appliance image

These are deferred until the WSL target is verified.

## Acceptance Criteria

The WSL runtime target is complete when:

- Docker Compose runs from WSL
- API health endpoint responds
- web dashboard loads from Windows browser
- worker starts and reports healthy behavior
- Postgres and Redis are reachable only as intended
- local pre-PR verification can run
- repository scan can read a mounted repository read-only

## Principle

Prove ArchetypeOS on one developer workstation before expanding to homelab, cloud, or distributed runtime.