# AOS-RUNTIME-003 — Repository Scan Persistence and History

## Status

In Review

## Verified Baseline

Confirmed by inspection:

- `POST /repositories/{id}/scan` (`apps/api/app/main.py`) creates a new `Artifact` row per scan (artifact_type `repository_scan`, checksum, size) but always writes the report to the SAME file path (`{artifact_root}/{project_id}/{repository_id}/repository-scan.json`) — each rescan overwrites the file, so older `Artifact` rows reference content that no longer exists and their checksums no longer match disk. Scan history rows accumulate but are unreadable and unlistable.
- No endpoint lists a repository's scan artifacts and no endpoint returns a stored scan report; the DNA endpoint (AOS-CTRL-001) returns only the latest snapshot.
- Rescan node duplication was already fixed by the AOS-ARCH-001 upsert (PR #25) — that draft criterion from Plane AOS-4 is satisfied and out of scope here.
- `Artifact` model already carries everything a scan-run record needs: `repository_id`, `artifact_type`, `path`, `checksum`, `size_bytes`, `created_at`. No new table required.

## In-Scope Files

- `apps/api/app/main.py` (versioned artifact filename; two new read routes)
- `apps/api/app/schemas.py` (scan report content response if needed)
- `apps/api/tests/test_scan_history.py` (new)
- state docs + this spec

## Out-of-Scope

- new database tables or model changes
- artifact retention/pruning policy (future package)
- worker-job execution of scans
- dashboard history view (follow-up UI slice)
- scanner report schema changes

## Acceptance Criteria

- Each scan writes a distinct artifact file (no overwrites); older artifacts remain readable with checksums matching disk — evidence: `test_two_scans_produce_two_versioned_artifacts` (distinct paths, both files exist, sha256 of each matches its row).
- Scan history is listable per repository, newest first — evidence: `test_scan_history_listing`.
- A stored scan report is retrievable by artifact id and parses as the scan report (contains `summary` and `risk_signals`) — evidence: `test_scan_report_content_retrievable`.
- Unknown repository/artifact and cross-repository artifact access return 404 — evidence: `test_scan_history_404s`.
- Existing behavior unchanged: scan response shape, DNA upsert, architecture upsert — evidence: existing 28 tests stay green.

## Verification Plan

Level 2: ruff/compileall/pytest (28 existing + new). Level 3: GitHub CI on the PR; merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): implementation + tests. Orchestrator (Fable): spec, review, verification, PR, merge gate.

## Board Linkage

- Plane: AOS-4 (In Progress)
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
