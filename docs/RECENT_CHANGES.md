# Recent Changes

## Purpose

This file gives new sessions a quick chronological view of what changed recently.

It is not a replacement for Git history. It is a human-readable coordination log.

## 2026-07-05

### Merged

- PR #14: AOS-RUNTIME-002 — Repository Scanner MVP (merge commit `856e5ff`). Scanner extended with structured manifests/docker_files/ci_files with kinds, folder_structure with depth, summary block, structured risk_signals (severity/code/path/message), primary language hints, expanded ignore list pruned before descent, MAX_FILES truncation guard, deterministic sorted traversal, no timestamps, strict superset of legacy report keys. Tests extended to 11 scanner tests (16 API tests total). `.gitignore` gained `archetypeos_dev.db`. Added `docs/REPOSITORY_SCANNER.md`.
- PR #15: Post-merge state reconciliation for AOS-RUNTIME-002.
- PR #21: AOS-PROC-001 — Build Process Hardening (merge commit `783f329`): PR Guardian acceptance-evidence enforcement for code-path PRs, a shared API test fixture, 4 new scan-endpoint integration tests, pinned dev toolchain (ruff==0.8.6, pytest==8.3.4, Python 3.12), RFC-0003 work-package specs, `.archetype/work/` specs, PR Guardian merge-gate and acceptance-evidence documentation, scanner runtime-enforcement note. First merge executed under the Manual Merge Gate. Verified at Level 3 (CI run 28728454334, all 5 jobs green).

### Also Merged

- PR #22: Post-merge state reconciliation for AOS-PROC-001.
- PR #23: AOS-KNOW-001 — Knowledge Vault Seed (merge commit `87fa769`): vault built out to the full RFC-0002 / `docs/KNOWLEDGE_VAULT_STRUCTURE.md` structure, `hot.md`/`index.md`/`overview.md`/`log.md` refreshed with current content, `.manifest.json` updated, `KnowledgePage` API read path explicitly deferred. Verified at Level 3 (CI run 28728964219, all 5 jobs green).

### Also Merged (later on 2026-07-05)

- PR #24: Post-merge state reconciliation for AOS-KNOW-001.
- PR #25: AOS-ARCH-001 — Architecture Spine Graph API (merge commit `b9b3024`): graph query endpoint with repository filter, node/edge manual-correction PATCH endpoints, and rescan upsert preserving node ids and corrections; 5 new integration tests (25 API tests total). Verified at Level 3 (CI run 28729930724, all 5 jobs green).

### Important Notes

- Verification: Verified at Level 3. GitHub CI green on both PR heads (runs 28726472816 and 28726897393, all 5 jobs including PR Guardian and the compose smoke test), plus local ruff/compileall/pytest and a correct self-scan of the ArchetypeOS repo.
- GitHub Actions does run on this private repo; what the plan lacks is enforceable required status checks, so merge gating stays manual via the local guardian and Orchestrator review.
- Plane is back online. The `ArchetypeOS` Plane project (AOS) has been seeded with 12 labels, default states, and work items AOS-1..AOS-9.
- GitHub issues #16-#20 were briefly opened to mirror the Plane seed and have been closed as migrated to Plane.
- Plane Modules, Cycles, Pages, Intake, and Views were enabled in Project Settings; all 10 epic Modules and the "Sprint 2 — Operating Loop" cycle are now populated.
- Workstation access CONFIRMED: `teevee-1` can run Docker/WSL via Tailscale — AOS-LOCAL-001 (Plane AOS-7) is unblocked. Plane back online and fully synced (AOS-3, AOS-5 Done).

### Added Recently

- `docs/REPOSITORY_SCANNER.md`
- `docs/rfc/RFC-0003-Work-Package-Specs.md`
- `.archetype/work/TEMPLATE.md`, `.archetype/work/AOS-PROC-001.md`, `.archetype/work/AOS-KNOW-001.md`

### Current Branch

- `claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` after PR #15 merged)

### Also Merged (later on 2026-07-05, continued)

- PR #26: Post-merge state reconciliation for AOS-ARCH-001; cleared Plane and workstation blockers.
- PR #27: AOS-CTRL-001 — Engineering Control Tower first dashboard surface (merge commit `32399e0`): `GET /repositories/{id}/dna` endpoint + 3 tests; dashboard rebuilt (project create/select, repository register/scan, stored scan summary, architecture counts, per-section error isolation). Verified at Level 4 — CI run 28730415566 all green plus headless-Chromium drive (10/10 checks).

### Also Merged (continued)

- PR #28: Post-merge state reconciliation for AOS-CTRL-001.
- PR #29: AOS-RUNTIME-003 — Scan persistence and history (merge commit `7697265`): versioned scan artifact files fixing the rescan overwrite bug, scan history list and stored-report retrieval endpoints; 4 new tests (32 API tests total). Verified at Level 3 (CI run 28730851673, all 5 jobs green).

### Also Merged (final batch)

- PR #30: AOS-PLANE-001 — Plane board sync discipline (merge commit `12dc5f7`): Sync Discipline + Board ID Registry. Verified at Level 3 (CI run 28731234910, all 5 jobs green).
- PR #31: exec-bit fix for shell scripts (AOS-LOCAL-001 finding 1).

### Sprint 2 Closed / Sprint 3 Opened

- PR #32 merged: AOS-LOCAL-001 Level 4 handoff + remediations — Sprint 2 complete, AOS-1..AOS-9 all Done.
- Sprint 3 — v0.1 Completion opened in Plane (cycle `9d9c2fd6-3305-419a-a5e8-0c6d4d3c058b`): AOS-6 scanner-informed guardian (in progress), AOS-10 decision/research artifacts, AOS-11 nightly digest, AOS-12 Alpha Review capstone.

### Sprint 3 Merged

- PR #33: AOS-PRG-002 — scanner-informed guardian (merge commit `5f0cfdc`): path-based secret/.env BLOCKs, MISSING_TESTS and ecosystem WARNs, --scan-report input + stdlib-only in-repo scan fallback with graceful degradation; 8 new tests (40 total). Verified at Level 3 — the CI guardian job executed the new code live on its own PR.

### Sprint 3 Merged (continued)

- PR #34: AOS-DEC-001 — decision/research artifacts (merge commit `fe158fd`): nine create/list/read routes, evidence-required recommendations (422), validated research→decision links as typed evidence entries, Decisions & Research dashboard section; 6 new tests (46 total). Verified at Level 4 (CI run 28742814441 + 7/7 browser drive). Phase 5 scope-lock criteria closed.

### Sprint 3 Merged (micro)

- PR #35: `/guardian` command (`.claude/commands/guardian.md`) — one shared guardian invocation for local, remote, and workstation sessions; dogfooded live in-session before merge (merge commit `c006d35`).

### Sprint 3 Merged (continued 2)

- PR #36: AOS-LEARN-001 — nightly learning digest, manual run (merge commit `8b39e67`): POST /projects/{id}/digests with deterministic aggregation (changes, repeated tasks, draft-only recommendations from four rules), list/read endpoints, dashboard Run Digest section; 6 new tests (52 total). Verified at Level 4 (CI run 28743687095 + 7/7 browser drive). Phase 7 scope-lock criteria closed.

### Sprint 3 Closed — v0.1 COMPLETE

- PR #37: AOS-ALPHA-001 — Phase 10 Alpha Review (merge commit `74c2406`): ArchetypeOS ran its full v0.1 loop against its own repository through the public API — two self-scans, DNA, architecture graph, decisions from live findings (incl. the /health-without-Redis 500), digest that caught a genuinely unlinked decision, end-to-end worker job via real Redis, guardian self-run (two real first-pass BLOCKs on its own PR, fixed not overridden). Artifact: `docs/ALPHA_REVIEW_V0_1.md` + `.archetype/alpha/` captures. Verified at Level 4 (CI run 28744117867 + the live self-evaluation). **Sprint 3 and v0.1 are complete**: AOS-1..AOS-12 all Done in Plane; all 11 v0.1 acceptance criteria assessed Met.

### AOS-LOCAL-001 Executed

- Operator ran the Level 4 runbook on `teevee-1` (Windows 11 + WSL 2): 6/6 services healthy, `/health` all true with real Redis (first time), dashboard-driven scan loop, two versioned scan artifacts, read-only mount probe rejected with "Read-only file system". Five findings recorded (`.archetype/work/AOS-LOCAL-001.md`); remediations: PR #31 (exec bit) and this branch (hermetic tests, `.env.example` port guidance).

### Sprint 4 Opened — Self-Healing & Learning Loop

Operator-approved principle: every PR, learning moment, and failure ties back into the loops; the guardian and the system itself get better as we go. Plane cycle `b0547f2d` with AOS-13 (/health fix), AOS-14 (Learning Feedback Loop, RFC-0004), AOS-15 (guardian evolution).

### Sprint 4 Merged

- PR #39: AOS-RUNTIME-004 — /health graceful degradation (merge commit `2b8febf`): per-probe guarding, 200 `degraded` instead of 500, 3 new tests (55 total), conftest Redis pinned to a dead port. Verified at Level 4 — CI exercised both states (API job = degraded path, compose smoke = healthy path) plus Orchestrator dual live probes. Alpha finding #1 closed (LES-005).

### Sprint 4 Merged (continued)

- PR #40: AOS-LEARN-002 — Learning Feedback Loop Phase 1, RFC-0004 (merge commit `e8527b9`): lessons contract + `knowledge/wiki/lessons/` registry seeded with the 7 real Sprint 3–4 events, CLAUDE.md recording rule, capability map Layer 8 entry. Verified at Level 2 (docs-only; CI run 28747618699 all green).

### Sprint 4 Closed

- PR #41: AOS-PRG-003 — guardian evolution (merge commit `98914f7`): metadata errors teach their fix (LES-003), accepted-warnings registry with expiry (LES-006, web-tests entry expires 2026-08-01), guardian changes require lessons, overrides require LES citations; 10 new tests (65 total). Verified at Level 3 — the CI guardian job ran the evolved code live on its own PR. **Sprint 4 (Self-Healing & Learning Loop) complete: PRs #39, #40, #41.**

### Sprint 4 Closed / Orchestrator Handoff

- PR #42: AOS-ORCH-004 — Sprint 4 close-out + Orchestrator Handoff Pack (merge commit `74e9370`): `docs/ORCHESTRATOR_PLAYBOOK.md`, committed `scripts/web_drive/` harness, Board ID Registry backfill (Sprints 3–4), HANDOFF transition section, LES-008. Verified at Level 2 (CI run 28748558659 all green). Orchestration handed from Fable 5 to Opus 4.8 (same container, model switch).

### Sprint 5 Opened — Enforcement & Foundations

Cycle `8bc59801`. Operator-approved order: AOS-16 web tests (deadline 2026-08-01) → AOS-17 Alembic → AOS-18 worker pipeline; AOS-21 second repo parallel. First sprint under the Opus 4.8 orchestrator; Board ID Registry backfilled with AOS-16..23 (UUIDs fetched from Plane, LES-008).

### Sprint 5 Merged

- PR #43: AOS-WEB-001 — Playwright e2e suite, enforced (merge commit `821171e`): the `scripts/web_drive/` seed corpus promoted to a real `@playwright/test` suite at `apps/web/e2e/` (3 specs), a new CI `web-e2e` job running it headless on ubuntu, and a guardian evolution (`web-tests-not-enforced` fires only on web source without an `apps/web/e2e/` change; accepted-warnings retired to `[]`). Portable browser resolution via a `PW_LOCAL_CHROMIUM` env seam. Verified at Level 4 — CI run 28750193960 all 6 jobs green + Orchestrator's own headless run (3/3). LES-006 deadline closed 26 days early; LES-009 recorded.

### Current Work

AOS-ALEMBIC-001 in review on this branch — Alembic adopted with a model-driven baseline migration (`apps/api/alembic/versions/0001_baseline.py`) reproducing the current 20-table schema exactly (no schema change; the no-drift autogenerate probe emits zero schema ops). The api container entrypoint (`docker-entrypoint.sh`) runs `alembic upgrade head` before uvicorn and hard-fails on migration error, so a broken migration is surfaced by compose-smoke rather than masked; `init_db()` create_all stays as a sqlite-dev safety net. Migration discipline (incl. the one-time `alembic stamp head` for teevee-1's populated DB) documented in `docs/DATABASE_MIGRATIONS.md`. Orchestrator independently verified the sqlite round-trip (upgrade→21 tables, no-drift, downgrade→clean); 67 API + 1 worker green. Unblocks the schema-dependent packages.

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