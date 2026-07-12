# RFC-0017 — Foundation Intelligence Slice 0: Vocabulary & Contracts

## Status

Proposed (2026-07-12). First child RFC under **RFC-0016** (accepted, merged in PR #208). Delivers
the design's **Slice 0** (`docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md` §18): canonical enums, a
single-source Pydantic contract layer with generated JSON Schemas, the lifecycle transition
table, the evidence authority matrix, the **C4 canonical-serialization spec**, the **C3
truth-layer minter guard**, and example fixtures. **No tables, no migrations, no API routes, no
LLM, no UI, no persistence.** Pure Python contracts + pure functions + fixtures + tests, hermetic
in CI. This is the vocabulary every later slice imports; getting it right once avoids re-spelling
the domain in each of RFC-0018…RFC-0024.

## Summary

Slice 0 stands up a new self-contained subpackage `packages/aos_core/aos_core/foundation/` holding
the capability's **contracts** — the enums, schemas, state-transition rules, authority rules, and
hashing spec — with **zero runtime coupling** (it imports nothing from `services/`, `apps/`, or the
ORM, and nothing imports it yet). It is the deterministic tier of the capability: pure data and
pure functions, fully unit-testable offline.

Four of RFC-0016's five locked reconciliations get their **enforceable contract form here**, before
any row exists to violate them:

- **C3** (deterministic-only `observed`) becomes the pure function `allowed_truth_layers(minter)`,
  unit-tested — the guard `create_claim` will call in Slice 1.
- **C4** (immutability is a mechanism) becomes the `canonical_bytes()` + `content_hash()` spec and
  code, unit-tested for determinism and field-projection.
- **C1** (decided-claim-is-a-`Decision`-projection) becomes a schema validator on `Claim`
  (`truth_layer="decided"` ⇒ `derivation.method="approved"` **and** a `decision_ref` present).
- **C2** (reuse-vs-new) is expressed as contract-level *links* (`recommendation_ref`,
  `evaluation_ref`) on the foundation schemas so the reuse target is named in the type, not
  discovered later.

No behavior ships; this PR is the argument for the contract shapes. Implementation is one work
package (**AOS-FOUND-CONTRACTS-001**) after acceptance.

## Problem

RFC-0016 locked the *decisions*; nothing yet encodes the *vocabulary*. Without a single canonical
contract layer:

- Each of Slices 1–6 would re-declare truth layers, claim types, statuses, conflict types, genome
  dimensions, and selection states — guaranteeing drift between the ORM (Slice 1+), the API
  schemas (`apps/api/app/schemas.py` pattern), and the UI.
- The four reconciliations that RFC-0016 made binding (C1–C4) have no testable form until a table
  exists, so the first place they can fail is a migration — the most expensive place.
- There is no agreed hashing spec, so `content_hash` / `claim_set_hash` / `baseline_hash`
  (design §4.3, §5, §14) would be invented per-slice and be mutually irreproducible.

The repo already proves the pattern works: `V0_1_DATA_MODEL.md` defined the data contract *before*
endpoints, and shared domain types live in `packages/aos_core` (RFC-0006). Slice 0 is that
discipline applied to Foundation Intelligence.

## Goals

- One canonical, import-light source of truth for the capability's vocabulary and contracts,
  reused verbatim by every later slice (ORM columns, API DTOs, UI enums all derive from it).
- C1–C4 given **testable, pure-function / schema-validator form now**, so Slice 1 wires guards it
  can already trust rather than inventing them at migration time.
- A deterministic hashing spec that makes immutable-row and corpus/baseline hashes reproducible
  across processes and languages.
- JSON Schemas generated from the Pydantic models (single source; schemas are a derived artifact
  for UI/external consumers), with a CI drift check.
- Fixtures seeding the design's §20 MVP scenario, usable as golden inputs by Slice 1+ tests.
- Hermetic: no network, no DB, no model calls; the whole slice runs in the deterministic tier.

## Non-goals

- **No persistence.** No SQLAlchemy models, no Alembic migration, no `Base.metadata` entry. (Slice 1
  / RFC-0018 owns the evidence tables.)
- **No API/UI/worker.** No FastAPI routes, no React, no `job_type`, no handler.
- **No LLM / extraction.** No agent mints anything; fixtures are hand-authored.
- **No enforcement wiring.** The C3 guard and C4 hasher are *defined and tested* here but not yet
  called by any create/ingest path (that is Slice 1).
- **No genome/foundation logic.** No trait derivation, no scoring, no eligibility — only the *shapes*
  those slices will fill.

## Design

### Layout — a new leaf subpackage (imports nothing from the app)

```
packages/aos_core/aos_core/foundation/
    __init__.py            # re-exports the public contract surface
    enums.py               # all StrEnum vocabularies (the single source)
    truth.py               # C3: MinterClass + allowed_truth_layers(minter) -> frozenset
    contracts.py           # Pydantic v2 models for every entity (evidence/genome/foundation)
    lifecycle.py           # transition tables + can_transition(entity, frm, to) -> bool
    authority.py           # AuthorityDomain/Level + authority_of(source_type, domain) -> level
    serialization.py       # C4: canonical_bytes(model) + content_hash / set_hash
    fixtures/              # §20 MVP scenario as JSON (golden inputs for later slices)
        mvp_scenario.json
schemas/foundation/        # GENERATED JSON Schemas (derived from contracts.py)
scripts/gen_foundation_schemas.py   # regenerates schemas/foundation/ from the Pydantic models
packages/aos_core/tests/foundation/ # unit tests (pure, hermetic)
```

Constraint (enforced by a test): `foundation/` may import only stdlib + `pydantic`. A test asserts
no `foundation/*` module imports `aos_core.models`, `aos_core.services`, `apps.*`, or `sqlalchemy` —
so the contract layer stays a true leaf and Slice 1 can depend on it without a cycle.

### Enums — the single vocabulary (`enums.py`, Python `StrEnum`)

One `StrEnum` per controlled vocabulary in the design, values verbatim from the source of record:

- **Evidence:** `SourceType`, `SourceOrigin`, `Sensitivity`, `SourceStatus`, `IngestionMethod`,
  `ExtractionMethod`, `TruthLayer` (`observed|claimed|inferred|decided`), `ClaimType`
  (`fact|requirement|constraint|preference|hypothesis|finding|risk|assumption|decision_candidate|definition`),
  `Polarity`, `Materiality`, `ClaimStatus`, `DerivationMethod` (`direct|extracted|aggregated|inferred|approved`),
  `EvidenceRelationship` (`supports|opposes|qualifies|originates|verifies|invalidates`),
  `ClaimRelationship` (`supports|contradicts|supersedes|refines|duplicates|depends_on|derived_from|implements|violates|applies_to|validated_by|invalidated_by`),
  `ConflictType`, `ConflictStatus`, `Strength`.
- **Genome:** `StateView` (`current|intended|target|candidate`), `GenomeStatus`, `GenomeDimension`
  (the 16 dimensions A–P as stable keys, e.g. `runtime_topology`, `deployment_ownership`, …),
  `TraitClassification` (`primary|secondary|conditional|absent|unknown`), `Stability`,
  `Criticality` (`informational|important|foundation_shaping`), `AnswerType`, `QuestionStatus`.
- **Foundation:** `RequirementType` (`hard_constraint|required_capability|quality_attribute|preference|optimization_goal`),
  `Priority` (`must|should|could`), `FoundationDomain` (the 16 domains of §9.2),
  `CandidateStatus` (`draft|eligible|challenged|validation_required|selectable|rejected|selected`),
  `Reversibility`, `EvaluationCriterion` (the 20 criteria of §10.2), `ValidationType`,
  `ValidationStatus`, `BaselineStatus`.
- **Lifecycle:** `SelectionRunState` (the 22 states of §13), `AuthorityDomain`, `AuthorityLevel`,
  `MinterClass`.

`GenomeDimension` also carries a frozen mapping `DIMENSION_TRAIT_KEYS` documenting the design's §6.5
enumerations as *advisory* trait-key hints (not a closed set — traits are open-vocabulary strings;
this is a lint aid, not a constraint).

### C3 as a pure function (`truth.py`)

```python
class MinterClass(StrEnum):
    DETERMINISTIC_TOOL = "deterministic_tool"   # scanner, lockfile/manifest parser, test runner, authenticated-record ingest
    AGENT = "agent"                             # any LLM/provider output
    HUMAN = "human"                             # a person asserting
    APPROVAL_PROCESS = "approval_process"       # the governed Decision approval path

_ALLOWED: dict[MinterClass, frozenset[TruthLayer]] = {
    MinterClass.DETERMINISTIC_TOOL: frozenset({TruthLayer.OBSERVED, TruthLayer.INFERRED}),
    MinterClass.AGENT:              frozenset({TruthLayer.CLAIMED, TruthLayer.INFERRED}),
    MinterClass.HUMAN:              frozenset({TruthLayer.CLAIMED}),
    MinterClass.APPROVAL_PROCESS:   frozenset({TruthLayer.DECIDED}),
}

def allowed_truth_layers(minter: MinterClass) -> frozenset[TruthLayer]: ...
def may_mint(minter: MinterClass, layer: TruthLayer) -> bool: ...
```

The load-bearing rows: **only `DETERMINISTIC_TOOL` may mint `observed`; no minter but
`APPROVAL_PROCESS` may mint `decided`; an `AGENT` can never mint `observed`.** (`DETERMINISTIC_TOOL`
gets `inferred` too because deterministic derivation — e.g. "a lockfile + a Dockerfile ⇒ this
service exists" — is a legitimate machine inference; the guard's job is to keep *`observed`* and
*`decided`* honest.) Slice 1's `create_claim` calls `may_mint`; here it is unit-tested exhaustively
over the `MinterClass × TruthLayer` matrix.

### Contracts — Pydantic v2, one model per entity (`contracts.py`)

A frozen (`model_config = ConfigDict(frozen=True, extra="forbid")`) Pydantic model per design entity:
`EvidenceSource`, `EvidenceSourceVersion`, `EvidenceFragment` (+ `Locator`), `Claim` (+ `ClaimScope`,
`Derivation`), `ClaimEvidenceLink`, `ClaimRelationshipEdge`, `EvidenceConflict`, `CorpusSnapshot`
(+ `RepositoryRef`), `OpenQuestion`, `GenomeSnapshot`, `GenomeTrait`, `Archetype`,
`FoundationRequirement`, `FoundationCandidate`, `FoundationElement`, `CandidateScore`,
`ValidationTask`, `FoundationBaseline`, `SelectionStageEvent`. Fields and value-types are exactly the
design's JSON blocks; enum-typed where a controlled vocabulary exists; `Locator` is the open JSONB-
bound structure kept as a permissive sub-model (design §4.4).

Reconciliation validators live on the models themselves:

- **C1** — `Claim` model validator: `truth_layer == "decided"` ⇒ `derivation.method == "approved"`
  **and** `decision_ref` is set; conversely a non-decided claim must **not** carry `decision_ref`.
- **C2** — `FoundationCandidate` carries optional `recommendation_ref`; `CandidateScore` carries
  optional `evaluation_ref`; `ValidationTask` carries optional `result_refs` (to
  `Benchmark`/`Experiment`/`Evaluation`). The reuse target from RFC-0016 C2 is named in the schema,
  so Slice 3's "reuse vs new" decision is a link that already exists, not a retrofit.
- **provenance** — every mintable entity carries `minted_by: MinterClass`; a `Claim` validator
  cross-checks `may_mint(minted_by, truth_layer)` so an invalid pairing fails **at construction**,
  not at DB write.

### JSON Schema — generated, not hand-written

`scripts/gen_foundation_schemas.py` calls `Model.model_json_schema()` for each contract and writes
`schemas/foundation/<Entity>.json`. Pydantic is the **single source**; JSON Schema is a derived
artifact for the eventual UI/external consumers. A unit test regenerates in-memory and asserts byte
-equality with the checked-in files (drift guard) — same "generated artifact stays in sync" pattern
the repo uses elsewhere.

### Lifecycle transition table (`lifecycle.py`)

Data-driven, not code-branching. One `dict[State, frozenset[State]]` per lifecycle:

- `SELECTION_RUN_TRANSITIONS` — the §13 machine (`draft → intake_complete → corpus_frozen →
  evidence_extracted → … → baselined → execution_compiled → monitoring`), plus the lateral
  terminals every state may reach (`blocked`, `cancelled`, `superseded`) and the documented
  re-open edges (`monitoring → genome_review` on a drift-triggered reevaluation).
- Per-entity status tables: `CLAIM_STATUS_TRANSITIONS`, `CONFLICT_STATUS_TRANSITIONS`,
  `GENOME_STATUS_TRANSITIONS`, `CANDIDATE_STATUS_TRANSITIONS`, `VALIDATION_STATUS_TRANSITIONS`,
  `BASELINE_STATUS_TRANSITIONS`.

```python
def can_transition(kind: LifecycleKind, frm: str, to: str) -> bool: ...
def next_states(kind: LifecycleKind, frm: str) -> frozenset[str]: ...
```

Pure and total (unknown state ⇒ `False`, never raises). Slice 4/5's persisted state machine reuses
the existing owned-transition CAS (`services/jobs.py` pattern) but validates the *edge* through this
table — one source for "is this transition legal," testable without a DB.

### Evidence authority matrix (`authority.py`) — design §4.7 made concrete

Domain-specific authority: **no universal source ranking.** A matrix keyed by
`(SourceType, AuthorityDomain) -> AuthorityLevel`:

```python
class AuthorityDomain(StrEnum):
    RUNTIME="runtime"; PRODUCT="product"; LEGAL="legal"; SECURITY="security"
    DATA="data"; ARCHITECTURE="architecture"; OPERATIONS="operations"; COST="cost"; COMPLIANCE="compliance"

class AuthorityLevel(IntEnum):  # ordered for comparison; not a score
    NONE=0; LOW=1; MEDIUM=2; HIGH=3

# examples (illustrative rows; full matrix in the module):
#  repository            -> runtime:HIGH, architecture:HIGH, product:LOW,  legal:NONE
#  communication(legal)  -> legal:HIGH,   compliance:HIGH,   runtime:NONE, product:LOW
#  human_input(intvw)    -> product:HIGH, operations:MEDIUM, security:LOW, legal:NONE
#  test_run/runtime_rec  -> runtime:HIGH, security:MEDIUM,   product:NONE
#  external_reference    -> (domain):MEDIUM (research authority, never HIGH alone)

def authority_of(source_type: SourceType, domain: AuthorityDomain) -> AuthorityLevel:
    # defaults to LOW for unspecified (source_type, domain) pairs — present-but-weak, never silently HIGH
```

This encodes the design's worked examples (a contract has legal authority but none over runtime; a
repo has implementation authority but low authority over business intent). It is **advisory input**
to conflict resolution and requirement compilation later — Slice 0 only defines and tests the matrix.

### C4 canonical serialization & hashing (`serialization.py`)

Deterministic, cross-process, language-independent:

1. **Content projection.** Each entity declares `CONTENT_FIELDS` (the substantive fields), excluding
   surrogate/volatile fields (`id`, `created_at`, `updated_at`, `version`, `status`, and mutable
   annotation fields). `content_hash` covers *what the row asserts*, not its identity or lifecycle.
2. **Canonical form.** Build a plain dict of the projected fields → JSON with: keys sorted
   lexicographically; `separators=(",", ":")` (no insignificant whitespace); strings Unicode-NFC
   normalized; `ensure_ascii=False` over UTF-8 bytes; booleans `true`/`false`; `null` for `None`;
   **arrays preserve order** (order is significant); floats formatted via a fixed policy
   (`format(x, ".6g")`) so `confidence`/`relevance` hash stably across platforms; nested models
   recursed by their own content projection.
3. **Hash.** `content_hash = sha256(canonical_bytes).hexdigest()`.
4. **Set hashes.** `claim_set_hash` (design §5) = `sha256` over the **sorted** list of member claim
   `content_hash`es (sorted ⇒ order-independent set identity). `baseline_hash` (design §14) = hash
   over the baseline's content projection, which references its candidate/requirement/element
   `content_hash`es (a Merkle-style roll-up: the baseline hash changes iff any governed content
   changes).

```python
def canonical_bytes(model: BaseModel) -> bytes: ...
def content_hash(model: BaseModel) -> str: ...
def set_hash(hashes: Iterable[str]) -> str: ...
```

Tests: byte-identical output across two constructions and across dict-key insertion order;
whitespace/number-format stability; a changed content field flips the hash while a changed
`id`/timestamp does not; `set_hash` is permutation-invariant.

### Fixtures (`fixtures/mvp_scenario.json`)

The design's §20 scenario as golden data: one repository source (+version), an uploaded product-notes
document, an architecture diagram, and a legal constraint; observed claims from "repo inspection";
claimed requirements/constraints from the documents; one code-vs-intent conflict; a `current` and an
`intended` genome snapshot stub with a few traits linked to those claims; two foundation-requirement
stubs (one hard legal constraint). These validate cleanly against the contracts and become the seed
inputs Slice 1+ tests replay — so the MVP acceptance scenario is exercised from Slice 1 onward, not
only at the end.

## Alternatives considered

- **Skip Slice 0; declare vocabulary inline in Slice 1's ORM.** Rejected: couples the vocabulary to
  the ORM, forces the API/UI to re-declare it, and delays C1–C4 testability to migration time — the
  most expensive failure point. Slice 0 is cheap insurance.
- **Hand-write JSON Schemas as the source, generate Pydantic.** Rejected: the repo is Pydantic-first
  (`apps/api/app/schemas.py`); generating schemas *from* Pydantic keeps one source and matches house
  tooling. JSON Schema is the derived artifact.
- **Put contracts in `apps/api/app/schemas.py`.** Rejected: that module is API DTOs (request/response);
  these are cross-layer domain contracts (ORM + API + UI + worker all consume them), so they belong
  in the shared core (`packages/aos_core`, RFC-0006), as a leaf with no app imports.
- **Enums as plain constants / `Literal` unions.** Rejected: `StrEnum` gives one iterable, DB-storable,
  JSON-schema-emitting source; `Literal`s scatter the vocabulary across signatures.
- **Ship contracts + Slice 1 tables in one PR.** Rejected: violates "argue before code" (RFC_PROCESS)
  and "one PR = one work package"; Slice 0's value is being *stable and reviewed* before tables bind
  to it.

## Evidence

- `docs/rfc/RFC-0016-Foundation-Intelligence-Evidence-Spine-System-Genome.md` — parent; C1–C5 and the
  slice map this implements (Slice 0 → RFC-0017).
- `docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md` §3–§13, §18–§20 — the vocabularies, lifecycle,
  authority examples, and MVP scenario transcribed into these contracts.
- `packages/aos_core/aos_core/models.py` — the ORM Slice 1 will add; its `AuditMixin`
  (`id/status/version/created_at/updated_at`) is exactly the volatile set C4's content projection
  excludes.
- `apps/api/app/schemas.py` — the existing Pydantic pattern these contracts follow (but live in core,
  not the API layer).
- `services/jobs.py` owned-transition CAS — the enforcement Slice 4/5 reuses; `lifecycle.py` is the
  edge-legality source it will validate against.
- `docs/V0_1_DATA_MODEL.md`, RFC-0006 — precedent for "contract before endpoints" and shared-core
  domain types.

## Security impact

None in this PR. No new surface — no routes, no egress, no persistence, no secrets. The slice is
security-*positive* in intent: it lands the **C3 truth-layer guard** and the **provenance
(`minted_by`) field** as tested pure code before any ingestion path exists, so Slice 1 cannot mint an
`observed`/`decided` claim from the wrong source class. Claim/source `Sensitivity` is defined as an
enum here but **not enforced** — enforcement is RFC-0024 (gated by Security Agent review), unchanged.

## Compliance impact

Governance-positive and self-contained. Encodes the traceability vocabulary (truth layers,
provenance, authority domains) and the reproducible hashing that later slices' audit trail depends
on. No Capability Map layer changes beyond what RFC-0016 already registered (Layer 2 lists Foundation
Intelligence); this RFC is an additional artifact under that entry — **the PR updates
`docs/capability-map/layer-02.md`'s artifact list to add RFC-0017** (pre-empting the
`capability-map-not-updated` Guardian check per LES-040).

## Migration plan

**None.** No `Base.metadata` change, no Alembic revision, single head `0027` untouched. The new
subpackage and generated schemas are additive files; nothing imports `foundation/` yet, so there is
no runtime or import-time impact on the API/worker. Slice 1 (RFC-0018) is the first consumer and
introduces the first migration (`0028+`).

## Risks

- **Vocabulary churn after later slices start.** Mitigation: Slice 0 is deliberately data-only and
  reviewed as *the* vocabulary; changes are additive enum members (backward compatible) and caught by
  the schema-drift test. A breaking change to a shipped enum requires an RFC note.
- **Over-modeling / speculative fields.** Mitigation: fields are exactly the design's blocks — no
  invented structure; `Locator`/`metadata` stay open (JSONB-bound) rather than prematurely typed.
- **C4 float-hash instability across platforms.** Mitigation: fixed `.6g` float policy + a
  cross-construction determinism test; confidence/relevance are the only floats and are bounded [0,1].
- **Authority matrix bikeshedding.** Mitigation: ship the design's worked examples as the seed matrix
  with `LOW` default; it is advisory input, tunable later without a schema change.

## Acceptance criteria (this RFC)

- Operator approves the contract layout, the enum vocabularies, the C3/C4 specs, the authority matrix
  shape, and the "generated JSON Schema from Pydantic" approach.
- Implementation lands as **one work package AOS-FOUND-CONTRACTS-001**, one PR, builder ≠ verifier,
  hermetic (no network/DB/model), delivering: `foundation/` subpackage, generated
  `schemas/foundation/`, the regen script, the MVP fixture, and unit tests that:
  - exhaust `may_mint(MinterClass × TruthLayer)` (C3);
  - prove `content_hash`/`set_hash` determinism + field-projection + permutation-invariance (C4);
  - reject a `decided` claim lacking `derivation.method="approved"`/`decision_ref` (C1) and a
    non-decided claim carrying one;
  - assert `foundation/` imports only stdlib + pydantic (leaf-purity);
  - assert JSON-Schema regeneration is a no-op (drift guard);
  - validate `fixtures/mvp_scenario.json` against the contracts.
- `docs/capability-map/layer-02.md` artifact list updated to include RFC-0017.
- No table, migration, route, LLM call, or UI is added.

## Open questions

1. **`GenomeDimension` closed enum vs open string.** Leaning: dimensions are a **closed** enum (the
   16 A–P are the framework), while `trait_key` within a dimension is **open** string (traits are
   discovered). Confirm no 17th dimension is expected before Slice 2.
2. **Where generated schemas live** — `schemas/foundation/` at repo root vs under the package. Leaning
   repo-root `schemas/` for easy external/UI consumption; confirm no packaging constraint.
3. **`AuthorityLevel` as `IntEnum` (comparable) vs opaque enum.** Leaning `IntEnum` so
   conflict/authority logic can compare levels; it is an ordering, explicitly **not** a numeric score
   (avoids the LES-023 "raw number surfaced as confidence" trap).
4. **Float hashing policy** — `.6g` vs integer-scaled fixed point. Leaning `.6g`; revisit only if a
   determinism test flakes across CI arch.

## Dependencies

- **Blocks on:** RFC-0016 (accepted, merged) — this is its Slice 0.
- **Reuses:** the Pydantic-first pattern (`apps/api/app/schemas.py`), shared-core placement (RFC-0006),
  Python `StrEnum`/`IntEnum` (stdlib, Python 3.12 per CI).
- **Enables:** RFC-0018 (Evidence Spine — imports `foundation/` for column enums, the C3 guard, and
  the C4 hasher), and every later slice's schema/DTO/UI vocabulary. RFC-0024 will enforce the
  `Sensitivity` enum defined here.

## Final Judge verdict

Pending operator approval. The cheapest, most reversible, highest-leverage slice: pure contracts and
pure functions, no persistence or runtime, hermetic — and it lands C1–C4 as tested code before any
row can violate them, which is exactly where RFC-0016 said the integrity risk lives. Recommend
acceptance and delivery as AOS-FOUND-CONTRACTS-001 (one PR), with RFC-0018 (Evidence Spine) to follow
as the first consumer.
