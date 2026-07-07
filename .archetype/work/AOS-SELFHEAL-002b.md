# AOS-SELFHEAL-002b — Reconcile nightly routine (the "correct" half, headless)

- Status: In Review
- Owner: laptop session (parallel Orchestrator)
- Branch: `laptop/aos-selfheal-reconcile-nightly` (fresh, from `origin/main`)
- Follows: AOS-SELFHEAL-002 (#83, CI-on-main detect + draft) and AOS-SELFHEAL-001 (#80, the `--fix` draft generator + `/reconcile-state` skill).

## Why

The self-heal loop could **detect** drift everywhere (Guardian WARN on PRs, the
post-merge hook locally, and now the CI-on-main tracking issue) but the
**correct** half still needed a human to sit down and run `/reconcile-state`.
The operator runs nightly Claude routines; this wires the correction into one so
the docs reconcile themselves overnight and present a PR for the morning review.

## Design

Deterministic gate + reasoned tier, opening a PR for review (never merging) —
the autonomy level the operator chose.

- `scripts/nightly/reconcile_state.prompt.md` — the self-contained headless
  contract (apply narrative → re-run detector to FRESH → guardian → open PR).
  The single source of truth for both runners.
- `scripts/nightly/reconcile_state.sh` — the local-cron path: syncs `main`, runs
  `tools/doc_staleness.py --fix`, and **only on real drift** cuts one fresh daily
  branch and invokes the prompt via headless `claude`. Refuses a dirty tree;
  skips if today's reconcile branch already exists; `DRY_RUN=1` for a detect-only
  rehearsal.
- `docs/runbooks/nightly-routines.md` — how to register it as a `/schedule`
  cloud routine or a local crontab entry.
- `skills/ci_devops/reconcile_state.md` — extended with the Nightly automation
  contract and the full trigger set.

### Conservative scope (cross-session safety)

The routine edits only union-safe / watermark fields: `docs/RECENT_CHANGES.md`
(append), the `docs/CURRENT_STATE.md` PR-watermark, and `.archetype/roadmap.md`
(only on a roadmap-phase HARD). It deliberately does **not** touch the
"Current sprint" narrative line or `docs/HANDOFF.md` — a live Orchestrator owns
those (single-writer discipline; avoids the tandem-conflict class).

## In-Scope Files
- `scripts/nightly/reconcile_state.prompt.md` (new)
- `scripts/nightly/reconcile_state.sh` (new, executable)
- `docs/runbooks/nightly-routines.md` (new)
- `skills/ci_devops/reconcile_state.md` (Nightly automation section)
- `docs/CAPABILITY_MAP.md` (Layer 8 note) · `docs/ACTIVE_WORK.md` +
  `docs/RECENT_CHANGES.md` (own entries — union-safe)

## Out-of-Scope
- Auto-merging any reconciliation PR (human gate stays on).
- Editing the "Current sprint" line / HANDOFF (remote Orchestrator owns them).
- The conflict self-learn nightly (AOS-SELFHEAL-003 — separate package).

## Acceptance Criteria
1. `bash -n` clean; the dirty-tree guard exits 0 without touching branches
   (evidence: run on a dirty tree → SKIP, still on the caller's branch).
2. The deterministic gate keys on `PENDING.md` existence after `--fix`, matching
   the CI workflow; `DRY_RUN=1` performs no branch/claude action.
3. Runtime artifacts (`PENDING.md`, `nightly.log`) stay gitignored — nothing
   machine-generated is committed.
4. Guardian PASS / PASS_WITH_WARNINGS.

## Verification Plan
- Level 2 (local): `bash -n`; exercise the dirty-tree SKIP guard; confirm
  `.archetype/reconciliation/` is gitignored; doc-staleness `--fix` drift/ FRESH
  semantics already covered by `apps/api/tests/test_doc_staleness.py`.
- Level 3: first live nightly run opens a reconcile PR when `main` has drifted —
  watch the first run after registering the routine.

## Board Linkage
- Plane: AOS-SELFHEAL-002b (create Done on merge). Advances Article XX.
