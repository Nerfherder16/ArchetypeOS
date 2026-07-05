# AOS-PRG-002 — PR Guardian Reads Repository Scanner Output

## Status

In Progress

## Verified Baseline

Confirmed by inspection:

- `tools/pr_guardian.py` is deterministic and consumes only the git diff and PR body. It detects secrets by regex over ADDED DIFF LINES only — a committed `.env` or secret-like FILE (e.g. `key.pem`, `id_rsa`) added to the repo is caught only if its content matches the content patterns; the filename itself is never checked. It has no awareness of the repository's test posture or language ecosystems.
- `apps/api/app/repository_scanner.py` is stdlib-only (`os`, `collections`, `pathlib`) — importable from the guardian's CI job, which installs no dependencies. `scan_repository()` is read-only and deterministic and emits structured `risk_signals` (ENV_FILE_PRESENT, SECRET_LIKE_FILENAME, MISSING_TESTS, MULTIPLE_ECOSYSTEMS, …).
- The guardian CI job checks out the merge ref with full history and runs Python 3.12 with no pip installs.
- Scan reports are also persisted per-repository via the runtime (AOS-RUNTIME-003), but CI has no runtime — so the guardian must be able to produce its own scan.

## In-Scope Files

- `tools/pr_guardian.py` (scanner integration + new checks)
- `apps/api/tests/test_guardian_scanner.py` (new; lives in the api test tree because that is the only pytest target CI runs — explicit `sys.path` bootstrap to import the tool, with a load-bearing comment)
- `docs/PR_GUARDIAN.md` (document the new checks)
- state docs + this spec

## Out-of-Scope

- LLM-based review; network calls of any kind
- guardian writing to the repository or runtime
- blocking on info-severity scanner signals
- changes to `repository_scanner.py` or the report schema
- CI workflow changes

## Design

- New optional CLI arg `--scan-report <path>` (JSON file). When absent, the guardian attempts an in-repo scan: insert `apps/api` into `sys.path`, import `app.repository_scanner.scan_repository`, scan the working tree. If the import or scan fails for any reason, all scanner-informed checks are skipped and the guardian behaves exactly as today (graceful degradation, one info line in the report).
- New deterministic checks fed by the scan report:
  1. `scanner-secret-path` (BLOCK): a changed file path appears in a `SECRET_LIKE_FILENAME` risk signal — catches committed key files by NAME, which the diff-content regexes miss.
  2. `scanner-env-committed` (BLOCK): a changed file path appears in an `ENV_FILE_PRESENT` risk signal — a real `.env` is being committed.
  3. `scanner-missing-tests` (WARN): scan reports `MISSING_TESTS` and the PR adds code-suffix files — corroborates the repo-wide test gap at review time.
  4. `scanner-new-ecosystem` (WARN): the PR adds a manifest file and the scan reports `MULTIPLE_ECOSYSTEMS` — surfaces ecosystem expansion for explicit acknowledgment.
- Overrides follow the existing convention: `PR_GUARDIAN_OVERRIDE_SCANNER` skips all four checks (rationale required in body).
- Report prints one line noting whether scanner-informed checks ran and how many signals were consulted.

## Acceptance Criteria

- Guardian consumes a scan report from `--scan-report` and from the in-repo fallback — evidence: `test_scan_report_file_input`, `test_in_repo_scan_fallback`.
- At least two checks are informed by scan data — evidence: `test_secret_path_blocks`, `test_env_committed_blocks`, `test_missing_tests_warns`, `test_new_ecosystem_warns` (four).
- Deterministic and read-only; no behavior change when the scanner is unavailable — evidence: `test_graceful_degradation_without_scanner` (simulated import failure → findings identical to baseline).
- Existing guardian checks unchanged — evidence: full API suite green; guardian self-run on this PR.
- Guardian remains dependency-free in CI — evidence: scanner module is stdlib-only; no new imports beyond it.

## Verification Plan

Level 2: ruff/compileall/pytest (32 existing + new guardian tests); guardian self-run on this diff (which itself exercises the in-repo scan path live). Level 3: GitHub CI; merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): implementation + tests. Orchestrator (Fable): spec, review, verification, PR, merge gate.

## Board Linkage

- Plane: AOS-6 (In Progress), Sprint 3 cycle `9d9c2fd6-3305-419a-a5e8-0c6d4d3c058b`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
