# AOS-SELFHEAL-002 — CI-on-main doc-staleness self-heal (surface + draft)

- Status: In Review
- Owner: laptop session (parallel Orchestrator)
- Branch: `laptop/aos-selfheal-ci` (fresh, from `origin/main` @ `a80e737`)
- Follows: AOS-SELFHEAL-001 (the `--fix` draft generator + post-merge hook + `/reconcile-state` skill). This adds the deterministic **CI-on-main** trigger — the follow-up deferred in that spec.

## Verified Baseline

- `tools/doc_staleness.py --fix` (AOS-SELFHEAL-001) generates `.archetype/reconciliation/PENDING.md` deterministically from `git log` (never edits prose; Article XII). Stdlib-only, so CI needs only python — no deps.
- The PR Guardian already surfaces doc-staleness as a non-blocking WARN, but **only when someone opens a PR** — drift that accumulates with no open PR is invisible (the exact case seen all session: CURRENT_STATE lagged 5 PRs).
- The digest/nightly loop (`build_digest`) runs **in-container** with only `knowledge/`+`repositories/` mounted — no `git`/`docs/`, so `doc_staleness.evaluate()` cannot run there. CI (full checkout + git) is the right host for this trigger.
- `.github/workflows/ci.yml` triggers on push→main already; a **separate** workflow keeps this isolated from the main CI (no risk to the 9 gating jobs).

## Design

New workflow `.github/workflows/doc-staleness-reconcile.yml` (isolated from `ci.yml`), on `push: main` + `workflow_dispatch`:
1. Checkout `fetch-depth: 0` (so `git log` sees merged PRs) + python 3.12.
2. Run `tools/doc_staleness.py --fix`; drift = the `PENDING.md` draft exists.
3. On drift: idempotently **open or update** a single `doc-staleness`-labelled tracking issue whose body is the reconciliation draft (never edits the state docs). One issue, updated in place — no spam.
4. On fresh (no HARD drift): **auto-close** the open `doc-staleness` issue — self-healing: once the docs are reconciled, the next merge closes the issue.
5. `permissions: { contents: read, issues: write }`; `GITHUB_TOKEN`; block-scalar `run:` steps only (LES-027).

The LLM narrative reconciliation half stays with the `/reconcile-state` skill — intended to run from a **nightly Claude routine** (operator already runs nightlies), which applies the draft and opens the PR; the next merge then auto-closes the issue. CI detects+drafts; the routine corrects.

## In-Scope Files
- `.github/workflows/doc-staleness-reconcile.yml` (new)
- `.archetype/work/AOS-SELFHEAL-002.md`
- `docs/CAPABILITY_MAP.md` (Layer 8 note) · `docs/ACTIVE_WORK.md` + `docs/RECENT_CHANGES.md` (own entries — union-safe)

## Out-of-Scope
- Auto-editing the narrative state docs (drafts only; the routine/human applies).
- Auto-opening a reconciliation *PR* from CI (an issue is lower-risk — no bot-commit/branch machinery; the nightly routine opens the PR).
- The digest/nightly in-container wiring (blocked by the container filesystem; separate follow-up needing a runner→DB path).
- Any change to `ci.yml` or the 9 gating jobs.

## Acceptance Criteria
1. The new workflow YAML parses (`yaml.safe_load`) and defines exactly one job `reconcile`; `ci.yml` is untouched (still 9 jobs). — evidence: lint output.
2. No inline `run:` scalar carries a colon-space (LES-027). — evidence: grep.
3. The detect step correctly sets drift from the presence of `PENDING.md`; dry-run on this tree (real #79-vs-#81 drift) produces the expected draft body. — evidence: local dry-run.
4. Guardian PASS (a non-blocking high-risk-files WARN for the workflow is expected + acknowledged in the PR body). — evidence: guardian output.

## Verification Plan
- Level 2 (local): YAML lint the new workflow + confirm `ci.yml` unchanged; grep the LES-027 trap; dry-run the detect + issue-body logic against this tree.
- Level 3: on merge, the workflow runs on `main` and (given current drift) opens the tracking issue — dogfoods immediately. Watch the first run.

## Board Linkage
- Plane: AOS-SELFHEAL-002 (create Done on merge). Advances Article XX.
