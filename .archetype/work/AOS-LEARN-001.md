# AOS-LEARN-001 — Nightly Learning Digest, Manual Run (Phase 7)

## Status

In Review

## Verified Baseline

Confirmed by inspection:

- `NightlyDigest` model exists (`apps/api/app/models.py`): `project_id`, `digest_date`, `summary`, `changes` (list), `recommendations` (list), `repeated_tasks` (list), plus AuditMixin. No routes, no schemas, no UI.
- Aggregation sources all exist and are queryable: scan artifacts (`Artifact` where `artifact_type == "repository_scan"`, one per scan since PR #29), `RepositoryDNA.risk_flags` (latest scan posture), `Decision` (incl. typed research links in `evidence`), `ResearchNote`, `Recommendation`.
- v0.1 scope-lock criteria not yet met: "Nightly learning digest can run manually", digest saved, recommendations drafts only; Interface list includes a "nightly digest view".
- Dashboard placeholders still list "Nightly digest view".

## In-Scope Files

- `apps/api/app/main.py` (three routes), `apps/api/app/schemas.py` (`NightlyDigestRead`)
- `apps/api/tests/test_digests_api.py` (new)
- `apps/web/src/api.ts`, `apps/web/src/main.tsx` (digest section: Run Digest button + list)
- state docs + this spec

## Out-of-Scope

- scheduling/cron/worker automation (manual run only, per scope lock)
- LLM summarization (deterministic aggregation only in v0.1)
- model/table changes or migrations
- voice inbox (remaining placeholder)

## Design

- `POST /projects/{project_id}/digests` (no body): deterministically aggregates current DB state into a saved `NightlyDigest`:
  - `changes`: recent scan runs (up to 20 scan artifacts: repository id, artifact name, created_at ISO), recent decisions/research notes/recommendations (titles + created_at), each entry a typed dict (`{"type": "...", ...}`).
  - `repeated_tasks` (draft detection): repositories scanned more than once → `{"task": "repository_scan", "repository_id": ..., "count": N}`.
  - `recommendations` (DRAFTS ONLY — every entry carries `"status": "draft"`): deterministic rules —
    1. repository DNA `risk_flags` mention missing tests → "Add tests to <repo>";
    2. registered repository never scanned → "Run a scan for <repo>";
    3. decision has no typed `research_note` evidence entry → "Link research to decision <title>";
    4. project has scans but no decisions → "Record the first decision for this project".
  - `summary`: counts string (repositories, scans, decisions, research notes, recommendations, draft items).
  - `digest_date`: `now_utc()` (timestamps allowed here — tests must not assert exact times).
- `GET /projects/{project_id}/digests` (desc by created_at), `GET /digests/{digest_id}`; 404 conventions as established.
- Dashboard: "Nightly Digest" section for the selected project — Run Digest button, list of digests (digest_date, summary), latest digest's draft recommendations rendered as lines; remove the "Nightly digest view" placeholder (voice inbox remains).

## Acceptance Criteria

- Digest can be run manually and is saved — evidence: `test_digest_run_and_saved` (POST → row exists, GET list/read return it).
- Aggregation reflects real data — evidence: `test_digest_changes_aggregation` (scans + decision + research note appear in `changes`).
- Draft recommendations fire deterministically and are marked draft — evidence: `test_digest_draft_recommendations` (missing-tests rule + never-scanned rule + unlinked-decision rule; every entry has `status == "draft"`).
- Repeated-task detection — evidence: `test_digest_repeated_tasks` (repo scanned twice → count 2 entry).
- Empty project digest works; unknown project 404s — evidence: `test_digest_empty_project`, `test_digest_404s`.
- Dashboard runs and displays digests — evidence: Orchestrator headless-Chromium drive (Run Digest → digest listed with summary; draft recommendations visible; reload persistence).
- Build/type safety — evidence: strict tsc + vite build exit 0; full API suite green.

## Verification Plan

Level 2: ruff/compileall/pytest (46 existing + new). Level 4 (local): headless-Chromium drive. Level 3: GitHub CI; merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): API + web + tests. Orchestrator (Fable): spec, review, browser verification, PR, merge gate.

## Board Linkage

- Plane: AOS-11 (In Progress), Sprint 3 cycle `9d9c2fd6-3305-419a-a5e8-0c6d4d3c058b`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
