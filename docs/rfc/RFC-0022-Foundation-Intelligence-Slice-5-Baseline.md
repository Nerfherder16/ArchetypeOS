# RFC-0022 — Foundation Intelligence Slice 5: Foundation Baseline

## Status

Proposed — 2026-07-13. Child of RFC-0016 (Foundation Intelligence Evidence Spine & System Genome), slice 5 of 6. Builds on the merged Slices 0–4 (RFC-0017…RFC-0021).

## Summary

Turns a **selected** foundation candidate (Slice 4's human-gated output) into an **immutable, versioned `FoundationBaseline`** — the durable root-of-trust from which RFC-0015 Decisions and build plans derive (design §12 Stage 14, AD-12, AD-15). Minting is a **second mandatory human gate**; the baseline freezes its constituents (approved elements, target genome, corpus, validation posture) into a reproducible `baseline_hash`, is enforced immutable at the database layer (reconciliation **C4**), and supersedes the project's prior active baseline as a new version. A new baseline creates and links a governing **approved anchor Decision** (AD-15), and a deterministic `compare_baselines` diff plus persisted `review_triggers` give Slice 6 (Continuous Evolution) the primitives it consumes — without any drift *engine* here.

## What already exists (the gap this RFC fills)

Slices 0–4 already shipped most of the baseline scaffolding — this RFC is deliberately narrow:

- `foundation/contracts.py::FoundationBaseline` — the Pydantic contract (already registered in `_ALL_CONTRACT_MODELS`, so `content_hash`/`set_hash` already project it).
- `foundation/enums.py::BaselineStatus` (`active`/`superseded`/`retired`) and `SelectionRunState.BASELINED`.
- `foundation/lifecycle.py` — `LifecycleKind.BASELINE` + `BASELINE_STATUS_TRANSITIONS` (`active→{superseded,retired}`, `superseded→{retired}`) **and** the `selected → baselined` selection-run hop, already wired.

**Missing (this RFC):** the ORM `FoundationBaseline` + `FoundationBaselineElement` tables, migration `0032`, the C4 database-level immutability guard, the mint/supersede/compare service, the anchor-Decision linkage (AD-15), and the HTTP surface.

## Reconciliations honored (RFC-0016)

- **C3** — the baseline mints no `observed` claims; it references the corpus/genome/validation evidence already minted by the deterministic tier. No new truth is invented at baseline time.
- **C4 (load-bearing here)** — immutability via `content_hash` + append-only. The baseline and its element snapshot are frozen at the **database layer** with the same `before_update` event-listener guard that protects `CorpusSnapshot`/`Claim` (`models.py::_assert_evidence_content_immutable`), not merely a service convention. A correction is a **new version**, never an in-place edit.
- **AD-12** — human approval → immutable versioned baseline. Minting requires an `approver`; the row is immutable thereafter except its `status` (active→superseded→retired).
- **AD-15** — the baseline is the higher-order source Decisions/plans derive from; minting creates and links one governing approved anchor Decision, and RFC-0015 plans key off `foundation_baseline_id`/its Decision downstream.

## The C4 immutability decision (the central design call)

Two existing precedents:

- **Hard guard** — `CorpusSnapshot`, `Claim`, and the evidence rows are in `_EVIDENCE_IMMUTABLE_CONTENT_FIELDS`; a mapper `before_update` listener raises `ImmutableContentError` if any *content* field changes. Status/audit columns stay mutable.
- **Soft convention** — `GenomeSnapshot` is documented immutable but only the service refrains from mutating it; no DB guard.

**Decision: `FoundationBaseline` and `FoundationBaselineElement` get the HARD guard** — added to the existing immutable-content registry, reusing the exact same generic listener (generalize its name to `_IMMUTABLE_CONTENT_FIELDS` / `_assert_content_immutable`; the evidence models keep their entries). Rationale: the baseline is the root artifact from which every downstream Decision and plan derives; a silent in-place content edit would corrupt the whole derivation chain with no audit trail, which is precisely what AD-12/C4 exist to prevent. The soft convention is rejected as too weak for the root-of-trust; a lesson already exists (`GenomeSnapshot`'s softer choice) but the baseline's blast radius is strictly larger.

## Design

### Tables (ORM in `models.py`; enums from `aos_core.foundation`)

**`FoundationBaseline`** (`foundation_baselines`), `AuditMixin` + immutable-content guard:

- `project_id` (GUID FK `projects.id`, indexed), `candidate_id` (GUID FK `foundation_candidates.id`), `selection_run_id` (GUID FK `foundation_selection_runs.id`), `target_genome_snapshot_id` (GUID FK `genome_snapshots.id`), `corpus_snapshot_id` (GUID FK `corpus_snapshots.id`, nullable — a project may baseline before a corpus freeze), `approved_decision_id` (GUID FK `decisions.id`) — the AD-15 anchor.
- `baseline_version` (String — the contract's semantic `"1.0"`; **not** `version`, which `AuditMixin` owns — LES-042), `element_set_hash` (String(64)), `baseline_hash` (String(64), indexed), `review_triggers` (JSONField, default list), `approved_by` (String(128)), `approved_at` / `effective_from` (DateTime tz).
- `status` carries `BaselineStatus` (active/superseded/retired) — the one mutable field, driven through `LifecycleKind.BASELINE`.
- `supersedes_baseline_id` (GUID self-FK, nullable) — the version chain (EvidenceSourceVersion pattern).

**`FoundationBaselineElement`** (`foundation_baseline_elements`), `AuditMixin` + immutable-content guard: a **frozen copy** of each approved `FoundationElement` at mint time so the baseline is self-contained and reproducible even if the source candidate's elements later change — `baseline_id` (GUID FK, indexed), `source_element_id` (GUID FK `foundation_elements.id`), `domain`, `title`, `decision`, `rationale`, `technology_refs`/`claim_ids`/`requirement_ids`/`tradeoffs`/`risks` (JSON), `verification_method`, `content_hash` (String(64)). (Membership-snapshot pattern, like `CorpusSnapshotSource`.)

Immutable content fields (added to the registry): baseline — everything except `status` + audit; element — every content field + `content_hash`.

### `baseline_hash` (reproducible, C4)

`element_set_hash = set_hash([e.content_hash for e in baseline_elements])` (permutation-invariant, mirrors `claim_set_hash`). `baseline_hash = content_hash(<canonical FoundationBaseline projection>)` — the projection includes `candidate_id`, `target_genome_snapshot_id`, `corpus_snapshot_id`, `approved_decision_id`, `element_set_hash`, `baseline_version`, and `review_triggers`, so the hash is reproducible from the frozen constituents and any tamper is detectable.

### `services/foundation_baseline.py`

- **`mint_baseline(db, *, selection_run_id, approver, review_triggers=None)`** — the mandatory human gate. **409** unless the run is `SELECTED` with exactly one `SELECTED` candidate. Then: snapshot the candidate's approved `FoundationElement`s into `FoundationBaselineElement` rows (freezing `content_hash` via `content_hash(contracts.FoundationElement)`); compute `element_set_hash`; **create + approve a governing anchor `Decision`** ("Adopt foundation '<candidate>' for project <p>", via `services/decisions.py::create_decision` + `approve_decision(approver)`) and link it as `approved_decision_id` (AD-15); compute `baseline_hash`; supersede the project's prior `active` baseline (`status → superseded`, `supersedes_baseline_id` chain, `baseline_version` = prior+1 else `"1.0"`); insert the immutable `FoundationBaseline` (`status=active`); write an `ApprovalRecord(requested_capability="foundation.mint_baseline", target=baseline.id, approval_status="approved")` (the `select_candidate` pattern); advance the run `SELECTED → BASELINED` via `_advance_run_at_least`. All in one transaction.
- **`supersede_baseline` / `retire_baseline`** — status transitions through `LifecycleKind.BASELINE` (a human/operator action; a superseded baseline is retained, never deleted).
- **`compare_baselines(db, *, base_id, other_id)`** — a deterministic diff: elements added/removed/changed by domain (keyed on `source_element_id` + `content_hash`), target-genome-snapshot delta (ids + version), `baseline_hash` equality, and `review_triggers` delta. Pure/read-only — the primitive Slice 6 consumes.

No new transition table — every run/baseline state change goes through `foundation/lifecycle.py`.

### Migration `0032`

`down_revision='0031'`, single head. `create_table` for `foundation_baselines` + `foundation_baseline_elements` via a locally-copied `_audit_columns()` (LES-042: `status`/`version` come only from the helper, never redeclared). Additive, dialect-agnostic; validated with `alembic upgrade 0031:0032 --sql` under the Postgres dialect.

### Tests (hermetic, `apps/api/tests/test_foundation_baseline_*.py`)

- Full walkthrough: reviewable run → select → **mint** → assert baseline `active`, run `BASELINED`, anchor Decision `approved` + linked, `ApprovalRecord` written, elements frozen, `baseline_hash`/`element_set_hash` reproducible from constituents.
- **C4 immutability**: an UPDATE to a baseline/element content field raises `ImmutableContentError`; a `status` transition (active→superseded) succeeds.
- Gate: `mint_baseline` 409s a non-`SELECTED` run / a run with no selected candidate.
- Versioning: a second mint supersedes the prior baseline (`superseded`, `supersedes_baseline_id` set, `baseline_version` incremented).
- `compare_baselines`: added/removed/changed elements and genome delta computed deterministically; identical baselines → empty diff + equal hash.

## Non-goals (explicit boundary)

- **The drift/evolution engine is Slice 6 (RFC-0023).** This RFC persists `review_triggers` and ships `compare_baselines`, but does **not** detect drift, watch new evidence, emit drift events, or propose replacement baselines (design §16). RFC-0016 §189 places the active monitoring there.
- No RFC-0015 build-plan *generation* — only the baseline→Decision linkage that plans key off. No PR Guardian baseline checks (Slice 6).
- No agent-minted content (C3).

## Work items

1. **AOS-FOUNDATION-BASELINE-MODELS-001** (bundled with this RFC) — the two ORM tables + the C4 immutability-guard registry extension + migration `0032` + `services/foundation_baseline.py` (`mint_baseline`, `supersede`/`retire`, `compare_baselines`) + hermetic + immutability tests.
2. **AOS-FOUNDATION-BASELINE-API-001** (follows) — routes: `POST /foundation-runs/{run_id}/baseline`, `GET /projects/{project_id}/foundation-baselines`, `GET /foundation-baselines/{baseline_id}`, `GET /foundation-baselines/{a}/compare/{b}`; schemas; tests.

## Alternatives considered

- **Soft (service-only) immutability** like `GenomeSnapshot` — rejected: the baseline is the root-of-trust; a DB guard is warranted (see the C4 decision).
- **Reference the candidate's live elements instead of freezing copies** — rejected: the baseline would silently change when a candidate's elements are later edited, breaking reproducibility of `baseline_hash` and the audit trail.
- **Require a pre-existing `approved_decision_id` passed in** rather than minting the anchor Decision — rejected: AD-15 makes the baseline the *source* of the governing Decision; creating+approving it atomically at mint keeps the single human act authoritative and avoids an orphan-decision race.
- **Store the semantic version in `AuditMixin.version`** — rejected (LES-042): that column is the audit int; the contract's `"1.0"` string lives in `baseline_version`.

## Risks

- **Anchor-Decision evidence gate** — `approve_decision` 409s a `NEEDS_EVIDENCE` decision; the anchor must be created with the selection run's evidence refs so it approves cleanly. Mitigation: derive the anchor Decision's evidence from the selected candidate's claims/validation results; covered by a test.
- **Immutability guard over-reach** — the `before_update` guard must exclude `status`/audit or supersession breaks. Mitigation: the registry lists only content fields (the evidence precedent already works this way); a test asserts the status transition succeeds.
- **Corpus optionality** — a project may baseline before freezing a corpus; `corpus_snapshot_id` is nullable and excluded from the required-evidence gate.

## Acceptance criteria (this RFC + AOS-FOUNDATION-BASELINE-MODELS-001)

- `mint_baseline` produces an `active`, immutable, hash-reproducible baseline from a `SELECTED` run, links an approved anchor Decision (AD-15), writes an `ApprovalRecord`, and advances the run to `BASELINED`; 409s otherwise.
- A content-field UPDATE on a baseline or element raises `ImmutableContentError`; a `status` transition succeeds (C4/AD-12).
- A second mint supersedes the prior baseline and increments `baseline_version`, retaining the superseded row.
- `compare_baselines` returns a deterministic element/genome/hash diff.
- Migration `0032` is single-head, mixin-safe, and generates valid Postgres DDL.
- Hermetic tests pass; full API suite green; compose-smoke green.

## Dependencies

Slices 0–4 (merged). `services/decisions.py` (anchor Decision), `foundation/serialization.py` (hashing), `foundation/lifecycle.py` (transitions), the `_EVIDENCE_IMMUTABLE_CONTENT_FIELDS` guard.

## Implementation Status

- **AOS-FOUNDATION-BASELINE-MODELS-001** (this PR) — the two ORM tables (`FoundationBaseline`,
  `FoundationBaselineElement`) + migration `0032` (single head `0031→0032`, mixin-safe) + the C4
  immutability-guard generalization (`_EVIDENCE_IMMUTABLE_CONTENT_FIELDS`→`_IMMUTABLE_CONTENT_FIELDS`,
  `_assert_evidence_content_immutable`→`_assert_content_immutable`, reusing the same `before_update`
  listener; the 5 evidence entries unchanged, `FoundationBaseline`/`FoundationBaselineElement` added
  with `status`+audit excluded so status transitions stay legal), and `services/foundation_baseline.py`:
  `mint_baseline` (409 unless a `selected` run with a selected candidate; freezes elements to
  reproducible `content_hash`es, computes `element_set_hash` + a field-prefixed `baseline_hash`, mints +
  approves the AD-15 anchor Decision, supersedes the prior active baseline with a version bump, writes an
  `ApprovalRecord`, advances the run `selected→baselined` — one transaction, INSERT-only before commit so
  the C4 guard never sees a mutation on a fresh row), `compare_baselines` (deterministic element/genome/
  trigger diff), `supersede_baseline`/`retire_baseline` (status-only transitions). 11 hermetic tests
  including C4 immutability (content edit refused; status transition allowed) and `baseline_hash`
  reproducibility. Full API suite green (914 passed); the guard rename broke no evidence-immutability test.
- **AOS-FOUNDATION-BASELINE-API-001** — queued.

## Final Judge verdict

Recommend acceptance. Slice 5 is the payoff of the whole Foundation line: it converts a validated, human-selected candidate into the immutable, versioned, hash-reproducible root artifact the rest of the platform builds on — with a database-level C4 guard, an AD-15 governing Decision, and a deterministic comparison primitive, while cleanly deferring the active evolution engine to Slice 6. Start AOS-FOUNDATION-BASELINE-MODELS-001; API to follow.
