# Orchestrator Playbook

## Purpose

The complete, battle-tested operating loop for the ArchetypeOS Orchestrator role, as practiced across Sprints 1–4 (PRs #1–#41). Written at the Fable 5 → Opus 4.8 orchestrator handoff (2026-07-05) so the loop survives model switches, context compaction, and container loss. Where this document and CLAUDE.md disagree, CLAUDE.md wins; where it and the state files disagree about status, the state files win.

## Boot order for a fresh orchestrator session

1. `CLAUDE.md` (operating rules — including the RFC-0004 lesson-recording rule)
2. `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/RECENT_CHANGES.md`
3. This playbook
4. `knowledge/wiki/lessons/index.md` (the open-lesson queue is the improvement backlog)
5. The active package spec in `.archetype/work/`, if any

## Role contract

- The Orchestrator owns: specs, delegation, **independent verification**, PRs, merge gates, board sync, state reconciliation, lesson recording.
- Builders (Opus subagents for code, Sonnet for large docs) own implementation inside **exact file boundaries** given in the delegation prompt. Builders never commit, never push, never self-certify — their raw command output is input to the Orchestrator's own re-run, not a substitute for it.
- The human operator owns: merges (Manual Merge Gate — this plan has no enforceable required status checks), destructive actions, scope changes, and RFC approval.
- Development happens ONLY on branch `claude/aos-runtime-002-scanner-1egyjw`. Never push elsewhere.
  - **Branch-name constraint (known, not sloppy):** this name is **pinned by the session/environment config** (the "Git Development Branch Requirements" contract), not chosen per-package — which is why it still says `runtime-002-scanner` even though it has since carried PROC/KNOW/…/SCHED/CORE/COUNCIL/APIROUTES work. Two things keep this honest despite the stale name: (1) **each package restarts the branch from `main`** (`git checkout -B … origin/main`), so one PR = exactly one package and the git *history* is disciplined; (2) the *name* is a config artifact, not a claim about the work. A per-package scheme (e.g. `opus/aos-<pkg>`) is preferable and will be adopted **only** when the operator reconfigures the environment's branch mapping or grants explicit permission — the Orchestrator cannot change it unilaterally (pushing elsewhere is forbidden). Flagged by the Lead-Architect critique 2026-07-05; operator chose "document the constraint" (Decision 2a) for now.

## The package loop (repeat per work package)

1. **Spec** — write `.archetype/work/<ID>.md` per RFC-0003: Verified Baseline (claims confirmed by inspection with file:line pointers), In-Scope Files (exact), Out-of-Scope, Design, Acceptance Criteria as assertions each with an evidence pointer, Verification Plan, Board Linkage.
2. **Board** — Plane item → In Progress (IDs in `docs/PLANE_PROJECT_BLUEPRINT.md` Board ID Registry). Markdown state files win on conflict; Plane outages → keep a "Pending Plane updates" list and retry via a `send_later` trigger.
3. **Delegate** — one Agent call with: the spec path, strict file boundaries ("touch ONLY these files"), style-matching instructions, the verification commands it must run, the rules (no git, no new deps, never edit the guardian or tests to make something pass), and "RETURN raw data, not prose".
4. **Independently verify** — re-run the full suite yourself (`python3 -m ruff check apps/api apps/worker tools`; `python3 -m compileall -q apps tools`; `PYTHONPATH=apps/api python3 -m pytest apps/api/tests -q`), read the actual diff, and probe live behavior (see Level 4 recipes). Review remediations you make are learning events — record a lesson (LES-004 is the precedent).
5. **State updates in-PR** — ACTIVE_WORK, CURRENT_STATE, HANDOFF, RECENT_CHANGES updated in the same PR (fold the previous PR's post-merge reconciliation in too). New docs REQUIRE a `docs/CAPABILITY_MAP.md` touch (guardian-enforced).
6. **Lessons** — every guardian BLOCK, CI failure, or review remediation gets a `knowledge/wiki/lessons/` page + index row in the same change set (guardian-enforced for guardian changes; convention otherwise).
7. **Guardian** — `python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file <body>` from the **repo root**. PR body metadata must be plain `Field: value` lines (no bold/bullets). Statuses: exactly `Verified` / `Verified with warnings` / `Verification pending` / `Verification unavailable` / `Verification blocked`; levels exactly `Level 0`..`Level 5`. Never bypass a BLOCK; overrides need a `LES-<n>` citation in the body.
8. **PR** — title `<ID>: <what> (<context>)`; body carries Summary, Changes, Verification Metadata (plain lines), **Acceptance Evidence** (`## Acceptance Evidence` heading + `— evidence:` bullets; required for code-path PRs), Board Linkage.
9. **Babysit** — see the babysitter recipe below.
10. **Gate** — when CI is green on the head SHA, post the Manual Merge Gate comment (template below). A new push voids the gate; re-verify and re-post.
11. **Merge (human)** → delete the babysitter trigger, Plane item → Done, `git fetch origin main && git checkout -B claude/aos-runtime-002-scanner-1egyjw origin/main`, next package (fold reconciliation into it).

## Babysitter recipe (per PR)

1. `subscribe_pr_activity` for the PR (webhooks deliver comments/CI failures/merge — but NOT CI success or new pushes).
2. Background `sleep 180` — when it fires, check `pull_request_read get_check_runs`; if all green, post the gate comment.
3. `send_later` ~60 min with a message that carries: the PR number + head SHA, what to do if OPEN (verify CI, ensure gate posted, re-arm silently), and **the full continuation instructions if MERGED** (trigger delete, Plane issue UUID + Done state UUID, branch restart, next package definition). This is what makes the loop survive unattended merges.
4. On merge webhook: delete the trigger FIRST (stale babysitters have fired after merge before — they're no-ops if instructions are idempotent, but delete anyway).

## Manual Merge Gate comment template

Pinned to head SHA. Sections: `## Manual Merge Gate — VERIFIED ✅`; **Pinned to head SHA** + void-on-push sentence; Verification Metadata (Status/Level/Method); Evidence — CI run link + 5-job table (PR Guardian, API tests and lint, Worker tests and lint, Web typecheck and build, Docker Compose smoke test) + Orchestrator-independent evidence; scope/loop-closure notes; `**Gate decision: READY FOR MERGE**`.

## Level 4 verification recipes

- **API live probe**: uvicorn from `apps/api` with `DATABASE_URL=sqlite:///<scratch>.db`, `ARTIFACT_ROOT=<scratch>`, `REPOSITORY_ROOT` as needed, `REDIS_URL=redis://localhost:9999/0` (dead port) or a real `redis-server --port 6390 --daemonize yes` when the path needs Redis. `/health` returns `degraded` without Redis by design (PR #39).
- **Dashboard drives**: `scripts/web_drive/README.md` — the committed harness with per-package drive scripts.
- **Self-scan**: `REPOSITORY_ROOT=/home/user` + register `local_path=ArchetypeOS` scans this repo through the public API (the Alpha Review pattern; captures in `.archetype/alpha/`).

## Environment quirks registry (hard-won — trust these)

- **Stop-hook false positive**: merge commits on `main` authored by `noreply@github.com` are flagged "Unverified". They are GitHub's merge commits. NEVER rewrite main history; note it and move on.
- **Compound bash + `kill`**: `kill`/`pkill` in a `set -e` compound command aborts the remaining script (exit 144). Run teardown in its own Bash call.
- **Playwright**: `chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })` in managed containers; never `playwright install`.
- **Plane MCP**: `create_issue`/`create_cycle` need `project_id` nested inside `issue_data`/`cycle_data` (as well as the top-level param); `create_cycle` 400s on `start_date` without `end_date` — omit both for a dateless cycle; `create_label` needs a `label_data` object. Outage → markdown wins + pending-updates list + retry trigger.
- **Guardian invocation**: run from the repo root (`cd /home/user/ArchetypeOS`) — relative paths break from subdirs. `git fetch origin main` first for freshness.
- **Hermetic tests**: `apps/api/tests/conftest.py` pins env vars BEFORE app imports; Redis pinned to dead port 9999 (LES-004 — degraded-state assertions must hold on machines with a real local Redis, e.g. `teevee-1` which co-hosts Plane, Postgres on 5433).
- **CI truth**: GitHub Actions RUNS on this private free-plan repo; what's missing is enforceable required checks — hence the gate. Typical CI wall time ~90s; the compose smoke is always last.
- **PR body override mentions**: the literal string `PR_GUARDIAN_OVERRIDE_` anywhere in a PR body triggers the lesson-citation rule — if you mention tokens in prose, cite a `LES-<n>` too.

## Current facts at handoff (2026-07-05, post-PR #41)

- v0.1 COMPLETE (Alpha Review `docs/ALPHA_REVIEW_V0_1.md`); Sprint 4 (Self-Healing & Learning Loop) complete: PRs #39/#40/#41.
- Test suite: 65 (API incl. guardian tests) + 1 worker. Toolchain pins: Python 3.12 target, ruff==0.8.6 via `python3 -m ruff`.
- Open lesson queue: LES-007 (doc staleness). Accepted warning `web-tests-not-enforced` expires **2026-08-01** — ship web tests or renew consciously before then.
- Next-sprint candidates, evidence-ranked: web tests (deadline above), LES-007 doc-staleness detection, architecture-graph semantics (manifest/compose-derived edges), digest breadth, KnowledgePage API read path.

## Update rule

Amend this playbook whenever the loop itself changes (new gate steps, new guardian behaviors, new environment quirks) — in the same PR as the change.
