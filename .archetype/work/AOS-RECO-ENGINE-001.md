# AOS-RECO-ENGINE-001 — Recommendation + Technology Fitness generator

## Status

Proposed (2026-07-11). Wave C of RFC-0015. Unblocked (builds on AOS-RESEARCH-COUNCIL-001, merged). No execution, hermetic.

## Origin

Closes AOS-REVIEW-003 seam #4 and gives two of the six name-only engines a real engine: **Technology Fitness** and **Recommendation Intelligence**. Today `Recommendation` is hand-written CRUD (`routes/decisions.py:136-158`) that nothing generates; only the digest reads it. This package turns the `compare → recommend` stage from vestigial into a real generator.

## Verified Baseline

Confirmed on `main` @ `70dfccb`:

- `Recommendation` (`models.py:260-275`): `project_id, title, recommendation, rationale, alternatives, pros, cons, risk, effort, dependencies, acceptance_criteria, evidence, confidence`.
- `RepositoryDNA` (`models.py:89-105`): `purpose, maturity, language_mix, package_managers, frameworks, runtime_services, deployment_files, risk_flags, scan_summary, confidence, evidence`. Read for a project by joining `Repository` on `project_id` (pattern: `council._project_dna`, `council.py:63-72`).
- `ResearchNote` (`models.py:152-168`): `question, summary, sources, findings, confidence`.

## In-Scope Files

- `packages/aos_core/aos_core/services/recommendation.py` (new):
  - `score_fitness(dna) -> list[dict]` — a **deterministic, rule-based** Technology Fitness pass. Emits fitness signals `{subject, signal, score, severity, evidence}` from the DNA: each `risk_flag` → a low-fitness signal (score derived from a small documented severity table); each `framework`/`runtime_service` → a neutral/positive signal. No model call — deterministic over DB rows (Article VIII).
  - `generate_recommendations(db, *, project_id) -> list[Recommendation]` — gathers the project's `RepositoryDNA` (same join as `_project_dna`) + latest `ResearchNote`s, derives draft `Recommendation` rows: each `risk_flag` → a remediation recommendation; each research finding that names an option → an adoption recommendation. Populates `rationale`, `evidence` (typed pointers `{"type":"repository_dna"|"research_note","id":...}`), `risk`, `confidence` (from the fitness score × source confidence). Draft/advisory (`approved_by` null). **Idempotent** via `meta["reco_signature"]` (a stable hash of subject+kind) — re-running does not duplicate.
- `apps/api/app/routes/decisions.py` (or a new `recommendations.py`) — `POST /projects/{project_id}/recommendations/generate` runs `generate_recommendations` and returns the created rows. Update the frozen route inventory.
- `apps/api/tests/test_recommendation_engine.py` (new).

## Out-of-Scope

- No provider/LLM call (keep it deterministic + hermetic). A phrasing pass via the Provider can be a later slice.
- No migration (reuses `recommendations`).
- No web UI.
- No change to the existing hand-CRUD recommendation routes.

## Acceptance Criteria

- `generate_recommendations` on a project with DNA `risk_flags` creates draft `Recommendation`s, each with a typed `evidence` pointer and a `confidence` in [0,1] — evidence: `test_generate_from_dna_risk_flags`.
- Re-running does not duplicate (dedup on `meta["reco_signature"]`) — evidence: `test_generate_idempotent`.
- `score_fitness` returns the documented signal shape for frameworks + risk flags — evidence: `test_score_fitness_signals`.
- A research finding naming an option yields an adoption recommendation citing the note — evidence: `test_generate_from_research_finding`.
- Empty project (no DNA, no notes) → no recommendations, no error — evidence: `test_generate_empty_project`.
- `POST /projects/{id}/recommendations/generate` returns the created rows — evidence: route test. Route inventory updated. Full suite green; ruff clean.

## Verification Plan

Level 2 (hermetic tests). Builder ≠ verifier: Sonnet builds; Opus reviews the fitness rule table (must be honest/defensible, not fabricated scores) and the dedup signature.

## Suggested Delegation

Sonnet subagent; Opus reviews the fitness scoring for engineering-integrity (Article XII — no manufactured confidence).

## Board Linkage

Branch: designated session branch. Deferred with intent if descoped.
