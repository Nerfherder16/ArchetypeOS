# AOS-PROC-001 — Build Process Hardening

## Status

In Progress

## Verified Baseline

Confirmed by inspection before implementation:

- `tools/pr_guardian.py` had no acceptance-evidence check; PR bodies were not required to map criteria to evidence beyond the existing Verification Protocol metadata block.
- `docker-compose.yml` already mounted `${HOST_REPOSITORY_ROOT:-./repositories}:/repositories:ro` for both `api` and `worker` services — the read-only guarantee was already runtime-enforced, just undocumented.
- No `apps/api/tests/test_scan_endpoint.py` existed; the scan endpoint had no integration-level test (only unit tests on `scan_repository()` in `test_scanner.py`).
- `apps/api/tests/conftest.py` did not exist as a shared fixture file; each test module built its own `TestClient`.
- Toolchain versions (`ruff`, `pytest`) were pinned inline only in `.github/workflows/ci.yml`, with no repo-root pin file.
- No `.python-version` file existed.

## In-Scope Files

- `tools/pr_guardian.py`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_scan_endpoint.py`
- `apps/api/tests/test_repository_registry.py`
- `requirements-dev.txt`
- `.python-version`
- `docs/rfc/RFC-0003-Work-Package-Specs.md`
- `.archetype/work/TEMPLATE.md`
- `.archetype/work/AOS-PROC-001.md`
- `.archetype/work/AOS-KNOW-001.md`
- `docs/PR_GUARDIAN.md`
- `docs/REPOSITORY_SCANNER.md`
- `docs/PLANE_PROJECT_BLUEPRINT.md`
- `docs/ACTIVE_WORK.md`
- `docs/CURRENT_STATE.md`
- `docs/HANDOFF.md`
- `docs/RECENT_CHANGES.md`

## Out-of-Scope

- `apps/web/`
- scanner report schema changes
- Plane Modules/Cycles creation (blocked on a Project Settings feature toggle a human must flip)
- WSL/Docker local workstation verification

## Acceptance Criteria

- PR Guardian blocks code-path PRs missing an `## Acceptance Evidence` section — evidence: guardian unit/self-check exercising `missing-acceptance-evidence`.
- PR Guardian blocks an `## Acceptance Evidence` section with no `evidence:` bullet — evidence: guardian self-check exercising `empty-acceptance-evidence`.
- Override token `PR_GUARDIAN_OVERRIDE_ACCEPTANCE` suppresses the check — evidence: guardian override-path self-check.
- Scan endpoint produces a report, persists `RepositoryDNA`, and writes a checksummed artifact — evidence: `test_scan_endpoint_produces_report_dna_and_artifact`.
- Scan endpoint does not mutate the scanned repository — evidence: `test_scan_endpoint_is_read_only_against_scanned_repo`.
- Scan endpoint returns 404 for an unknown repository — evidence: `test_scan_endpoint_404_for_unknown_repository`.
- Rescanning a repository updates its `RepositoryDNA` — evidence: `test_scan_endpoint_rescan_updates_dna`.
- Toolchain versions are pinned outside CI so local and CI environments match — evidence: `requirements-dev.txt` (ruff==0.8.6, pytest==8.3.4) and `.python-version` (3.12) present in diff.
- Full API test suite and lint pass locally — evidence: `PYTHONPATH=apps/api pytest apps/api/tests -q` exit 0; `ruff check apps tools` exit 0.

## Verification Plan

Level 2 (local execution) in this session: ruff, `python -m compileall`, and the full `apps/api/tests` suite (20 tests including the 4 new scan-endpoint integration tests), plus guardian self-checks against synthetic PR bodies. Level 3 (GitHub CI) required next, via the opened PR.

## Suggested Delegation

Runtime slice (already completed by the Runtime Agent in this worktree): implement the guardian acceptance-evidence check, the shared `conftest.py` fixture, the four scan-endpoint integration tests, and the toolchain pin files. Docs slice (this agent): RFC-0003, work-package specs, and durable state file updates.

## Board Linkage

- Plane: AOS-2 (Build process hardening, In Progress)
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
