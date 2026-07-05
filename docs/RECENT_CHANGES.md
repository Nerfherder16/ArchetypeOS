# Recent Changes

## Purpose

This file gives new sessions a quick chronological view of what changed recently.

It is not a replacement for Git history. It is a human-readable coordination log.

## 2026-07-05

### Merged

- PR #14: AOS-RUNTIME-002 — Repository Scanner MVP (merge commit `856e5ff`). Scanner extended with structured manifests/docker_files/ci_files with kinds, folder_structure with depth, summary block, structured risk_signals (severity/code/path/message), primary language hints, expanded ignore list pruned before descent, MAX_FILES truncation guard, deterministic sorted traversal, no timestamps, strict superset of legacy report keys. Tests extended to 11 scanner tests (16 API tests total). `.gitignore` gained `archetypeos_dev.db`. Added `docs/REPOSITORY_SCANNER.md`.
- PR #15: Post-merge state reconciliation for AOS-RUNTIME-002.
- PR #21: AOS-PROC-001 — Build Process Hardening (merge commit `783f329`): PR Guardian acceptance-evidence enforcement for code-path PRs, a shared API test fixture, 4 new scan-endpoint integration tests, pinned dev toolchain (ruff==0.8.6, pytest==8.3.4, Python 3.12), RFC-0003 work-package specs, `.archetype/work/` specs, PR Guardian merge-gate and acceptance-evidence documentation, scanner runtime-enforcement note. First merge executed under the Manual Merge Gate. Verified at Level 3 (CI run 28728454334, all 5 jobs green).

### In Progress

- AOS-KNOW-001 — Knowledge Vault Seed: vault built out to the full RFC-0002 / `docs/KNOWLEDGE_VAULT_STRUCTURE.md` structure, `hot.md`/`index.md`/`overview.md`/`log.md` refreshed with current content, `.manifest.json` updated, `KnowledgePage` API read path explicitly deferred.

### Important Notes

- Verification: Verified at Level 3. GitHub CI green on both PR heads (runs 28726472816 and 28726897393, all 5 jobs including PR Guardian and the compose smoke test), plus local ruff/compileall/pytest and a correct self-scan of the ArchetypeOS repo.
- GitHub Actions does run on this private repo; what the plan lacks is enforceable required status checks, so merge gating stays manual via the local guardian and Orchestrator review.
- Plane is back online. The `ArchetypeOS` Plane project (AOS) has been seeded with 12 labels, default states, and work items AOS-1..AOS-9.
- GitHub issues #16-#20 were briefly opened to mirror the Plane seed and have been closed as migrated to Plane.
- Plane Modules, Cycles, Pages, Intake, and Views were enabled in Project Settings; all 10 epic Modules and the "Sprint 2 — Operating Loop" cycle are now populated.
- Local WSL/Docker Level 2 verification on the user's workstation remains pending confirmation.

### Added Recently

- `docs/REPOSITORY_SCANNER.md`
- `docs/rfc/RFC-0003-Work-Package-Specs.md`
- `.archetype/work/TEMPLATE.md`, `.archetype/work/AOS-PROC-001.md`, `.archetype/work/AOS-KNOW-001.md`

### Current Branch

- `claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` after PR #15 merged)

### Current Work

AOS-KNOW-001 — Knowledge Vault Seed (Plane AOS-3), in progress on this branch; PR to be opened.

### Why It Matters

The scanner is the foundation for Repository DNA and future architecture graph and PR Guardian work. AOS-PROC-001 hardens the build/PR process (evidence enforcement, test coverage, toolchain pins) and moves planning onto the now-live Plane board before AOS-KNOW-001 — Knowledge Vault Seed starts.

## 2026-07-04

### Merged

- PR #1: Runtime foundation
- PR #2: CI and deterministic PR Guardian
- PR #3: CI enforcement and branch protection documentation
- PR #5: Repository Registry MVP
- PR #6: Verification Protocol
- PR #7: Agent Communication Bus and PR Monitoring skill
- PR #8: Branch Isolation / Worktree Protocol
- PR #10: Independent Architecture Review artifact
- PR #11: Engineering OS Strategy and WSL Windows 11 Runtime Target
- PR #12: Operating Loop planning docs recovery

### Important Notes

- PR #9 was closed after branch conflicts; useful planning docs were recovered through PR #12.
- Backup branches preserve the old PR #9 head.
- Plane remains pinned/offline due to local power outage.
- Local WSL/Docker Level 2 verification remains blocked until power and workstation access return.
- GitHub plus markdown state files remain the fallback execution board.

### Added Recently

- `docs/AGENT_COMMUNICATION_BUS.md`
- `docs/WORK_PACKAGE_PROTOCOL.md`
- `skills/ci_devops/monitor_pr.md`
- `docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md`
- `docs/INDEPENDENT_ARCHITECTURE_REVIEW_V0_1.md`
- `docs/ENGINEERING_OS_STRATEGY.md`
- `docs/WSL_WIN11_RUNTIME_TARGET.md`
- `docs/EXTERNAL_REVIEW_TRIAGE_2026_07_04.md`
- `docs/ROADMAP_REVIEW.md`
- `docs/BORIS_CLAUDE_CODE_RESEARCH.md`
- `docs/APP_CREATION_LOOP.md`
- `docs/PLANE_PROJECT_BLUEPRINT.md`

### Current Branch

- `docs/state-reconciliation`

### Current Work

AOS-PMO-002 — State Reconciliation.

### Why It Matters

The repo must accurately describe its own state before implementation resumes. The next implementation task should be AOS-RUNTIME-002 — Repository Scanner MVP.

## Update Rule

Update this file after each meaningful merge or milestone.