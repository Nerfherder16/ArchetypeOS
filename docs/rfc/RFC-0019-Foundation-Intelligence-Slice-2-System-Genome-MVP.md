# RFC-0019 — Foundation Intelligence Slice 2: System Genome MVP

## Status

Proposed (2026-07-12). Third child RFC under **RFC-0016**; first consumer of the merged Evidence
Spine (RFC-0018, #211/#212/#214). Delivers the design's **Slice 2** (`docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md`
§6–§7, §18): the **System Genome** as versioned, evidence-backed traits across the design's 16
dimensions, in separate `current` / `intended` snapshots, derived **deterministically** from the
claims the Evidence Spine now holds. Per the design, "the first version should use deterministic
rules and human review before advanced agent classification" — so **no LLM trait classification in
this slice**.

## Summary

Adds the **genome domain** to the ORM + one additive migration (**0029**; head is `0028`):
`genome_snapshots`, `genome_traits`, `genome_trait_claims` (normalized trait↔claim links),
`system_archetypes`, `genome_deltas`. A `services/genome.py` derives a `GenomeSnapshot` for a given
`state_view` from a project's claims via a **deterministic rule table** (`services/genome_rules.py`):
each rule reads claims (by domain / claim_type / truth_layer / keyword) and emits a `GenomeTrait`
with supporting/opposing claim links, a **coverage-calibrated** confidence, and a criticality. The
snapshot rolls traits into a small set of readable **archetypes**, computes **quality indicators**
(coverage by dimension, unsupported-trait count, opposing-claim count, unknown dimensions), and
generates targeted **OpenQuestions** only where a foundation-shaping dimension lacks evidence.

Two work packages: **AOS-GENOME-MODELS-001** (tables + migration + deterministic derivation service +
quality indicators + tests — bundled with this RFC) and **AOS-GENOME-API-001** (routes:
generate / list / get / review / questions / compare).

### The AD-4 boundary (locked in RFC-0016), restated

**Repository DNA describes code; the Genome describes the engineered system.** The Genome does **not**
read `RepositoryDNA` directly — it reads **claims**. DNA already became `observed` claims via the C5
backfill (#214), so the derivation path is uniform: *claims → traits*, never *DNA → traits*. This
keeps a multi-repo / hardware / human-workflow system describable by the same mechanism (a future
non-repo source just contributes more claims).

## Problem

The Evidence Spine can store and query claims, but nothing yet answers "**what kind of system is
this?**" There is no `genome` anywhere in code (grep-confirmed pre-Slice-2). Slices 3–5 (requirements,
candidates, baseline) all read a Genome; without it they have no input. And the design's §20 MVP
needs separate **Current** and **Intended** genomes (steps 7–8) to show drift between code and intent.

## Goals

- `GenomeSnapshot` per `state_view` (`current` / `intended`), versioned and immutable-once-`approved`,
  each tied to a `corpus_snapshot_id` so a genome is reproducible against a frozen claim set.
- Evidence-backed `GenomeTrait`s across the 16 dimensions (RFC-0017 `GenomeDimension`), each linking
  its supporting **and** opposing claims (design §6.4) — no trait without provenance or an explicit
  `unknown` classification.
- **Deterministic derivation** (rules over claims), human-reviewable; **no LLM** in this slice.
- **Current vs Intended separation** driven by truth layer: `current` derives from `observed` (+
  deterministic-`inferred`) claims; `intended` derives from `claimed`/document claims. A dimension
  where the two disagree is surfaced (feeds the Contradiction Inbox / drift, later slices).
- **Coverage-honest quality indicators** — `aggregate_confidence` is **coverage-calibrated, never a
  naive average** (LES-023): a confident-looking genome over thin evidence must not read as complete.
- Targeted `OpenQuestion`s only for foundation-shaping dimensions that lack evidence (design §7),
  ranked by expected decision impact.
- `genome_deltas` to compare two snapshots (current vs intended, or version N vs N+1).
- Hermetic: rules run offline over claims; sqlite `create_all` green; single Alembic head.

## Non-goals

- **No LLM / agent classification.** Deterministic rules + human review only (design Slice 2). Agent
  classification is a later slice.
- **No foundation requirements/candidates/baseline** (Slices 3–5).
- **No `target` genome authoring UI** — `target` is a state_view the schema supports but this slice
  only *derives* `current`/`intended`; `target` is set in Slice 3+.
- **No new authority model** — genome `review`/`approve` reuses the existing approval pattern
  (`ApprovalRecord`), like decisions.
- **No provenance/genome UI** (that's AOS-GENOME-UI-001, later).

## Design

### C2 reuse check (RFC-0016)

Measured against existing models: `RepositoryDNA` is per-repository and flat — it is **evidence
feeding** the genome (AD-4), not the genome; not reusable as the system classification.
`Evaluation`/`Recommendation` are decision-support, not a dimensional classification. No existing
table represents a multi-dimensional system genome, so the genome tables are **new** (justified). The
genome **reads** the merged `claims`/`evidence_conflicts`/`corpus_snapshots` — it does not duplicate
them.

### Tables (ORM in `models.py`; enums from `aos_core.foundation`)

- **GenomeSnapshot** — `project_id` FK, `corpus_snapshot_id` FK (nullable until a freeze exists),
  `state_view` (StateView), `version` (int), `summary`, `coverage` (Float), `aggregate_confidence`
  (Float), `open_question_count`, `critical_conflict_count`, `generated_by` (String — the ruleset id/
  version), `approved_by`/`approved_at`. Status via AuditMixin (`draft`/`reviewed`/`approved`/
  `superseded`). Invariant (service-enforced): at most one non-superseded snapshot per
  `(project_id, state_view)`.
- **GenomeTrait** — `genome_snapshot_id` FK, `dimension` (GenomeDimension), `trait_key` (String —
  open vocabulary), `value` (JSON — bool/str/number), `value_type`, `classification`
  (TraitClassification), `confidence` (Float), `stability`, `criticality`, `rationale`,
  `source_methods` (JSON list), `human_locked` (bool). Index on `(genome_snapshot_id, dimension)`.
- **GenomeTraitClaim** — `trait_id` FK, `claim_id` FK, `polarity` (`supporting`/`opposing`) — the
  normalized trait↔claim provenance (design §6.4 `supporting_claim_ids`/`opposing_claim_ids` kept
  queryable, not JSON blobs).
- **SystemArchetype** — `genome_snapshot_id` FK, `name`, `tier` (`primary`/`secondary`), `confidence`
  (Float), `trait_ids` (JSON list — the traits that produced it). Readable summary, not a substitute
  for traits (design §6.6).
- **GenomeDelta** — `project_id` FK, `from_snapshot_id` FK, `to_snapshot_id` FK, `changes` (JSON:
  added/removed/changed traits + confidence/coverage deltas), `summary`.

`OpenQuestion` (from Slice 1) gets its `genome_snapshot_id` populated by this slice.

### `services/genome_rules.py` — the deterministic derivation rule table

A list of pure `TraitRule`s, each: `dimension`, `trait_key`, a `predicate(claims) -> (value,
classification, matched_claim_ids, opposing_claim_ids, confidence)`, and a `criticality`. Rules match
claims by `domain` / `claim_type` / keyword over `statement` (e.g. a `runtime_service` observed claim
mentioning a queue → `runtime_topology: distributed_workers`; a `deployment` claim "no public cloud"
→ `deployment_ownership: local_first`). Seed rules cover the **foundation-shaping** dimensions first
(runtime_topology, deployment_ownership, data_profile, ai_autonomy, assurance_criticality,
security_privacy) — breadth over all 16 grows later. Every rule is unit-testable in isolation over a
fixture claim set. This module is the genome analog of `foundation/` — deterministic, hermetic, the
single source of derivation logic.

### `services/genome.py` — derivation + quality

- `generate_genome(db, *, project_id, state_view, corpus_snapshot_id=None) -> GenomeSnapshot`:
  select the claim set for the `state_view` (**current** = `observed` + deterministic-`inferred`;
  **intended** = `claimed` + `inferred`-from-documents), run every `TraitRule`, persist traits +
  `GenomeTraitClaim` links, roll up archetypes, compute quality indicators, generate open questions,
  supersede the prior snapshot for that `(project, state_view)`. Draft status; **human review before
  `approved`** (`review_genome`/`approve_genome`, writing an `ApprovalRecord`).
- **Coverage-calibrated confidence (LES-023):** `coverage = (dimensions with ≥1 evidence-backed
  trait) / (foundation-shaping dimensions)`; `aggregate_confidence = mean(trait.confidence) *
  coverage_penalty`, where a dimension with **no** evidence contributes an explicit `unknown` trait
  at confidence 0 (it cannot be silently omitted to inflate the mean). A test asserts a sparse-
  evidence genome yields *lower* aggregate_confidence than a dense one with the same per-trait scores.
- `compare_genomes(db, from_id, to_id) -> GenomeDelta`: pure diff over traits (added/removed/changed
  classification or value) + coverage/confidence deltas.
- `generate_open_questions`: for each foundation-shaping dimension whose best trait is `unknown`/
  low-confidence, emit one `OpenQuestion` (affected_dimensions, materiality by criticality, reason).

### Migration 0029

Additive `create_table` for the 5 genome tables + the `open_questions.genome_snapshot_id` FK column
(nullable add), `down_revision="0028"`, single head, `import aos_core.models`, no-drift +
compose-smoke validated.

### Tests (hermetic, `apps/api/tests/test_genome_*.py`)

Rule-level (each seed rule fires on a matching claim, abstains otherwise); `generate_genome` over the
§20 fixture (backfilled) produces a `current` and an `intended` snapshot with the expected traits +
claim links; **current≠intended** on at least one dimension (the code-vs-intent contradiction, §20
step 6→8); coverage-calibration (sparse < dense aggregate_confidence, LES-023); `unknown` dimensions
are explicit, not omitted; open questions generated only for unevidenced foundation-shaping
dimensions; `compare_genomes` delta; one-non-superseded-per-state_view invariant; supersession on
re-generate.

## Alternatives considered

- **Derive traits from `RepositoryDNA` directly.** Rejected — violates AD-4; DNA is one repo's code.
  Deriving from claims keeps the system (multi-repo/hardware/human) describable and reuses the C5
  backfill. DNA's signal already reaches the genome *as claims*.
- **One `genome` JSON document per project.** Rejected — design §15 forbids it; traits + claim links
  must stay queryable/comparable/versioned. Hence normalized tables.
- **LLM trait classifier now.** Deferred (design Slice 2 = deterministic + human first); it attaches
  behind the same `services/genome.py` seam later, exactly as RFC-0005 did for the Final Judge.
- **Average per-trait confidence for `aggregate_confidence`.** Rejected — re-commits LES-023
  (confident genome over thin evidence). Coverage-calibrated instead.

## Evidence

- RFC-0016 (AD-4, C2, slice map → RFC-0019); RFC-0017 (`GenomeDimension`/`StateView`/
  `TraitClassification` enums, `content_hash`); RFC-0018 (the `claims`/`evidence_conflicts`/
  `corpus_snapshots` this reads; C5 backfill made DNA into `observed` claims).
- `packages/aos_core/aos_core/models.py` — AuditMixin/GUID/JSONField reused; `OpenQuestion` (Slice 1)
  gets `genome_snapshot_id`.
- `services/decisions.py` + `ApprovalRecord` — the review/approve pattern `review_genome` mirrors.
- `knowledge/wiki/lessons/LES-023` — the coverage-calibration requirement.
- Current Alembic head `0028_evidence_spine`; 0029 chains from it.

## Security impact

None new — derivation is deterministic and offline over already-stored claims; no routes in this
package (routes are AOS-GENOME-API-001, reusing the approval pattern). Genome inherits claim
sensitivity transitively (a trait's supporting claims may be sensitive) — but enforcement remains
RFC-0024; this slice stores links, does not gate reads.

## Compliance impact

Positive: the Genome is the evidence-backed, versioned, reproducible (corpus-pinned) system
classification the traceability chain needs between claims and foundation requirements. Every trait
traces to claims; `docs/capability-map/layer-02.md` (or a new Layer-3 entry — decide at build) gains
RFC-0019.

## Migration plan

One additive migration `0029_system_genome`, `down_revision="0028"`, single head, `import
aos_core.models`, no-drift + compose-smoke. No data migration; genomes are generated on demand from
claims (idempotent-ish via supersession).

## Risks

- **Overconfidence (LES-023).** Mitigated by coverage-calibration + a regression test.
- **Rule quality / breadth.** Seed rules cover foundation-shaping dimensions first; breadth grows
  incrementally. Unevidenced dimensions are explicit `unknown` + an open question, never guessed.
- **Current/Intended mis-split.** The truth-layer→state-view mapping is explicit and tested.
- **Shared `models.py` + migration churn.** Opus verifies the migration + derivation + calibration
  line-by-line; builder ≠ verifier.

## Acceptance criteria (this RFC + AOS-GENOME-MODELS-001)

- Operator approves the genome tables, the deterministic-rule derivation, the coverage-calibrated
  confidence, and the current/intended split.
- AOS-GENOME-MODELS-001 lands: 5 genome tables + migration 0029 (single head) + `services/genome.py`
  + `services/genome_rules.py` + hermetic `test_genome_*` proving derivation, current≠intended on the
  §20 fixture, coverage-calibration (LES-023), explicit `unknown` dimensions, open-question
  generation, delta, and the one-non-superseded-per-state_view invariant. Builder ≠ verifier; full
  suite + ruff green.
- Capability map updated (LES-040); PR ships the RFC Implementation-Status + bullet Acceptance
  Evidence up front (LES-041).
- No LLM, no foundation logic, no routes (API is the next package).

## Open questions

1. **Genome home layer in the capability map** — Layer 2 (Research/Evidence) vs Layer 3
   (Architecture/Modeling). Leaning Layer 3 (the Genome is a system model), cross-ref Layer 2.
   Resolve at build.
2. **`current` inclusion of `inferred`.** Leaning: `current` = `observed` + `inferred` whose
   `derivation.parent_claim_ids` are all observed (a purely-machine inference over facts); other
   `inferred` → `intended`. Confirm in AOS-GENOME-MODELS-001.
3. **Archetype rule set.** Seed 2–3 archetypes (e.g. "Local-First Control Plane") from trait
   combinations; keep it small and readable (design §6.6). Expand later.

## Dependencies

- **Blocks on:** RFC-0016, RFC-0017 (merged), RFC-0018 Slice 1 (merged #211/#212/#214).
- **Reuses:** `models.py` mixins; `claims`/`corpus_snapshots`/`evidence_conflicts`; the approval
  pattern; `foundation` enums.
- **Enables:** Slice 3 (Foundation Requirements compile from Genome traits + claims), and the design
  §20 MVP steps 7–9.

## Implementation Status

- **AOS-GENOME-MODELS-001** (this PR) — the 5 genome ORM models + migration `0029` (single head,
  `0028→0029`; wires `open_questions.genome_snapshot_id` to a real FK), `services/genome_rules.py`
  (8 deterministic seed rules across the 6 foundation-shaping dimensions, with negation-aware keyword
  matching so mutually-exclusive traits don't double-fire; `FOUNDATION_SHAPING_DIMENSIONS` derived
  from the rule table), and `services/genome.py` (`generate_genome` with the current/intended split
  and coverage-calibrated `aggregate_confidence = mean(evidence-backed conf) × coverage`;
  `review_genome`/`approve_genome` via `ApprovalRecord`; `compare_genomes` delta; explicit `unknown`
  traits for unevidenced foundation-shaping dimensions; supersession). Reads **claims only** (AD-4).
- **AOS-GENOME-API-001** (queued) — routes: generate / list / get / review / questions / compare.
- **AOS-GENOME-UI-001** (queued) — the genome view (current/intended toggle, trait confidence,
  coverage, unknowns).

## Final Judge verdict

Pending operator approval. The Genome turns the evidence graph into a system classification — still
deterministic and human-reviewed (no LLM yet), coverage-honest (no LES-023 overconfidence), and
reproducible against a frozen corpus. It reads claims, never DNA (AD-4), so it scales past code.
Recommend acceptance; start AOS-GENOME-MODELS-001 (bundled here), API to follow.
