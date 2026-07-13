# RFC-0021 — Foundation Intelligence Slice 4: Council & Validation

## Status

Proposed (2026-07-12). Fifth child RFC under **RFC-0016**; first consumer of the Foundation Candidates
(RFC-0020, #218/#219) and the typed Council payloads (AOS-COUNCIL-TYPED-001, #220). Delivers the
design's **Slice 4** (`docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md` §10–§13, §18): run the
**Engineering Council** over each eligible foundation candidate producing **typed specialist reviews**,
track **objections**, prescribe **validation tasks** when evidence is insufficient, synthesize a
**Final Judge dossier**, and gate a **human candidate selection**. This is where LLM/agent review
re-enters — deterministic in CI (the `DeterministicProvider`), a real model behind the `Provider` seam
on an authed node.

## Summary

Reuses the existing, now-typed Council (`run_council` + `CouncilReview` + `CouncilAgentOutput` +
`synthesize_verdict`) rather than a parallel review engine, and adds the foundation-adjudication layer:
migration **0031** (head `0030`) adds `validation_tasks`, `validation_results`, `foundation_objections`,
`foundation_dossiers`, and two nullable link columns (`candidate_id`, `selection_run_id`) on
`CouncilReview` so a review can attach to a candidate.

`services/foundation_council.py` orchestrates the design's Stages 11–13:
- **`review_candidate`** — assembles a candidate's context (its `FoundationElement`s, the run's
  `FoundationRequirement`s, its score vector, the assumption claims) into the council's evidence and
  calls `run_council`; the resulting `CouncilReview` is tagged with the candidate. Blocking council
  `concerns`/unsupported findings become **`FoundationObjection`** rows; "required validation" signals
  and low-confidence/uncertain criteria become **`ValidationTask`** rows.
- **`resolve_objection`** — an objection is `open` until explicitly `resolved`, `accepted_exception`
  (by an authorized person), or `converted_to_validation` (links a `ValidationTask`). Design §11: an
  objection stays visible until resolved.
- **`record_validation_result`** — a `ValidationResult` (pass/fail/inconclusive) becomes new evidence;
  a failed **blocking** validation can flip a candidate back to ineligible / rescore.
- **`synthesize_dossier`** — across the run's reviewed candidates, produces a **`FoundationDossier`**
  (Final Judge output, design §13): recommended candidate, reasons, remaining uncertainty, rejected
  alternatives, conditions of approval, required future reviews. It **synthesizes, it does not select**
  (design §13: "does not silently become the project authority").
- **`select_candidate`** — the **mandatory human gate** (design §13): requires no unresolved *blocking*
  objection and every *blocking* validation `passed` or `accepted_exception`; sets the candidate
  `selected`, advances the run to `selected`, and writes an `ApprovalRecord`.

The selection-run lifecycle advances (via the Slice-0 `foundation.lifecycle` table) `eligibility_review
→ council_review → validation_required → validation_complete → ready_for_selection → selected`.

Two packages: **AOS-COUNCIL-VALIDATION-MODELS-001** (tables + migration + the adjudication engine +
tests — bundled with this RFC) and **AOS-COUNCIL-VALIDATION-API-001** (routes).

## The C2 reuse-vs-new decisions (RFC-0016)

- **Reuse `CouncilReview` / `CouncilAgentOutput` / `synthesize_verdict`** for the specialist review —
  the design §11 explicitly says "the current generic agent envelope can remain, but each agent needs a
  typed payload" (shipped in #220). We add two nullable link columns to `CouncilReview` (candidate/run)
  rather than a parallel review table; a candidate review *is* a council review with a subject.
- **Reuse `ApprovalRecord`** for the human selection gate (as decisions/plans/genome approvals do).
- **`ValidationTask` / `ValidationResult` → new tables.** No existing entity models a prescribed,
  blocking, pass/fail validation with success/failure criteria; `Benchmark`/`Experiment`/`Evaluation`
  are *result* records — a `ValidationResult` may **project into** a `Benchmark`/`Experiment` row
  (reuse-link where a real benchmark backs it), but the queueable *task* is new (design §11).
- **`FoundationObjection` → new table.** Council `concerns` are transient per-review text; an objection
  is a *tracked* item with a resolution workflow and a blocking flag (design §11 gate) — new, linked to
  its source `CouncilReview` + candidate.
- **`FoundationDossier` → new table.** The Final Judge's per-run adjudication record (design §13) has
  no existing home (`CouncilReview` is per-review; a `Decision` is the *downstream* artifact). New.

## Problem

Slice 3 produces eligible candidates with score vectors, but nothing adversarially reviews them,
tracks the objections, prescribes validation for uncertain assumptions, or gates a human choice. The
design's §20 steps 12–15 (specialist reviews produce structured objections; an uncertain assumption
creates a benchmark validation task; validation evidence changes the comparison; a human selects one
candidate) need this slice. It is the payoff of the whole chain: *candidates a human can choose between,
with the objections and validations that make the choice defensible.*

## Goals

- Typed, evidence-bearing specialist reviews of each eligible candidate, reusing the Council (design
  §11); every review attached to its candidate + run.
- **Objection tracking** with a real resolution workflow — blocking objections must be resolved,
  accepted as explicit exceptions, or converted to validation before selection (design §11 gate).
- **Validation, not invented certainty** (AD-10): insufficient-evidence / high-uncertainty signals
  become blocking `ValidationTask`s; results become new evidence that can change the ranking (§20 step
  14).
- A **Final Judge dossier** that synthesizes the record and recommends — but does not select.
- A **mandatory human selection gate** (design §13, Constitution IX/XIX), enforced: no unresolved
  blocking objection, all blocking validations cleared.
- Deterministic + hermetic in CI (the council runs on the `DeterministicProvider`); a real model
  attaches behind the `Provider` seam on an authed node — exactly as the existing Council already does.
- Single Alembic head; migration mixin-safe and locally `alembic upgrade head`-verified (LES-042).

## Non-goals

- **No new review engine** — reuse the Council; no change to the specialist personas beyond the typed
  payloads already shipped.
- **No autonomous selection** — the dossier recommends; a named human selects (the gate).
- **No baseline** — the immutable Foundation Baseline is Slice 5 (RFC-0022); this slice ends at
  `selected`.
- **No execution/build compilation** (Stage 15) — that derives from the Slice-5 baseline via the
  existing Decision→Plan loop (RFC-0015).
- **No new authority model / no LLM in CI** — reuse `ApprovalRecord` + `DeterministicProvider`.
- **No UI** (later package).

## Design

### Tables (ORM in `models.py`; enums from `aos_core.foundation`)

- **ValidationTask** — `candidate_id` FK, `selection_run_id` FK, `title`, `validation_type`
  (`ValidationType`), `question`, `method`, `success_criteria` (JSON), `failure_criteria` (JSON),
  `required_evidence` (JSON), `blocking` (bool), `status` (`ValidationStatus`), `result_claim_ids`
  (JSON). Index `(selection_run_id, status)`.
- **ValidationResult** — `validation_task_id` FK, `outcome` (`passed|failed|inconclusive`), `summary`,
  `evidence` (JSON), `benchmark_ref`/`experiment_ref` (nullable, C2 reuse-links), `result_claim_ids`
  (JSON).
- **FoundationObjection** — `candidate_id` FK, `review_id` FK (nullable → `CouncilReview`),
  `raised_by` (persona/agent), `objection`, `materiality` (`Materiality`), `blocking` (bool), `status`
  (`open|resolved|accepted_exception|converted_to_validation`), `resolution`,
  `resolution_validation_task_id` (nullable FK), `resolution_decision_id` (nullable FK).
- **FoundationDossier** — `selection_run_id` FK, `recommended_candidate_id` FK (nullable), `verdict`,
  `reasons` (JSON), `remaining_uncertainty` (JSON), `rejected_alternatives` (JSON),
  `conditions_of_approval` (JSON), `required_future_reviews` (JSON), `approved_by`/`approved_at` (set
  by the human selection). One active dossier per run.
- **`CouncilReview`** gains nullable `candidate_id` FK + `selection_run_id` FK (additive columns in
  0031 — LES-042: plain `ADD COLUMN`, no mixin-column redeclaration).

### `services/foundation_council.py` — the adjudication engine

- `review_candidate(db, *, candidate_id, provider) -> CouncilReview` — build the candidate's context
  (elements + run requirements + score vector + assumption claims) as council evidence; `run_council`;
  tag the review with candidate/run; derive `FoundationObjection`s from blocking concerns/unsupported
  findings and `ValidationTask`s from required-validation signals + low-confidence criteria. Advances
  the run to `council_review` (and `validation_required` if any blocking task exists).
- `resolve_objection(db, *, objection_id, status, resolution, ...)` — the resolution workflow;
  `converted_to_validation` creates/links a `ValidationTask`.
- `record_validation_result(db, *, validation_task_id, outcome, ...)` — persists a `ValidationResult`,
  flips the task status, and (on a failed blocking task) can mark its candidate `challenged`/ineligible
  or trigger a rescore; when all blocking tasks are cleared, advances the run to `validation_complete`.
- `synthesize_dossier(db, *, selection_run_id) -> FoundationDossier` — reuse `synthesize_verdict` per
  reviewed candidate; recommend the top **eligible** candidate with **no unresolved blocking objection**
  and **all blocking validations cleared**, by adjusted score; record reasons/uncertainty/rejected/
  conditions. Advances to `ready_for_selection`. **Recommends only.**
- `select_candidate(db, *, selection_run_id, candidate_id, approver) -> FoundationCandidate` — the
  human gate: **409** unless the candidate is eligible, has no unresolved blocking objection, and every
  blocking validation is `passed`/`accepted_exception`; sets candidate `selected`, run `selected`,
  writes an `ApprovalRecord`, stamps the dossier's `approved_by`/`approved_at`.
- All lifecycle transitions validated via `foundation.lifecycle` (illegal → raise → 409 at the API).

### Migration 0031

Additive: `create_table` for the 4 new tables + `add_column` (nullable FK) ×2 on `council_reviews`,
`down_revision="0030"`, single head, `import aos_core.models`, `_audit_columns()` helper once per new
table (LES-042). Validated by no-drift + compose-smoke + a local `alembic upgrade head`.

### Tests (hermetic, `apps/api/tests/test_foundation_council_*.py`)

Set up a project → genome → requirements → candidates (via the Slice-1/2/3 services), then on the
`DeterministicProvider`: `review_candidate` attaches a typed CouncilReview to the candidate and derives
objections + validation tasks; a blocking objection blocks selection until resolved/accepted;
`record_validation_result` on a failed blocking task blocks/rescopes; `synthesize_dossier` recommends
the top clear-eligible candidate and **does not** select; `select_candidate` **409s** with an
unresolved blocking objection or a failing blocking validation, and succeeds (writing an
`ApprovalRecord`, run→`selected`) once cleared (design §20 steps 12–15); lifecycle advances
council_review→validation_required→validation_complete→ready_for_selection→selected and rejects illegal
transitions; the C2 reuse-links (`benchmark_ref`/`experiment_ref`, `resolution_validation_task_id`)
round-trip.

## Alternatives considered

- **A parallel candidate-review engine** instead of reusing the Council. Rejected — the Council is the
  design's Engineering Council (§11), now typed; a candidate review is a council review with a subject.
  Two nullable link columns beat a duplicate review stack.
- **LLM-driven review in CI.** Rejected — hermetic CI runs the `DeterministicProvider`; a real model
  attaches behind the `Provider` seam on an authed node, unchanged from today's Council.
- **Auto-select the top-scored candidate.** Rejected — violates the design §13 human gate and AD-9
  (scores never replace human approval). The dossier recommends; a human selects.
- **Skip validation tasks; treat uncertainty as a low score.** Rejected — AD-10: high uncertainty
  creates validation work, not invented certainty; a passed validation must be able to *change* the
  ranking (§20 step 14).

## Evidence

- RFC-0016 (AD-9/AD-10, C2, slice map → RFC-0021); design §10–§13, §20 steps 12–15.
- `services/council.py` (`run_council`, `synthesize_verdict`, typed payloads from #220),
  `models.CouncilReview`/`CouncilAgentOutput` — reused.
- `services/foundation.py` + `foundation_rules.py` (RFC-0020) — the candidates/scores this reviews;
  the run lifecycle + `foundation.lifecycle` transition table.
- `services/decisions.py` + `ApprovalRecord` — the human-approval pattern the selection gate reuses.
- Current Alembic head `0030_foundation`; 0031 chains from it. LES-042 migration discipline.

## Security impact

No new external surface in CI/default — the council runs on the `DeterministicProvider` (offline);
a real model runs only on the operator's authed node behind the `Provider` seam (subscription auth,
LES-021 context isolation), exactly as today. Selection is a human-gated `ApprovalRecord` write.
Validation tasks/objections inherit claim sensitivity transitively; enforcement remains RFC-0024.

## Compliance impact

Strongly positive — this is the adjudication + human-approval segment of the traceability chain
(candidate → typed review → objection → validation → dossier → human selection), with durable, auditable
objection and validation records and a mandatory human gate (AD-9). `docs/capability-map/layer-04.md`
gains RFC-0021.

## Migration plan

One additive migration `0031_council_validation`, `down_revision="0030"`, single head, mixin-safe
(`_audit_columns()` once per new table; the two `council_reviews` columns are nullable `ADD COLUMN`),
`import aos_core.models`, no-drift + compose-smoke + local `alembic upgrade head` (LES-042). No data
migration.

## Risks

- **Human-gate bypass.** Mitigated: `select_candidate` refuses (409) with any unresolved blocking
  objection or unpassed blocking validation; tested.
- **Migration column-add on `council_reviews` (LES-042).** Plain nullable `ADD COLUMN`, no mixin-column
  redeclaration; `alembic upgrade head` run locally; Opus verifies the migration line-by-line.
- **Objection/validation never converging.** Mitigated: objections have an explicit resolution set and
  `accepted_exception` is always available to an authorized human; the dossier reports unresolved items.
- **Council over a candidate returns weak/abstained reviews.** That is correct behavior (the existing
  abstention floor / `Insufficient evidence` verdict) — it produces validation tasks, not a forced
  decision.

## Acceptance criteria (this RFC + AOS-COUNCIL-VALIDATION-MODELS-001)

- Operator approves the reuse-the-Council approach, the 4 new tables + 2 link columns, the objection/
  validation workflow, and the human selection gate.
- AOS-COUNCIL-VALIDATION-MODELS-001 lands: tables + migration 0031 (single head, mixin-safe, locally
  `alembic upgrade head`-verified) + `services/foundation_council.py` + hermetic `test_foundation_council_*`
  proving typed candidate reviews, objection tracking, validation-task generation + result feedback, the
  dossier (recommend-not-select), and the human selection gate (409 until cleared) — §20 steps 12–15.
  Builder ≠ verifier; full suite + ruff + compose-smoke green.
- Capability map updated (LES-040); PR ships the RFC Implementation-Status + bullet Acceptance Evidence
  (LES-041).
- No autonomous selection, no baseline, no routes (API is the next package).

## Open questions

1. **Where "required validation" signals come from in a deterministic council.** Leaning: derive
   `ValidationTask`s from (a) candidate `FoundationScore` rows with high `uncertainty_penalty` / low
   confidence on a blocking criterion, and (b) a council `concern` tagged as a validation need. The
   real-model path enriches (a)/(b) later. Resolve at build.
2. **Dossier recommendation tie-break** when two clear-eligible candidates score equally. Leaning:
   prefer higher reversibility / lower lock-in, then flag the tie for the human. Resolve at build.
3. **Does a failed blocking validation reject the candidate or just block selection?** Leaning: mark it
   `challenged` (not `rejected`) so a re-validation can recover it; selection stays blocked. Confirm.

## Dependencies

- **Blocks on:** RFC-0016/0017 (merged), RFC-0018/0019/0020 (Slices 1–3, merged), AOS-COUNCIL-TYPED-001
  (#220, merged).
- **Reuses:** the Council (`run_council`/`synthesize_verdict`/typed payloads), `foundation` candidates/
  scores + `lifecycle.py`, `ApprovalRecord`, the `Provider` seam (deterministic in CI).
- **Enables:** Slice 5 (the selected candidate becomes the immutable Foundation Baseline) and the design
  §20 MVP steps 12–16.

## Implementation Status

- **AOS-COUNCIL-VALIDATION-MODELS-001** (this PR) — the 4 new ORM models (`ValidationTask`,
  `ValidationResult`, `FoundationObjection`, `FoundationDossier`) + two nullable link columns
  (`candidate_id`, `selection_run_id`) on `CouncilReview` + migration `0031` (single head, `0030→0031`,
  mixin-safe: `_audit_columns()` once per table, the `council_reviews` columns are nullable `ADD
  COLUMN`), and `services/foundation_council.py`: `review_candidate` (runs `run_council` over a
  candidate's elements/requirements/score-vector, tags the `CouncilReview`, derives blocking
  `FoundationObjection`s from council concerns + `ValidationTask`s from high-`uncertainty_penalty`/low-
  confidence blocking criteria — AD-10), `resolve_objection` (open→resolved/accepted_exception/
  converted_to_validation), `record_validation_result` (a failed blocking task marks the candidate
  `challenged`, not rejected; clearing all blocking tasks advances the run to `validation_complete`),
  `synthesize_dossier` (**recommends only — never selects**, AD-9; advances to `ready_for_selection`),
  and `select_candidate` (**mandatory human gate** — 409 unless the candidate is eligible with no
  unresolved blocking objection and every blocking validation `passed` (`accepted_exception` is an
  objection resolution, not a validation outcome — `ValidationStatus` has no such state); sets
  `selected`, advances the run, writes an `ApprovalRecord`). Deterministic in CI. Reuses the Council +
  `synthesize_verdict` + `ApprovalRecord` (C2).
- **AOS-COUNCIL-VALIDATION-API-001** (queued) — routes: review-candidate / objections (+resolve) /
  validation-tasks (+result) / synthesize-dossier / select / list / get.

## Final Judge verdict

Pending operator approval. Slice 4 is the adjudication payoff: it reviews the candidates with the
(now-typed) Council, keeps objections visible, turns uncertainty into validation rather than invented
certainty, and gates a human selection — recommend-don't-decide, deterministic in CI. Recommend
acceptance; start AOS-COUNCIL-VALIDATION-MODELS-001 (bundled here), API to follow.
