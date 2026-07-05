# ArchetypeOS Overview

ArchetypeOS is an Engineering Intelligence Platform that helps engineers research, model, decide, build, validate, learn, and evolve software systems.

## What v0.1 Currently Proves

The v0.1 runtime proves the local control plane and first repository intelligence loop, end to end without advanced automation:

- **Registry** — repositories can be registered against a project (Repository Registry MVP, PR #5).
- **Read-only scan** — a registered repository can be scanned deterministically and read-only, producing structure, ecosystem, and risk-signal data (`docs/REPOSITORY_SCANNER.md`, PR #14). Enforced read-only both in code (no writes, no execution, no symlink following) and at the container runtime (`:ro` compose mount).
- **Repository DNA / graph draft** — scan output is persisted to `RepositoryDNA` and includes early `architecture_nodes` / `architecture_edges` that seed future architecture graph work.
- **Artifact** — each scan is serialized to a checksummed JSON artifact under the ArchetypeOS-owned artifact root, never inside the scanned repository.
- **Verification protocol** — a defined set of verification levels and statuses (`docs/VERIFICATION_PROTOCOL.md`) is applied to every work package, recorded in handoffs and PR bodies.
- **PR Guardian** — a deterministic pre-merge reviewer (`tools/pr_guardian.py`) checks scope, tests, docs, secrets, and — as of AOS-PROC-001 — acceptance evidence on code-path PRs; merges go through a Manual Merge Gate.
- **Plane board** — the `ArchetypeOS` Plane project is live (AOS-1..AOS-9, 10 epic modules, the Sprint 2 cycle), with the markdown state files as the fallback source of truth until AOS-9 defines full sync discipline.

## What's Next

- **Scan history** (AOS-RUNTIME-003) — persist scan results over time instead of a single latest snapshot.
- **Architecture graph API** (AOS-ARCH-001) — build the Architecture Spine Graph from scanner-derived nodes and edges.
- **Control tower** — the Engineering Control Tower / dashboard design exists but implementation is deferred until scanner and runtime data are richer.
- Knowledge distillation automation (raw/sources -> wiki pages) is out of scope for this seed package (AOS-KNOW-001) and remains future work per RFC-0002.
