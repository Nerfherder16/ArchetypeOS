# Alpha Review v0.1 — ArchetypeOS Evaluates ArchetypeOS

## Purpose

Phase 10 of `docs/CONCRETE_BUILD_PATH.md`: before expanding, run ArchetypeOS on its own repository and answer five questions. This document is the review artifact. Every claim below is backed by a captured output in `.archetype/alpha/` produced by live API calls on 2026-07-05 (work package `AOS-ALPHA-001`), or by a cited PR/CI event from Sprints 1–3.

## How the run was executed

The full v0.1 loop was driven through the public API against this working tree (`REPOSITORY_ROOT=/home/user`, `local_path=ArchetypeOS`, sqlite, real Redis for the job leg):

1. Project + repository registered via `POST /projects` and `POST /projects/{id}/repositories`.
2. Two self-scans via `POST /repositories/{id}/scan` (two versioned artifacts stored).
3. DNA and architecture graph read back via `GET .../dna` and `GET .../architecture`.
4. One research note and two decisions recorded from real findings via `POST .../research-notes` and `POST .../decisions`.
5. Nightly digest run twice via `POST .../digests`.
6. A job executed end-to-end: `POST /jobs` → Redis queue → worker → `completed`.
7. PR Guardian run on this package's own diff (output in `.archetype/alpha/self-guardian.txt`).

## The Five Phase 10 Questions

### 1. Did it understand itself? — PARTIAL (structure yes, semantics no)

The scanner's self-report is accurate on every checkable fact (`.archetype/alpha/self-scan.json`, `self-dna.json`): 184 files; language mix Markdown 122 / Python 23 / TypeScript 4 / Shell 2 with primary-language hints Python + TypeScript; ecosystems npm + pip detected from 4 manifests; all 3 Dockerfiles + compose found; GitHub Actions CI found; `has_tests: true`; `has_env_example: true`; MULTIPLE_ECOSYSTEMS correctly flagged at info severity.

The architecture graph (`self-architecture.json`) is 12 nodes / 11 edges — the repository root plus its top-level directories with `contains` edges at confidence 0.65/0.75. That locates the system but expresses no service, dependency, or data-flow semantics (nothing says "api talks to postgres"). Recorded as a decision (below).

### 2. Did it find stale docs? — NO by machine, YES by process

v0.1 has no doc-staleness detection: the scanner records that docs exist, not whether they are current. Stale entries were found this sprint — `docs/ACTIVE_WORK.md` carried an outdated AOS-LOCAL-001 status until PR #36, and `docs/CURRENT_STATE.md` still described the Plane board at its Sprint 2 snapshot until this PR — but they were found by Orchestrator review during state reconciliation, not by the system. This is the clearest capability gap the alpha surfaced; it is recorded in the research note and in Next Development Guidance.

### 3. Did it generate useful decisions? — YES

Two decisions were created from defects actually observed during this run (`.archetype/alpha/self-decisions.json`):

- **"Fix /health Redis degradation as first post-v0.1 runtime task"** — during the run, `GET /health` returned HTTP 500 (Redis `ConnectionError` propagating out of `health()` in `apps/api/app/main.py`) when Redis was absent, and `{"status":"ok","api":true,"database":true,"redis":true}` (`self-health.json`) when Redis was up. A health endpoint that crashes exactly when the environment is degraded is a real defect. Decision carries a typed `research_note` evidence entry linking to the findings note.
- **"Deepen architecture graph beyond directory containment in v0.2"** — deliberately recorded *without* linked research to exercise the learning loop (see question 5).

Both are actionable, evidence-backed, and scoped — the intended shape of a decision card.

### 4. Did PR Guardian find real risks? — YES

Live self-run: the guardian ran on this package's own diff with its scanner-informed checks active (in-repo scan fallback — the scanner examining the repository that contains the guardian); verbatim output in `.archetype/alpha/self-guardian.txt`. Its first pass on this very PR returned two BLOCKs — the new review doc lacked a `docs/CAPABILITY_MAP.md` update, and the draft PR body's verification-metadata lines were formatted so they didn't parse — both real process violations, both fixed rather than overridden. The committed capture is the passing re-run (PASS_WITH_WARNINGS, expected verification-pending only).

Historical evidence from this sprint, on real PRs:

- It BLOCKed secret-looking strings in test fixtures twice (during AOS-PRG-002 and AOS-LEARN-001 preparation); both were fake markers, both were renamed rather than overridden — the check did exactly its job.
- It BLOCKed an invalid verification-level literal (`Level 4 (local)`), enforcing metadata discipline.
- Its CI job has gated every PR since #2; PR #33's guardian job executed the new scanner-informed code live on the PR that introduced it.

The risks found were real (credential-pattern leakage into diffs, metadata drift), not noise: no BLOCK this sprint was a false alarm requiring an override.

### 5. Did nightly learning produce useful recommendations? — YES

Digest run against the self-evaluation state (`.archetype/alpha/self-digest.json`):

- `summary`: "1 repositories, 2 scan runs, 2 decisions, 1 research notes, 0 recommendations; 1 draft suggestions".
- It caught the genuinely unlinked decision: draft suggestion "Link research to decision: Deepen architecture graph beyond directory containment in v0.2" with reason "decision has no linked research".
- Repeated-task detection fired: `{"task": "repository_scan", "repository_id": ..., "count": 2}` after the second scan.
- Every recommendation carries `"status": "draft"` (asserted programmatically during capture) — the drafts-only rule held.

The one suggestion produced is correct and actionable. Coverage is narrow (four rules), which is expected at v0.1 and noted below.

## v0.1 Acceptance Criteria Conformance

| Criterion (from `docs/V0_1_SCOPE_LOCK.md`) | Status | Evidence |
| --- | --- | --- |
| Local Docker runtime starts reliably | Met | teevee-1 run 2026-07-05: 6/6 services healthy (`.archetype/work/AOS-LOCAL-001.md`) |
| Dashboard shell loads | Met | headless-Chromium drives in PRs #27, #34, #36 (7–10 checks each) |
| API health endpoint responds | Met with defect | `self-health.json` all-true with Redis; HTTP 500 without Redis (decision recorded) |
| Worker can run a job | Met | `self-job.json`: queued → completed in 36 ms via Redis queue, live in this run |
| Repository can be registered | Met | this run; `self-scan.json` header |
| Scanner produces read-only report | Met | two versioned artifacts; read-only mount probe rejected on teevee-1 |
| Architecture graph draft generated as data | Met (shallow) | `self-architecture.json`, 12 nodes / 11 edges with confidence + correction fields |
| Decision/research artifacts created and viewed | Met | `self-decisions.json`; dashboard section (PR #34) |
| PR Guardian produces first-pass review report | Met | `self-guardian.txt`; CI guardian job on every PR |
| Nightly digest runs manually | Met | `self-digest.json`; dashboard Run Digest (PR #36) |
| Knowledge vault populated with initial artifacts | Met | PR #23 (AOS-KNOW-001), full RFC-0002 structure |

Phase 10 acceptance — "ArchetypeOS can evaluate ArchetypeOS": demonstrated above. "Output is useful enough to guide next development": the guidance below is drawn entirely from this run's findings.

## Next Development Guidance (evidence-backed)

1. **`/health` graceful degradation** — catch the Redis `ConnectionError` and return 200 with `redis: false`. Smallest, highest-signal fix; decision already recorded with research linkage.
2. **Architecture graph semantics** — derive service/dependency edges from manifests and compose (api→postgres, worker→redis, web→api). Decision recorded; v0.2 candidate.
3. **Doc staleness detection** — the one Phase 10 question answered "NO by machine". A deterministic first pass is cheap: compare state-file claims (branch names, PR numbers, "In Progress" items) against git history.
4. **Digest breadth** — feed guardian findings and architecture-graph deltas into the digest so nightly learning sees validation and architecture signals, not only scan/decision counts.
5. **Web test coverage** — the guardian has warned `MISSING_TESTS` for `apps/web` on every UI package; dashboard behavior is currently verified only by Orchestrator browser drives.
6. **KnowledgePage API read path** — explicitly deferred in AOS-KNOW-001; the vault is populated but not queryable through the API.

## Limitations of this review

- The evaluated tree was the working tree at merge commit `8b39e67` plus this package's own files; the scanner therefore saw `.archetype/alpha/` being born (an observer effect, harmless).
- The dashboard leg was not re-driven in this run; it is covered by the PR #36 drive three hours earlier on the same code.
- Deterministic aggregation only — no LLM judgment anywhere in the loop, per scope lock.
