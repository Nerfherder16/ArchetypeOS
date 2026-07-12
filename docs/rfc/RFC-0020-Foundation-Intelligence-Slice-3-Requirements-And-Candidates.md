# RFC-0020 — Foundation Intelligence Slice 3: Foundation Requirements & Candidates

## Status

Proposed (2026-07-12). Fourth child RFC under **RFC-0016**; first consumer of the System Genome
(RFC-0019, #215/#217) and the Evidence Spine (RFC-0018). Delivers the design's **Slice 3**
(`docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md` §8–§10, §18): compile the Genome + active claims into
a normalized **Foundation Requirement Set**, then generate **Foundation Candidates** (coherent
cross-domain decision sets) with **Foundation Elements** and **score vectors**, gated by
**hard-constraint eligibility before weighted scoring** (AD-8). This is where the Genome starts
driving *decisions*. Per the design's "deterministic + human first" stance (as with the Genome),
**no LLM candidate generation in this slice** — compilation, generation, eligibility, and scoring are
deterministic; agent generation and adversarial council review are Slice 4.

## Summary

Adds the **foundation domain** to the ORM + migration **0030** (head `0029`): `foundation_selection_runs`
(the §13 state-machine container), `foundation_requirements`, `foundation_candidates`,
`foundation_elements`, `foundation_scores`. It turns the RFC-0017 `foundation` contracts
(`FoundationRequirement`, `FoundationCandidate`, `FoundationElement`, `CandidateScore`,
`SelectionRunState`) — already merged in Slice 0 — into persisted, guarded records, exactly as Slice 1
did for the evidence contracts.

`services/foundation.py` provides the deterministic engine:
- **`compile_requirements`** — from an approved/reviewed **target** (or `intended`) `GenomeSnapshot` +
  active claims, deterministic rules emit `FoundationRequirement`s: `constraint`-type claims →
  `hard_constraint` (`veto_if_unsatisfied=true`); `foundation_shaping` traits → `required_capability`/
  `quality_attribute`; `preference` claims → `preference`. Each requirement links its source
  `claim_ids` and a `verification_method` (design §8).
- **`generate_candidates`** — deterministic, template-driven: from the requirements + Genome
  archetypes it produces 2–3 genuinely distinct candidates (a *recommended* and a
  *conservative/reduced-complexity* one, optionally an *alternative*), each addressing the applicable
  foundation domains with `FoundationElement`s derived from requirements. Plus `create_candidate`
  (manual authoring). No LLM.
- **`evaluate_eligibility`** (AD-8) — **before** any weighted score, deterministically check each
  candidate's elements against the `hard_constraint` requirements; a violation populates
  `hard_constraint_violations` and marks the candidate `rejected`/ineligible. A candidate that
  violates a hard legal/safety/security/deployment constraint is ineligible **regardless of score**.
- **`score_candidate`** — deterministic **score vector** (design §10.3): one `CandidateScore` row per
  criterion (`raw_score`, `weight`, `confidence`, `uncertainty_penalty`, `adjusted_score`,
  `supporting_claim_ids`). `score_summary` on the candidate stores the **vector**, never a single
  number; `uncertainty_penalty` reflects evidence thinness (coverage-honest, LES-023).

The `foundation_selection_runs` lifecycle advances through the Slice-0 `SelectionRunState` transitions
(`lifecycle.py`): `draft → requirements_compiled → candidates_generated → eligibility_review`. This
slice **stops at `eligibility_review`**; council review, validation tasks, final human selection
(Slice 4), and the immutable baseline (Slice 5) are out of scope.

Two packages: **AOS-FOUNDATION-MODELS-001** (5 tables + migration + the deterministic engine + tests —
bundled with this RFC) and **AOS-FOUNDATION-API-001** (routes).

## The C2 reuse-vs-new decisions (RFC-0016 — required)

RFC-0016 C2 requires every new foundation table to name the existing model it was measured against and
why reuse failed. Resolutions:

- **`FoundationSelectionRun` → new table.** No existing entity models a multi-stage selection with the
  §13 state machine; the `Job` lifecycle is execution-plumbing, not a foundation-selection run. New.
- **`FoundationRequirement` → new table.** No existing normalized requirement entity (Recommendation is
  a single suggestion; Risk is a hazard). New; links source `claim_ids`.
- **`FoundationCandidate` → new table, but LINKS to `Recommendation`.** A candidate is a coherent
  *cross-domain decision set*, not a single suggestion, so it is not a `Recommendation`. Per the
  RFC-0017 contract it carries an optional `recommendation_ref` — a generated candidate may cite the
  `Recommendation`(s) that seeded an element, so the two are linked, not duplicated.
- **`CandidateScore` → new `foundation_scores` table (NOT `Evaluation` reuse).** Measured against
  `Evaluation(evaluation_type="foundation_score")` and it does not fit: `Evaluation` has **no
  candidate FK** and a **single-score** shape, whereas a score vector is **per-criterion, per-candidate**
  with `weight`/`uncertainty_penalty`/`adjusted_score`/`supporting_claim_ids`. Forcing it into
  `Evaluation.findings` JSON would make the vector unqueryable and un-joinable to a candidate —
  defeating design §10.3 ("show the score vector, not one number"). New table; the RFC-0017
  `CandidateScore.evaluation_ref` remains available if a criterion is *backed by* a real `Evaluation`
  row (reuse-link preserved).
- **`FoundationElement` → new table.** A per-domain decision with rationale/tradeoffs/alternatives;
  no existing equivalent. New; links `claim_ids` + `requirement_ids`.

## Problem

The Genome answers "what kind of system is this?" but nothing compiles it into the **normalized
requirements** and **candidate options** a human chooses between. There is no `foundation_*` table in
code. Slices 4–5 (council/validation, baseline) have no candidates to review or approve. Design §20
steps 9–11 (compile hard constraints; produce ≥2 distinct candidates; deterministically reject a
candidate violating a legal constraint) need this slice.

## Goals

- The 5 foundation tables as normalized, queryable records (design §15), typed to the RFC-0017 enums,
  each `AuditMixin`-based.
- **Deterministic requirement compilation** from the Genome + claims, every requirement tracing its
  source `claim_ids` + a `verification_method` (design §8 gate: hard constraints have clear source
  claims and verification methods).
- **Deterministic candidate generation** producing ≥2 genuinely distinct, internally-coherent
  candidates that each explicitly address the hard constraints (design §9 gate); plus manual authoring.
- **Hard-constraint eligibility evaluated before weighted scoring** (AD-8) — an ineligible candidate is
  rejected regardless of score.
- **Score vectors, not scalars** (design §10.3), coverage-honest (`uncertainty_penalty`, LES-023).
- The selection-run lifecycle driven by the Slice-0 `lifecycle.py` transition table (single source of
  edge legality), advancing to `eligibility_review`.
- Hermetic: the whole engine runs offline over stored genome/claims; sqlite `create_all` green; single
  Alembic head; **`alembic upgrade head` verified locally** before push (LES-042).

## Non-goals

- **No LLM / agent candidate generation** (deterministic + human first, per the design; agent
  generation is Slice 4).
- **No council review, objection tracking, or validation tasks** (Slice 4).
- **No final human selection / Final Judge dossier** (Slice 4) — this slice stops at `eligibility_review`.
- **No Foundation Baseline** (Slice 5).
- **No UI** (later package).
- **No new authority model** — run/candidate approval reuses the `ApprovalRecord` pattern.

## Design

### Tables (ORM in `models.py`; enums from `aos_core.foundation`)

- **FoundationSelectionRun** — `project_id` FK, `target_genome_snapshot_id` FK, `corpus_snapshot_id`
  FK (nullable), `state` (`SelectionRunState`), `summary`. Status/version via AuditMixin. One active
  (non-terminal) run per project enforced in the service.
- **FoundationRequirement** — `selection_run_id` FK, `genome_snapshot_id` FK, `requirement_type`,
  `domain` (`FoundationDomain`), `statement`, `priority`, `weight` (Float), `veto_if_unsatisfied`
  (bool), `verification_method`, `claim_ids` (JSON list). Index `(selection_run_id, requirement_type)`.
- **FoundationCandidate** — `selection_run_id` FK, `name`, `summary`, `status` (`CandidateStatus`),
  `architecture_style` (JSON list), `recommendation_ref` (nullable, C2 link), `assumption_claim_ids`
  (JSON), `satisfied_requirement_ids`/`unsatisfied_requirement_ids` (JSON), `hard_constraint_violations`
  (JSON), `reversibility`, `lock_in_profile` (JSON), `estimated_cost`/`estimated_effort` (JSON),
  `score_summary` (JSON — the **vector**), `confidence` (Float).
- **FoundationElement** — `candidate_id` FK, `domain` (`FoundationDomain`), `title`, `decision`,
  `rationale`, `technology_refs` (JSON), `claim_ids`/`requirement_ids` (JSON), `alternatives_rejected`
  (JSON), `tradeoffs` (JSON), `risks` (JSON), `verification_method`.
- **FoundationScore** — `candidate_id` FK, `criterion` (`EvaluationCriterion`), `raw_score` (Float),
  `weight` (Float), `confidence` (Float), `uncertainty_penalty` (Float), `adjusted_score` (Float),
  `rationale`, `supporting_claim_ids` (JSON), `evaluation_ref` (nullable, C2 reuse-link). Unique
  `(candidate_id, criterion)`.

### `services/foundation.py` + `services/foundation_rules.py`

`foundation_rules.py` holds the deterministic **requirement-compilation rules** and the
**candidate-generation templates** (the foundation analog of `genome_rules.py`): pure functions over
`(GenomeSnapshot traits, claims)` → requirements, and over `(requirements, archetypes)` → candidate
skeletons. `services/foundation.py` orchestrates:

- `open_selection_run(db, *, project_id, target_genome_snapshot_id)` → run in `draft`.
- `compile_requirements(db, *, selection_run_id)` → persists `FoundationRequirement`s; advances the run
  to `requirements_compiled`. Gate: every `hard_constraint` has ≥1 source `claim_id` + a
  `verification_method` (else the requirement is flagged, not silently emitted).
- `generate_candidates(db, *, selection_run_id)` → 2–3 deterministic candidates + elements; advances to
  `candidates_generated`. `create_candidate`/`add_element` for manual authoring.
- `evaluate_eligibility(db, *, selection_run_id)` (AD-8) → for each candidate, deterministically test
  its elements against every `hard_constraint` requirement; populate `hard_constraint_violations` and
  set `status="rejected"` on any violator **before** scoring; advances to `eligibility_review`.
- `score_candidate(db, *, candidate_id)` → per-criterion `FoundationScore` vector; `adjusted_score =
  raw_score*weight − uncertainty_penalty`; `score_summary` = the vector + shape metadata (never a lone
  scalar). Only **eligible** candidates are scored (AD-8).
- Lifecycle transitions validated via `foundation.lifecycle.can_transition(LifecycleKind.selection_run, …)`
  — the Slice-0 table is the single edge-legality source; illegal transitions raise (→ 409 at the API).

### Migration 0030

Additive `create_table` for the 5 tables, `down_revision="0029"`, single head, `import aos_core.models`.
**Do not redeclare `AuditMixin` columns** (LES-042) — no explicit `id/status/version/...` in the model
bodies or the migration's create_table (use the `_audit_columns()` helper exactly once per table).
Validated by no-drift + compose-smoke, and by a local `alembic upgrade head` before push.

### Tests (hermetic, `apps/api/tests/test_foundation_*.py`)

Requirement compilation over a genome + claims fixture (a `constraint` claim → a `hard_constraint`
requirement with source claim + verification method); candidate generation yields ≥2 distinct coherent
candidates each addressing the hard constraints; **eligibility rejects a candidate whose element
violates a hard constraint, before scoring** (design §20 step 11); score vectors are per-criterion with
`adjusted_score` and an uncertainty penalty (and a sparse-evidence candidate carries a larger penalty —
LES-023); only eligible candidates are scored; the selection-run advances draft →
requirements_compiled → candidates_generated → eligibility_review and rejects illegal transitions; the
C2 links (`recommendation_ref`, `evaluation_ref`) round-trip.

## Alternatives considered

- **Reuse `Evaluation` for `CandidateScore`.** Rejected (C2 analysis above) — no candidate FK, wrong
  cardinality/shape for a per-criterion vector.
- **One `foundation_candidate` JSON blob.** Rejected — design §15 forbids; requirements/elements/scores
  must stay queryable and joinable.
- **LLM candidate generation now.** Deferred to Slice 4 — deterministic templates first (design), and
  they attach behind the same `services/foundation.py` seam later, as the Genome did.
- **Score candidates before eligibility.** Rejected — violates AD-8; a hard-constraint violator must be
  ineligible regardless of score. Eligibility runs first.
- **Fold selection/council/validation into this slice.** Rejected — Slice 4 scope; this slice stops at
  `eligibility_review` to stay reviewable.

## Evidence

- RFC-0016 (AD-8, C2, slice map → RFC-0020); RFC-0017 (`FoundationRequirement/Candidate/Element/
  CandidateScore` contracts + `SelectionRunState`/`FoundationDomain`/`EvaluationCriterion` enums +
  `lifecycle.py` transitions — all merged, #210); RFC-0019 (the `GenomeSnapshot`/`GenomeTrait` this
  compiles from); RFC-0018 (the `claims` requirements trace to).
- `services/genome.py` / `genome_rules.py` — the deterministic-rules + review/approve pattern this
  mirrors; `services/decisions.py` + `ApprovalRecord` — run/candidate approval pattern.
- Current Alembic head `0029_system_genome`; 0030 chains from it.
- LES-042 — the mixin-column + run-migration-locally discipline this slice's migration follows.

## Security impact

None new — deterministic, offline, over already-stored genome/claims; no routes in this package (routes
are AOS-FOUNDATION-API-001, reusing the approval pattern). Requirements/candidates inherit claim
sensitivity transitively; enforcement remains RFC-0024. No secrets/egress.

## Compliance impact

Positive: requirements and candidate elements each trace to claims + a verification method, extending
the traceability chain (source → claim → trait → **requirement → candidate decision**). Hard-constraint-
before-score (AD-8) is the governance guarantee that an ineligible option can't be score-laundered.
`docs/capability-map/layer-04.md` (Decision and Recommendation) gains RFC-0020.

## Migration plan

One additive migration `0030_foundation`, `down_revision="0029"`, single head, `import aos_core.models`,
no-drift + compose-smoke, **plus a local `alembic upgrade head` before push** (LES-042: `create_all` ≠
migration). No data migration; requirements/candidates are generated on demand.

## Risks

- **AD-8 bypass** (scoring an ineligible candidate). Mitigated: `score_candidate` refuses non-eligible
  candidates; a test asserts a hard-constraint violator is rejected and unscored.
- **Overconfidence (LES-023).** `uncertainty_penalty` + a sparse-vs-dense test.
- **C2 drift.** The reuse-links (`recommendation_ref`/`evaluation_ref`) are in the schema + tested.
- **Migration duplicate-column regression (LES-042).** Mitigated: no redeclared mixin columns, and
  `alembic upgrade head` run locally before push; Opus verifies the migration line-by-line.
- **Rule breadth.** Seed compilation/generation rules cover the foundation-shaping domains first;
  breadth grows incrementally, unevidenced areas stay explicit (no invented requirements).

## Acceptance criteria (this RFC + AOS-FOUNDATION-MODELS-001)

- Operator approves the 5 tables, the C2 decisions, the deterministic engine, AD-8 eligibility-before-
  scoring, and score vectors.
- AOS-FOUNDATION-MODELS-001 lands: 5 tables + migration 0030 (single head, mixin-safe, locally
  `alembic upgrade head`-verified) + `services/foundation.py` + `foundation_rules.py` + hermetic
  `test_foundation_*` proving compilation (with source claims + verification), ≥2 distinct candidates,
  hard-constraint eligibility-before-scoring (§20 step 11), score vectors + uncertainty penalty
  (LES-023), the lifecycle advance to `eligibility_review`, and the C2 links. Builder ≠ verifier; full
  suite + ruff + compose-smoke green.
- Capability map updated (LES-040); PR ships the RFC Implementation-Status + bullet Acceptance Evidence
  (LES-041).
- No LLM, no council/validation/selection/baseline, no routes (API is the next package).

## Open questions

1. **Which Genome state_view compiles into requirements?** Leaning the **`target`** genome when one
   exists, else `intended` (what stakeholders sought). `current` describes what *is*, not what to build.
   Confirm at build (target authoring is Slice 3+/manual for now).
2. **Candidate archetype templates.** Seed 2–3 (recommended / conservative / alternative) from Genome
   archetypes + requirement weights; keep small and readable. Expand later.
3. **`EvaluationCriterion` subset scored deterministically.** Not all 20 §10.2 criteria have a
   deterministic signal yet; score the ones derivable from requirement-satisfaction/coverage now, mark
   the rest `unknown`-confidence (never invented). Resolve the seed subset at build.

## Dependencies

- **Blocks on:** RFC-0016/0017 (merged), RFC-0018 Slice 1 (merged), RFC-0019 Slice 2 (merged #215/#217).
- **Reuses:** `models.py` mixins; `genome_snapshots`/`genome_traits`/`claims`; `foundation` contracts +
  `lifecycle.py`; the `ApprovalRecord` pattern.
- **Enables:** Slice 4 (council review + validation + selection consume these candidates/scores) and the
  design §20 MVP steps 9–14.

## Implementation Status

- **AOS-FOUNDATION-MODELS-001** (this PR) — the 5 foundation ORM models + migration `0030` (single
  head, `0029→0030`, mixin-safe: `_audit_columns()` helper once per table, verified in isolation via a
  `stamp 0029` + `upgrade`), `services/foundation_rules.py` (deterministic compilation rules +
  candidate templates + AD-8 violation detection + scoring helpers), and `services/foundation.py`:
  `open_selection_run`, `compile_requirements` (constraint claim → `hard_constraint` with source claim
  + verification method; foundation-shaping trait → `required_capability`/`quality_attribute`;
  `preference` claim → `preference`), `generate_candidates` (a *recommended* + a *conservative*
  template, each addressing hard-constraint domains), `evaluate_eligibility` (**AD-8** — hard-constraint
  check flips violators to `rejected` **before** scoring), `score_candidate` (per-criterion
  `FoundationScore` vector; refuses any non-`eligible` candidate with 409; `uncertainty_penalty` grows
  with evidence thinness, LES-023). Run lifecycle advances via `foundation.lifecycle` to
  `eligibility_review`. Scored `EvaluationCriterion` subset = requirement_coverage / evidence_strength /
  residual_uncertainty (the deterministically-derivable ones; the other 17 are not invented).
- **AOS-FOUNDATION-API-001** (queued) — routes: open-run / compile-requirements / generate-candidates /
  evaluate-eligibility / score / list / get.

## Final Judge verdict

Pending operator approval. Slice 3 turns the Genome into the requirement set and candidate options a
human will choose between — deterministic and human-reviewed (no LLM yet), hard-constraints-before-
scores (AD-8), score vectors not scalars, and coverage-honest. Recommend acceptance; start
AOS-FOUNDATION-MODELS-001 (bundled here), API to follow.
