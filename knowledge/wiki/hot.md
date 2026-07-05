# Hot Memory

## Current Focus

Sprint 2 — Operating Loop. AOS-KNOW-001 — Knowledge Vault Seed is in progress (this package): building out the vault to the full RFC-0002 / `docs/KNOWLEDGE_VAULT_STRUCTURE.md` shape.

## Current Phase

The operating loop is proven: the repository scanner merged (PR #14, AOS-RUNTIME-002), the build process was hardened (PR #21, AOS-PROC-001), and the Plane board is live with AOS-1..AOS-9 seeded.

## Active Decisions

- Plane is the live board; the markdown state files remain the fallback and win on conflict until AOS-9 defines full sync discipline.
- Merges require the Manual Merge Gate (head-SHA-pinned verification comment) per `docs/PR_GUARDIAN.md`.
- Implementation work follows work-package specs (RFC-0003) in `.archetype/work/` before code changes.

## Recent Blockers

- Local WSL/Docker Level 2 verification on the user's workstation remains pending confirmation.

## Important Constraints

- Keep repository access read-only by default.
- Do not implement deferred automation or multi-user auth in v0.1.
- Document schema and architecture before implementation.
- Enforce acceptance evidence on code-path PRs (PR Guardian, per AOS-PROC-001).

## Top Links

- [[index]]
- `docs/CURRENT_STATE.md`
- `docs/ACTIVE_WORK.md`
- `.archetype/work/`
