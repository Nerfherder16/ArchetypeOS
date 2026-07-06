# AOS-20 — Doc-staleness detection

- Status: In Progress
- Owner: laptop session (parallel Orchestrator)
- Branch: `laptop/aos-20-doc-staleness` (cut from `origin/main` @ `10242e4`)
- Plane: AOS-26 (In Progress → Done on merge)
- Closes: LES-007 (open, `process`) — "Doc staleness is only caught by human review — the one Phase 10 'NO by machine'."

## Verified Baseline (confirmed by inspection, not assumption)

- `.archetype/roadmap.md` still declares `## Current phase` → `Foundation.` on `origin/main` @ `10242e4`, while `docs/CURRENT_STATE.md:12` reads `Phase: v0.1 COMPLETE (2026-07-05); post-v0.1 development underway`. This is the exact real-world drift LES-007 names — a live true-positive for the detector to catch. (Fixing roadmap.md is OUT of this package's scope; it is owned by the pending sync/reconciliation PR.)
- No deterministic drift check exists. `tools/` contains only `pr_guardian.py`; there is no `tools/doc_staleness.py`.
- `tools/pr_guardian.py` is deterministic and stdlib-only: `Finding(severity, code, message)` (`tools/pr_guardian.py:22`); `render()` returns exit `1` iff any finding has `severity == "block"` (`:551`), so a `"warn"` finding is inherently non-blocking (`PASS_WITH_WARNINGS`); `main()` composes checks via `findings.extend(check_*(...))` (`:597`).
- Guardian tests live under `apps/api/tests/` (CI's only pytest target) and import the tool via a path bootstrap: `sys.path.insert(0, parents[3]); from tools.pr_guardian import ...` (`apps/api/tests/test_guardian_scanner.py:11`).
- State-doc formats the detector parses: `docs/CURRENT_STATE.md` "Status"/"Recently Merged" reference PRs as `PR #NN`/`#NN`; `docs/RECENT_CHANGES.md` uses `## DATE — title (AOS-ID merged/in review)` + `PR #NN`; `git log` merge commits read `Merge pull request #NN from ...`.
- Calibration on the current tree: newest merged PR in `git log` = `#66`; newest PR referenced in CURRENT_STATE = `#65` and in RECENT_CHANGES = `#65`. Lag = `1` — the normal one-PR reconciliation window (the prompt confirms a "TRANSFER-002 merged" reconciliation is pending). This MUST classify SOFT, not HARD.

## Design (mature-state target, and this package as a strict subset)

Mature-state target: a deterministic "doc-vs-reality" verifier that cross-checks every doc claim it can mechanically verify against ground truth (git history, state files, scanner/DNA, decision records), reports drift as severity-ranked findings, and is consumable both standalone (CI/manual) and as an advisory PR Guardian WARN. It is the deterministic floor of the same two-tier pattern the rest of the platform uses (a reasoned/LLM tier could later explain or prioritize drift behind a stable `Finding` seam).

This package ships a permanent SUBSET of that target — two robust, defensible signals — as a stable module later work extends, never scaffolding:

- **Module** `tools/doc_staleness.py` (stdlib-only, hermetic). Pure check functions operate on strings so tests inject fixtures; a thin IO layer reads real files + shells `git log` (degrading to empty on any failure — fail-open, never crash).
  - `Finding(signal, severity, message, evidence)` with `severity ∈ {"hard","soft"}`.
  - **Signal 1 — roadmap-phase-vs-reality (can be HARD).** Parse `.archetype/roadmap.md` "Current phase"; if it names an early-phase token (`foundation`, `phase 0`, `documentation foundation`, `scaffold`) while `docs/CURRENT_STATE.md` contains completion markers (`v0.1 complete`, `post-v0.1`, `sprint <n>`), emit HARD. This is the LES-007 defect.
  - **Signal 2 — state-doc PR lag (SOFT within window, HARD if far behind).** newest merged PR from `git log` vs newest PR referenced in CURRENT_STATE ∪ RECENT_CHANGES. lag ≤ 0 → clean; `1..hard_threshold` → SOFT; `> hard_threshold` (default `3`) → HARD. Conservative default keeps the normal reconciliation lag quiet.
  - `run_checks(...)` (pure) → `evaluate(repo_root)` (IO) → `main(argv)`: prints grouped findings; exit `1` iff any HARD, else `0`.
- **Guardian hook** `check_doc_staleness(files)` in `tools/pr_guardian.py` (additive): lazily/defensively imports `doc_staleness.evaluate`, maps **HARD** doc-staleness findings to guardian `Finding("warn", "doc-staleness:<signal>", ...)` and drops SOFT (keeps the guardian quiet). One `findings.extend(check_doc_staleness(files))` line in `main()`. NEVER emits `"block"`; NEVER alters an existing check.
- **Tests** `apps/api/tests/test_doc_staleness.py` (hermetic): a stale fixture trips each signal; a fresh fixture passes; SOFT lag does not exit non-zero; and the guardian hook only ever yields `"warn"` (never `"block"`), asserted with a monkeypatched `evaluate`.

## In-Scope Files (exact)

- `tools/doc_staleness.py` (new)
- `apps/api/tests/test_doc_staleness.py` (new)
- `tools/pr_guardian.py` (additive WARN hook only)
- `.archetype/work/AOS-20.md` (this spec)
- `knowledge/wiki/lessons/LES-024.md` + row in `knowledge/wiki/lessons/index.md` (closing LES-007 / recording the package; LES-022/023 are the remote session's merged IDs)
- `docs/CAPABILITY_MAP.md` (doc-staleness area only)
- `docs/ACTIVE_WORK.md` (my own item only) · `docs/RECENT_CHANGES.md` (prepend my own entry only)

## Out-of-Scope

- Editing `.archetype/roadmap.md` (owned by the pending sync PR) — the detector reports it; it does not fix it.
- `packages/aos_core/**`, `apps/api/app/**` transfer/distillation, `repository_scanner.py` (remote session's RFC-0009 zone).
- The CURRENT_STATE "Current sprint" status line and `docs/HANDOFF.md` (remote Orchestrator reconciles those).
- Making doc-staleness a guardian BLOCK, or a blocking CI step, or weakening any existing guardian rule.
- Additional signals (decision-coverage, doc freshness scoring, per-file owners) — future subsets of the same target.

## Acceptance Criteria (assertions, each with an evidence pointer)

1. `tools/doc_staleness.py` exists, stdlib-only, and `python3 -m compileall tools` is clean. — evidence: compileall output.
2. Signal 1 emits a HARD finding when roadmap phase is early but CURRENT_STATE shows completion, and none when roadmap phase matches reality. — evidence: `test_roadmap_phase_stale_is_hard`, `test_roadmap_phase_fresh_passes`.
3. Signal 2 emits SOFT for a 1-PR lag and HARD only when lag > threshold; clean when docs are current. — evidence: `test_pr_lag_one_is_soft`, `test_pr_lag_far_is_hard`, `test_pr_lag_current_is_clean`.
4. `main()` exits `1` iff a HARD finding is present, `0` for soft-only/clean. — evidence: `test_exit_nonzero_only_on_hard`.
5. The guardian gains exactly one additive check wired once in `main()`; it emits only `"warn"` (never `"block"`), and a HARD doc-staleness result yields `PASS_WITH_WARNINGS` (exit 0), not BLOCK. — evidence: `test_guardian_doc_staleness_warns_never_blocks`; `git diff` shows no existing check altered.
6. Full local gate green: `ruff check apps/api packages/aos_core apps/worker tools`, `compileall -q apps tools`, `PYTHONPATH=apps/api pytest apps/api/tests -q` (+ worker), and `tools/pr_guardian.py` passes on this PR (it may WARN on the live roadmap drift — that is the intended true positive, non-blocking). — evidence: command outputs in the PR body.

## Verification Plan

- Level 1 (inspection): read the diff — confirm additive-only guardian change, no existing check touched.
- Level 2 (local): ruff + compileall + pytest (api + worker); run `python3 tools/doc_staleness.py` against the live tree and confirm it reports the roadmap-phase HARD (true positive) and the 1-PR-lag SOFT.
- Level 2 (guardian): `python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file <body>` from repo root — expect PASS or PASS_WITH_WARNINGS (the doc-staleness WARN is acceptable and expected), never BLOCK from this change.
- Level 3: GitHub CI (5 jobs) green on head SHA → Manual Merge Gate.

## Board Linkage

- Plane AOS-26 "Doc-staleness detection" → In Progress now → Done on merge (state UUIDs in `docs/PLANE_PROJECT_BLUEPRINT.md`).
- Lesson: closes LES-007; records LES-024 (package + the live roadmap drift as a self-found defect).
