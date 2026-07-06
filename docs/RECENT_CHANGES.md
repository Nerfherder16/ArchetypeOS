# Recent Changes

## Purpose

This file gives new sessions a quick chronological view of what changed recently.

It is not a replacement for Git history. It is a human-readable coordination log.

## 2026-07-06 — First real Agent Council run (AOS-COUNCIL-PHASEA merged)

### Merged

- PR #54 — AOS-COUNCIL-PHASEA (merge commit `894e418`). The reality test for **Intelligence Phase 1**: the Orchestrator ran the RFC-0005 Agent Council over `pydantic/pydantic-ai` with the **live `claude_code` provider** (real Claude reasoning, 4 agents, 132 s), the way AOS-21 was the reality test for the scanner. **Result: the Council works and is constitution-faithful** — it returned a governed **abstention** (verdict `Insufficient evidence`, confidence 0.0375, below the 0.35 floor), refusing to manufacture an adoption recommendation it could not support and emitting precise follow-ups; `research_librarian` cited the Engineering Constitution + RFC-0004 by name. The run surfaced two honest gaps. **Gap 1 (LES-018, fixed here): fenced-JSON parse defect** — `claude -p --output-format json` wrapped 3 of 4 agents' JSON in a ` ```json ` Markdown fence, and `_parse_agent_output` called `json.loads` directly, degrading them to the prose fallback (conf 0.05, empty findings/concerns); the deterministic provider never emits a fence, so only a real run could surface it. Fixed via `_loads_tolerant` (parse → strip fence → brace-slice) + 4 parser tests; verified against the **captured raw run output** (architecture_cartographer `0→6` findings, technology_fitness_judge `conf 0.05→0.35`), aggregate still abstains. **Gap 2 (LES-019, open): evidence-class mismatch** — a structural scan of the *target* repo is the wrong evidence class for an *adoption* question; the Council rightly abstained and asked for a research/decision corpus. This is the design input for the Phase C decision loop, not fixed here. Shipped the captured review (`.archetype/council/pydantic-ai-review.json`), the evaluation (`docs/COUNCIL_REALRUN_PYDANTIC_AI.md`), and both lessons (vault 17→19; LES-018 closed, LES-019 open — both digest/dashboard-visible). Verified at Level 3: CI run 28764871261 6/6 green on head `225f8b4` + Orchestrator's independent live run; api **106** (+4 parser tests), worker 7, ruff full CI scope + compileall clean. Spec: `.archetype/work/AOS-COUNCIL-PHASEA.md`. Next: operator picks the next build (recommended **Phase C**, the decision loop that LES-019 motivates).

## 2026-07-06 — Portfolio reality test: 5 repos (AOS-21 Done)

### Merged

- PR #53 — AOS-PORTFOLIO-001 Portfolio reality test (merge commit `b64db41`; **Plane AOS-21 Done**). Grew to **five** repos across every axis — pydantic-ai (Python monorepo), claude-agent-sdk-python (lean Python SDK), gin (Go), example-voting-app (polyglot docker-compose), kubernetes (scale: 30,560 files). **Verdict: the scanner is robust and generalizes across language / deployment style / scale** — Go + multi-service compose handled well; at 30k files it degrades gracefully (~2s, truncation **surfaced** via `SCAN_TRUNCATED` + notes, DNA sane). Four honest gaps recorded as open lessons feeding the digest + Knowledge dashboard: LES-013 (language weighting, repo-dependent), LES-014 (dependency/compose architecture edges), LES-016 (manifest/ecosystem coverage — .NET `.csproj` missed), LES-017 (secret-signal precision — 71 warnings on kubernetes). Shipped a repeatable `clone_repo`/`onboard_repo.sh` acquire step (dogfooded on all 5 real clones). Verified at Level 4 (CI 6/6 green on `73f73ac` + Orchestrator's 5-repo pipeline runs, api 102, Playwright 5/5). **Empirically settled depth-vs-breadth toward depth.** Note: the GitHub MCP OAuth token expired mid-session (git/CI unaffected; PR comments blocked until re-auth).

### (package detail)

- AOS-PORTFOLIO-001 — Portfolio: onboard + scan **four** real repos across shapes (`pydantic/pydantic-ai` Python monorepo, `anthropics/claude-agent-sdk-python` lean Python SDK, `gin-gonic/gin` Go, `dockersamples/example-voting-app` polyglot docker-compose — operator-chosen), evaluate every engine (Plane AOS-21; **merging closes it**). The first portfolio reality test. The diverse batch + a **scale test** (kubernetes, 30,560 files) showed the scanner is **robust and broader than assumed** (Go `go.mod` + multi-service compose both handled well; at scale it degrades gracefully — 30k files in ~2s, truncation **surfaced** via a `SCAN_TRUNCATED` signal + notes rather than silent, DNA sane), and flushed out **four honest gaps** recorded as open lessons: LES-013 (file-count language mix, repo-dependent — 28% Python on pydantic-ai vs 77% on the SDK); LES-014 (tree-only architecture edges — universal; the voting-app compose file has the service graph it ignores); **LES-016 (new — `.csproj`/.NET manifest missed; ecosystem coverage stops at python/node/go)**; LES-017 (`SECRET_LIKE_FILENAME` flags legitimate test-cert fixtures — acute at scale: 71 warnings on kubernetes). `clone_repo` dogfooded on all five real network clones (incl. a 30k-file repo). **The scanner generalizes** — it ingested a real multi-package monorepo cleanly (all 8 sub-package manifests, npm+python ecosystems, 23 CI workflows, correct no-Docker; DNA + 15 architecture nodes / 14 `contains` edges persisted; digest ran over the external project) with no crash/truncation. **Two honest gaps recorded as open lessons: LES-013** (file-count `language_mix` reads pydantic-ai as only 28% Python — misleads a fitness/DNA read) and **LES-014** (architecture edges are directory-tree-only; dependency/manifest-derived edges are the missing signal — the Fable-flagged follow-up). Ships a repeatable repo-acquisition capability (`aos_core/services/onboarding.py` `clone_repo` — the missing clone step — + `scripts/onboard_repo.sh` + `test_onboarding.py`), the captured scan (`.archetype/portfolio/pydantic-ai/scan.json`), and the evaluation (`docs/PORTFOLIO_PYDANTIC_AI.md`). The two gaps are scoped follow-ups, not fixed here (per the Plane issue). Adding LES-013/014 as open (vault 12→15 lessons, 1→3 open) required making two count-coupled tests count-agnostic (the KNOW-002 digest test, the KNOW-003 e2e open-filter); a self-caught e2e count-race in that fix is recorded as LES-015 (closed). Orchestrator-verified: api 102 / full Playwright 5/5 headless / `clone_repo` real clone + path-safety / ruff full CI scope. Spec: `.archetype/work/AOS-PORTFOLIO-001.md`.

## 2026-07-06 — Knowledge dashboard (closes AOS-23)

### Merged

- PR #52 — AOS-KNOW-003 Knowledge dashboard (merge commit `c022c6b`; **Plane AOS-23 Done**). Verified at Level 4 (CI run 28761004456 all 6 jobs green on head `6a8942e` — compose-smoke booted api with the vault mount, web-e2e ran the knowledge spec; plus Orchestrator's independent full Playwright suite 5/5 headless, strict tsc/vite build, compose config valid). **AOS-23 complete: the knowledge read path (backend sync + API + digest visibility + dashboard) is done end to end, closing the AOS-KNOW-001 + RFC-0004 deferrals.** Guardian `high-risk-files` WARN (compose mount) acknowledged in the PR body. Next: AOS-21 (second repo).

### (package detail)

- AOS-KNOW-003 — Knowledge dashboard (Plane AOS-23 dashboard phase; **merging closes AOS-23**). Operator sequence "2 then 1": finish the knowledge dashboard, then AOS-21. A **global** "Knowledge" Control Tower section (renders with no project selected — lessons have no project): "Sync from vault" button (shows `synced N · N open`), lesson list with amber open-lesson badges, All/Open filter, per-section error isolation; `api.ts` gains `KnowledgePage`/`KnowledgeSyncResult` + `fetchKnowledgePages`/`syncKnowledge`. Compose: the api service gains a `${HOST_KNOWLEDGE_ROOT:-./knowledge}:/knowledge:ro` mount + `KNOWLEDGE_ROOT` so `POST /knowledge/sync` works in the shipped stack. e2e `knowledge.spec.ts` (sync → LES-007 open badge → Open filter → reload persistence); `serve-api.sh` exports `KNOWLEDGE_ROOT` (the load-bearing detail). Frontend + compose only — no backend/API/schema change. Orchestrator-verified: full Playwright suite 5/5 headless incl. the new knowledge spec; strict tsc/vite build exit 0; `docker compose config` valid with the mount in the api service. Spec: `.archetype/work/AOS-KNOW-003.md`.

## 2026-07-06 — Knowledge read path (substrate sequence)

### Merged

- PR #51 — AOS-KNOW-002 Knowledge read path (merge commit `a462b3a`; Plane AOS-23 backend phase — AOS-23 stays In Progress until the dashboard AOS-KNOW-003). Verified at Level 4 (CI run 28760266463 all 6 jobs green on head `88037c3`; plus Orchestrator's independent run at CI's exact ruff scope — api 99 / worker 7, sync on the real vault = all lessons/LES-007 sole open, digest surfaces it, no-drift after `0004`). Knowledge is operational: lessons queryable + digest-visible (RFC-0004 deferral closed); repo stays source of truth. **First CI run failed on a ruff F401 in migration `0004` — local ruff had scoped to `apps/api/app` (narrower than CI's `apps/api`); fixed, recorded LES-012, made knowledge tests count-agnostic.** LES-012 added to the lessons index (vault now 12 lessons).

### (package detail)

- AOS-KNOW-002 — Knowledge read path (Plane AOS-23 backend; RFC-0002/RFC-0004). Operator-directed sequence "aos-23, then aos-21, then reevaluate the roadmap." Closes two deferrals: the KnowledgePage API read path (AOS-KNOW-001) and digest visibility of open lessons (RFC-0004). **Design: the repo vault stays source of truth; `KnowledgePage` is a re-syncable derived read projection** (a DB reset loses nothing — re-sync from the repo; honors RFC-0004's "lessons travel with the repo"). Adds `knowledge_root` config; makes `KnowledgePage.project_id` nullable (migration `0004`, sqlite batch alter — lessons are global); `aos_core/services/knowledge.py` (`parse_lessons_index` + idempotent `sync_knowledge` upsert keyed by vault_path); a global read API (`POST /knowledge/sync`, `GET /knowledge/pages` [+ page_type/validation_state filters], `GET /knowledge/pages/{id}`); and **digest rule 5** surfacing open lessons (LES-007 today) as a change + draft recommendation. Orchestrator-verified: api 99 / worker 7; sync on the real vault → all lessons (LES-007 the sole open), idempotent, missing-vault→zeros; digest surfaces it; alembic no-drift after `0004` (24 tables, 0 ops, project_id nullable). First CI run flagged an F401 (unused `sqlalchemy` import) in migration `0004` — the Orchestrator's local ruff had scoped to `apps/api/app` while CI scopes to `apps/api` (incl. `alembic/`); fixed the import, recorded **LES-012** (lint-scope parity), and made the knowledge tests count-agnostic (derive from the live index, since lessons are append-only). Backend only — dashboard is AOS-KNOW-003. No Docker/compose change (compose self-contained sync = follow-up). Spec: `.archetype/work/AOS-KNOW-002.md`.

## 2026-07-05 — Control-plane hardening (Lead-Architect critique)

### Merged

- PR #50 — AOS-APIROUTES-001 Split API routes by domain (merge commit `2c5cdcb`; Plane AOS-24 Done). Verified at Level 4 (CI run 28759105408, all 6 jobs green; plus Orchestrator's route-table diff `origin/main` vs working tree → byte-identical 43 pairs, api 94 [92 unchanged + 2 guards], FakeRedis 11 in isolation, `main.py` 487→49). Pure behavior-preserving refactor — API modularized into 10 `routes/*.py`. Env-pinned branch constraint documented (Decision 2a).

### (package detail)

- AOS-APIROUTES-001 — Split API routes by domain (Plane AOS-24). Lead-Architect critique flagged `apps/api/app/main.py` growth (487 lines / 39 routes / ~13 domains, just grew with the council routes); operator directed "route split first, then AOS-COUNCIL-002." Pure behavior-preserving refactor: `main.py` split into 10 per-domain `APIRouter` modules under `apps/api/app/routes/` (`projects`/`repositories`/`scans`/`architecture`/`jobs`/`schedules`/`artifacts`/`decisions`/`digests`/`council`); `main.py` → 49 lines (app + CORS + startup + `/health` + ordered `include_router` loop, retains `import redis` so the FakeRedis `main.redis` patch target survives). New `test_route_inventory.py` freezes the (method, path) set. No endpoint/schema/behavior change. Orchestrator-verified: route table byte-identical `origin/main` vs working tree (43 pairs, empty diff); api 94 (92 unchanged + 2 guards); FakeRedis 11 in isolation. Also this change: the env-pinned branch-name constraint documented in HANDOFF + the Orchestrator Playbook (operator Decision 2a). Spec: `.archetype/work/AOS-APIROUTES-001.md`.

## 2026-07-05 — Intelligence thrust begins (RFC-0005)

### Merged

- PR #49 — AOS-COUNCIL-001 Agent Council seed (merge commit `a56d317`; RFC-0005 Phase 1; Plane AOS-19 Done). Verified at Level 4 (CI run 28757387442, all 6 jobs green incl. compose-smoke applying migration `0003` on Postgres; plus Orchestrator's 3.12-venv run — api 92 / worker 7, `run_council` branch checks, alembic no-drift 24 tables/0 ops). **The Intelligence Layer + Agent Council + Final Judge is live (backend); ArchetypeOS starts to reason.** Advisory/draft-only. Next: AOS-COUNCIL-002 (Agent Council Dashboard).

### (package detail)

- AOS-COUNCIL-001 — Agent Council seed (RFC-0005 Phase 1; Plane AOS-19). Operator-directed ("write RFC-0005 and start AOS-19"). Adds an LLM **provider abstraction** (`packages/aos_core/aos_core/llm/`: `Provider` protocol, `DeterministicProvider` CI default, `ClaudeCodeProvider` — headless `claude` via the operator's subscription, never called in CI, mocked-boundary test), a **council service** (`services/council.py`: four Phase-9 agents — Research Librarian / Architecture Cartographer / Technology Fitness Judge / Security Agent — each reading the project's scan/DNA/decisions, + a rule-based **Final Judge** emitting agreements/disagreements/unsupported-claims/verdict with an abstention floor → `Insufficient evidence`), dedicated `CouncilReview`/`CouncilAgentOutput` tables + Alembic migration `0003`, a worker `council_review` dispatch, and council trigger/read API (`POST/GET /projects/{id}/council-reviews`, `GET /council-reviews/{id}`). Operator decisions: Claude Code SDK via subscription (no metered API/budget gate), four agents, dedicated tables. Backend only — the Agent Council Dashboard is AOS-COUNCIL-002. Orchestrator-verified (3.12 venv): ruff/compile clean, api 92 / worker 7, `run_council` branch checks (4 outputs, disagreement, abstention, 404, determinism), alembic no-drift after `0003` (24 tables, 0 ops). RFC: `docs/rfc/RFC-0005-Intelligence-Layer-Agent-Council-Final-Judge.md`; provider doc: `docs/LLM_PROVIDER_ABSTRACTION.md`.

## 2026-07-05 — Sprint 5 close (worker pipeline complete)

### Merged

- PR #48: AOS-SCHED-002 — Scheduler dashboard: schedules UI + enqueue + job history (merge commit `350c8b0`; RFC-0007 / RFC-0006 Phase 3b). Adds `GET /projects/{id}/jobs` (recent jobs, cap 50, 404 on missing project) and a dashboard "Scheduling & Jobs" section: create/list schedules, per-row enable-disable + run-now + delete, enqueue scan/digest as jobs on demand, and a job-history read + refresh. New e2e `scheduling.spec.ts` (create → run-now → job-in-history → disable → reload); `serve-api.sh` starts an ephemeral redis so the enqueue path actually pushes; web-e2e CI job hardened with an "Ensure Redis available" step (LES-011 family). **Closes AOS-18 (Plane Done) and the worker pipeline — RFC-0006 (shared core) + RFC-0007 (control-plane scheduling) realized end to end: schedules → scheduler → queued jobs → workers → dashboard.** Verified at Level 4 (CI run 28756145778, all 6 jobs green, incl. compose-smoke booting api+worker+web+scheduler; plus Orchestrator's 3.12-venv run — Playwright 4/4 headless, 77 api, 6 worker, strict tsc/vite). **Sprint 5 packages 1–6 (PRs #43–#48) all delivered; the distributed-runtime substrate is complete.**

## 2026-07-05 (earlier)

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

### Sprint 5 Merged (continued)

- PR #44: AOS-ALEMBIC-001 — adopt Alembic migrations, baseline (merge commit `96550b8`): model-driven baseline for the 20-table schema (no schema change; no-drift probe = 0 ops), container entrypoint runs `alembic upgrade head` before uvicorn and hard-fails on error, migration discipline documented. Verified at Level 4 — CI run 28750732119 all 6 jobs green incl. compose-smoke running the migration against fresh Postgres.

### RFC-0006 Accepted — Shared Core Domain Library

Operator-approved 2026-07-05: extract an installable `aos_core` package both apps import (worker runs scans in-process). Reshapes AOS-18 into 3 phases: AOS-CORE-001 (extract), AOS-WORKERRUN-001 (worker runs jobs), AOS-SCHED-001 (schedule). `docs/rfc/RFC-0006-Shared-Core-Domain-Library.md`.

### Sprint 5 Merged (continued 2)

- PR #45: AOS-CORE-001 — extract aos_core shared package, RFC-0006 Phase 1 (merge commit `5d00a18`): `packages/aos_core/` (config/database/models/scanner moved verbatim + new scan/digest services); api reduced to routes + schemas; repo-root api Docker context; alembic + guardian scanner fallback retargeted; guardian BLOCKs `packages/aos_core/` changes without tests (LES-010). Zero behavior change. Verified at Level 4 — CI run 28753264841 all 6 jobs green + Orchestrator 3.12-venv run (69 tests, 67 unchanged; no-drift 0 ops; guardian works without aos_core installed).

### Sprint 5 Merged (continued 3)

- PR #46: AOS-WORKERRUN-001 — worker runs scan/digest jobs, RFC-0006 Phase 2 (merge commit `3fe8afb`): the worker imports `aos_core` and runs `repository_scan` → `run_scan` / `project_digest` → `build_digest` off the Redis queue with attempt-based retries; `config.py` deleted; worker Docker repo-root context. Verified at Level 4 — CI run 28753706406 all 6 jobs green + Orchestrator 3.12-venv run (5 worker tests incl. the e2e scan-job persistence proof).

### RFC-0007 Accepted — Scheduling & Control-Plane Job Origination

Operator-directed after weighing the mature-state architecture (roadmap Phase 5: "the control plane decides and stores; nodes execute"). Scheduling is a control-plane concern backed by schedules-as-data, decoupled from executors — not an in-worker loop (which would duplicate every recurring task once a second node exists). `docs/rfc/RFC-0007-Scheduling-Control-Plane-Job-Origination.md`. Cheap now because AOS-17 (Alembic) + AOS-CORE-001 (aos_core) landed.

### Sprint 5 Merged (continued 4)

- PR #47: AOS-SCHED-001 — scheduler seed, RFC-0007 (merge commit `915aa34`): `Schedule` model + **Alembic migration `0002` (first real migration, no-drift 0 ops)**; `aos_core.services.jobs.enqueue_job` (one origination path, shared `QUEUE`); `run_due_schedules` tick; a single-instance control-plane `apps/scheduler` service; Schedule CRUD API. Verified at Level 4 — CI all green incl. compose-smoke applying `0002` on Postgres + booting the scheduler. Added the scheduler to compose-smoke build/up (LES-011).

### Current Work

AOS-SCHED-002 (RFC-0007 / Phase 3b, **closes AOS-18**) in review on this branch — the dashboard "Scheduling & Jobs" section: create/list/enable-disable/run-now schedules, "enqueue scan/digest as job" buttons, and a job-history list; plus a new `GET /projects/{id}/jobs` endpoint. Orchestrator verified on the 3.12 venv + headless Playwright: **4/4 e2e specs pass** (incl. the new `scheduling.spec.ts`: create schedule → run now → job in history), 77 api tests, strict web build clean. Hardened the web-e2e CI job to ensure `redis-server` (the e2e enqueue path needs it; LES-011 family). Merging closes AOS-18 and the worker pipeline — schedules → scheduler → jobs → workers → dashboard, end to end.

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