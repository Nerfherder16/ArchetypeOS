# RFC-0018 — Foundation Intelligence Slice 1: Evidence Spine

## Status

Proposed (2026-07-12). Second child RFC under **RFC-0016**, first consumer of **RFC-0017**'s
`aos_core.foundation` contracts. Delivers the design's **Slice 1** (`docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md`
§4–§5, §18): the claim-centric evidence graph as first-class, queryable, versioned tables, with
RFC-0016's C1/C3/C4/C5 reconciliations moved from pure functions (Slice 0) into the persistence
layer. This is **the load-bearing slice** — every later slice (genome, requirements, candidates,
baseline) reads claims.

## Summary

Adds the **evidence domain** to the ORM (`packages/aos_core/aos_core/models.py`) and one Alembic
migration (**0028**, additive; head is `0027`): `evidence_sources`, `evidence_source_versions`,
`evidence_fragments`, `claims`, `claim_evidence_links`, `claim_relationships`, `evidence_conflicts`,
`corpus_snapshots`, `corpus_snapshot_sources`, `open_questions`. Columns store the RFC-0017 enum
values (as strings); a service layer (`services/evidence.py`) is the **only** write path and it
enforces the reconciliations:

- **C3** — `create_claim` derives `minted_by` server-side from the creator class and calls
  `foundation.truth.may_mint`; an `agent` can never persist an `observed` claim, only the
  deterministic tier can. (The client never sets `truth_layer` freely for `observed`.)
- **C4** — every immutable evidence row gets a `content_hash` computed via
  `foundation.serialization.content_hash` at insert; a service guard refuses UPDATEs to content
  fields (corrections create a new `evidence_source_versions` row). `corpus_snapshots.claim_set_hash`
  uses `set_hash`.
- **C1** — a `truth_layer="decided"` claim carries a `decision_id` FK to `decisions` and is created
  **only** by projecting an approved `Decision`; no route mints a decided claim directly.
- **C5** — `services/evidence_backfill.py` projects existing `evidence`/`confidence` JSON on
  `RepositoryDNA`, `Decision`, `Recommendation`, `Evaluation`, `Risk`, `ResearchRun` into read-only
  `Claim`/`Fragment` views, so the spine reflects current data on day one (delivered in its own
  follow-up package, AOS-EVIDENCE-BACKFILL-001).

Delivered as three sequential work packages (each its own PR after this RFC): **AOS-EVIDENCE-MODELS-001**
(tables + migration + write service + guards + hermetic tests — bundled with this RFC),
**AOS-EVIDENCE-API-001** (read/write routes + API tests), **AOS-EVIDENCE-BACKFILL-001** (C5 adapter).
The provenance UI is a later package (AOS-EVIDENCE-UI-001), out of this RFC's core.

## Problem

RFC-0017 gave us the *shapes*; nothing persists them. Evidence remains denormalized JSON on ~12
tables (`models.py`), so "what supports this claim / what opposes it / which source, version, line /
is it observed or asserted" are unanswerable. The Genome (Slice 2) has nothing to read. This slice
turns the contracts into rows.

## Goals

- The 10 evidence tables as normalized, queryable ORM models, columns typed to the RFC-0017 enums,
  each `AuditMixin`-based (id/status/version/timestamps) — the design §15 "normalized relational,
  JSONB only for locators/metadata" guidance.
- C1/C3/C4 enforced **in the write path** (`services/evidence.py`), with regression tests — the
  reconciliations are code + tests, not prose.
- Immutability is real: `content_hash` columns + a no-content-UPDATE service guard + tests.
- Hermetic: models create under sqlite `create_all` (reuse the `GUID`/`JSONField` patterns already in
  `models.py`); the write service runs offline; no LLM.
- Single Alembic head preserved; `alembic upgrade head` clean on fresh Postgres (compose-smoke).

## Non-goals

- **No genome/foundation/requirement logic** (Slices 2+).
- **No extraction/LLM.** Claims are created by deterministic tools, humans, or the approval path — no
  agent extraction pipeline here (that is a later slice); this slice provides the *substrate* and the
  guards, seeded by the §20 fixture + backfill.
- **No compartmentalization enforcement.** `sensitivity` columns are stored (reusing
  `aos_core.sensitivity.Sensitivity`) but claim-level ACLs are RFC-0024.
- **No UI** in the core packages (provenance UI is AOS-EVIDENCE-UI-001, follow-up).
- **No new authority model.** Write routes (AOS-EVIDENCE-API-001) reuse the existing envelope.

## Design

### Tables (ORM in `models.py`, mirroring the RFC-0017 contracts)

All `AuditMixin` (id/status/version/created_at/updated_at/created_by/updated_by/meta). Enum-valued
columns store `String` values from `aos_core.foundation.enums`. JSON only where the contract is open
(`locator`, `scope`, `derivation`, `metadata`).

- **EvidenceSource** — project_id FK; source_type, origin, originator, canonical_uri, sensitivity
  (`aos_core.sensitivity`), authority_domains (JSON list), access_policy_id, title. `content_hash`.
- **EvidenceSourceVersion** — source_id FK; version_ref, content_hash (of the source content),
  captured_at, effective_from/until, supersedes_version_id (self-FK), ingestion_method,
  parser_version. **Append-only** (corrections → new row).
- **EvidenceFragment** — source_version_id FK; locator (JSON), content_hash, excerpt,
  extraction_method, extraction_confidence (Float). Append-only.
- **Claim** — project_id FK; statement, claim_type, truth_layer, domain, scope (JSON), polarity,
  confidence (Float), materiality, valid_from/until, created_by, derivation (JSON: method +
  parent_claim_ids), **minted_by** (String), **decision_id** (FK→decisions, nullable, C1),
  `content_hash`. Status via AuditMixin (active/disputed/superseded/rejected/resolved).
- **ClaimEvidenceLink** — claim_id FK, fragment_id FK, relationship, relevance (Float), strength,
  notes. (junction, no content_hash needed.)
- **ClaimRelationship** — from_claim_id FK, to_claim_id FK, relationship, notes.
- **EvidenceConflict** — project_id FK; claim_ids (JSON list of 2+), conflict_type, materiality,
  status (open/accepted_exception/resolved/superseded), resolution, resolution_decision_id (FK
  nullable), blocking_stages (JSON list).
- **CorpusSnapshot** — project_id FK; source_version_ids (JSON list), repository_refs (JSON list),
  **claim_set_hash** (via `set_hash` over member claim content_hashes), purpose, created_by. Immutable.
- **CorpusSnapshotSource** — snapshot_id FK, source_version_id FK (normalized many-to-many so a
  snapshot's membership is queryable, not only JSON).
- **OpenQuestion** — project_id FK, genome_snapshot_id (nullable, Slice 2 wires it), question,
  affected_dimensions (JSON), affected_foundation_domains (JSON), materiality, reason, answer_type,
  status, answer_claim_id (FK nullable).

Indexes on the hot FKs (project_id, source_id, source_version_id, claim_id, from/to_claim_id) and on
`claims(project_id, truth_layer)` (the Genome's read pattern).

### `services/evidence.py` — the only write path (guards live here)

```python
def create_source(db, *, project_id, minted_by: MinterClass, **fields) -> EvidenceSource
def add_source_version(db, *, source_id, **fields) -> EvidenceSourceVersion   # append-only
def add_fragment(db, *, source_version_id, **fields) -> EvidenceFragment       # append-only
def create_claim(db, *, project_id, minted_by: MinterClass, truth_layer, ..., decision_id=None) -> Claim
def link_evidence(db, *, claim_id, fragment_id, relationship, ...) -> ClaimEvidenceLink
def relate_claims(db, *, from_claim_id, to_claim_id, relationship, ...) -> ClaimRelationship
def open_conflict(db, *, project_id, claim_ids, conflict_type, ...) -> EvidenceConflict
def freeze_corpus(db, *, project_id, source_version_ids, purpose) -> CorpusSnapshot
def project_decided_claim(db, *, decision_id) -> Claim   # C1: the ONLY decided-claim minter
```

Guards (each with a regression test):
- **C3:** `create_claim` calls `may_mint(minted_by, truth_layer)`; raises `ValueError`→HTTP 422 on
  violation. `minted_by` is passed by the caller's *class* (a deterministic tool caller vs an agent
  caller), never chosen by an external client to smuggle `observed`.
- **C1:** `create_claim(truth_layer="decided")` from a general caller is refused; the only path to a
  decided claim is `project_decided_claim`, which loads an **approved** `Decision` (else 409, mirroring
  `approve_decision`), sets `decision_id`, `derivation.method="approved"`, `minted_by=approval_process`.
- **C4:** on insert, `content_hash = foundation.content_hash(<contract projection of the row>)`; an
  `assert_immutable` guard rejects content-field UPDATEs on Source/SourceVersion/Fragment/Claim-body/
  CorpusSnapshot (status/annotation transitions still allowed via explicit status methods). `freeze_corpus`
  computes `claim_set_hash` via `set_hash`.

The service builds the RFC-0017 Pydantic contract for each row and reuses its validators (so C1/C3
are enforced at *both* the contract layer and the DB write — defense in depth) then persists the ORM row.

### Migration 0028

Additive `create_table` for the 10 tables, `down_revision = "0027"`, `import aos_core.models`,
FKs + indexes as above. Validated by the no-drift autogenerate probe + compose-smoke `alembic upgrade
head` on fresh Postgres. sqlite `create_all` stays green (GUID/JSONField dialect-variants already
handle this per RFC-0010).

### Tests (hermetic, `apps/api/tests/test_evidence_*.py`)

C3 (agent cannot persist observed; deterministic tool can); C1 (no direct decided claim; project from
approved Decision works; from non-approved 409); C4 (content_hash set on insert, stable, content UPDATE
refused, corpus claim_set_hash permutation-invariant); relationships/links persist and query; conflict
stays visible until resolved; `freeze_corpus` snapshot is immutable and references its versions;
the §20 fixture (`foundation/fixtures/mvp_scenario.json`) loads through `services/evidence.py` and
produces the expected rows (this replays the MVP acceptance seed).

## Alternatives considered

- **One giant PR (models+API+backfill+UI).** Rejected — unreviewable; the sequential packages keep
  each PR scoped and let the models/guards land and be trusted before the API/backfill build on them.
- **Store the graph as JSON on a single `evidence_graph` row.** Rejected — defeats the whole slice
  (no support/opposition queries, no dedup, no per-claim versioning); design §15 forbids it.
- **Enforce C1/C3 only at the API layer.** Rejected — the service is the reused write path (worker,
  backfill, future extraction all call it); guards must live in the service, tested independently of
  routes. The contract-layer validators add defense-in-depth.
- **A separate `evidence` table for JSON evidence (no migration of existing).** Rejected — C5 backfill
  projects existing evidence into the same claim model so there is one source of truth, not two.

## Evidence

- RFC-0016 (C1–C5, slice map) and RFC-0017 (`aos_core.foundation` — the enums/contracts/guards this
  imports; `content_hash`/`set_hash`/`may_mint` are already tested).
- `packages/aos_core/aos_core/models.py` — `AuditMixin`, `GUID`, `JSONField` patterns the new models
  reuse; the ~12 JSON `evidence` columns C5 backfills from.
- `services/decisions.py` (`approve_decision`, 409 on non-approved) — the pattern `project_decided_claim`
  mirrors for C1.
- `services/authority_envelope.py` — reused by the write routes (AOS-EVIDENCE-API-001).
- `apps/api/alembic/versions/0027_implementation_plans.py` — current head; 0028 chains from it.
- `aos_core/sensitivity.py` — the reused `Sensitivity` for source/claim sensitivity columns.

## Security impact

No new external surface in this package (service + models + migration; routes are the next package,
and reuse the envelope). Security-positive: C3 makes truth-layer laundering impossible at the DB
boundary, C4 makes evidence tamper-evident (content hash) and append-only. `sensitivity` is stored but
not enforced (RFC-0024). No secrets, no egress.

## Compliance impact

Strongly positive: this is the auditable, immutable, hash-anchored evidence substrate the whole
capability's traceability depends on. `docs/capability-map/layer-02.md` artifact list gains RFC-0018
(pre-empting the Guardian check per LES-040).

## Migration plan

One additive migration `0028_evidence_spine`, `down_revision="0027"`, single head preserved,
`import aos_core.models`, no-drift + compose-smoke validated. No data migration in this package;
C5 backfill (its own package) is idempotent and re-runnable, projecting existing JSON into claim views
without mutating the source rows.

## Risks

- **C4 immutability holes** (a content UPDATE slipping through). Mitigation: the `assert_immutable`
  guard + a test that attempts a content mutation and asserts it is refused; content_hash recomputed
  and compared in a test.
- **C1 leak** (a decided claim minted off-path). Mitigation: `create_claim` rejects `truth_layer=decided`
  outright; only `project_decided_claim` sets it; test both.
- **Migration drift / multi-head.** Mitigation: single `down_revision="0027"`, no-drift autogenerate
  probe, compose-smoke upgrade.
- **Over-broad models.** Mitigation: columns are exactly the RFC-0017 contracts; JSON only for
  locator/scope/derivation/metadata.
- **Sonnet builder touching the shared `models.py`/migrations.** Mitigation: Opus verifies the
  migration + guards line-by-line and re-runs the full evidence test suite (builder ≠ verifier).

## Acceptance criteria (this RFC + the bundled AOS-EVIDENCE-MODELS-001)

- Operator approves the 10-table shape, the service-as-only-write-path with C1/C3/C4 guards, and the
  sequential-package split.
- AOS-EVIDENCE-MODELS-001 lands: 10 ORM models + migration 0028 (single head) + `services/evidence.py`
  with the guards + hermetic `test_evidence_*` proving C1/C3/C4 and the §20 fixture load. Builder ≠
  verifier; ruff + full-suite green in CI.
- `docs/capability-map/layer-02.md` updated with RFC-0018.
- No genome/foundation logic, no LLM, no UI, no compartmentalization enforcement in this package.
- AOS-EVIDENCE-API-001 and AOS-EVIDENCE-BACKFILL-001 follow as their own PRs.

## Open questions

1. **`content_hash` as a stored column vs computed-on-read.** Leaning stored (set at insert, indexed
   for dedup, immutable) — confirm at build time it round-trips against `foundation.content_hash`.
2. **Do we normalize `claim_evidence_links`/`claim_relationships` with a surrogate id or a composite
   PK?** Leaning surrogate id + a unique constraint on (claim_id, fragment_id, relationship). Resolve
   in AOS-EVIDENCE-MODELS-001.
3. **Backfill provenance:** projected claims get `minted_by=deterministic_tool` (they come from a
   deterministic scan of existing rows) and `truth_layer` per source (DNA scan → observed; a Decision →
   decided via C1; a Recommendation/Research finding → inferred/claimed). Confirm the mapping in
   AOS-EVIDENCE-BACKFILL-001.

## Dependencies

- **Blocks on:** RFC-0016 (accepted), RFC-0017 (merged, #210) — imports `aos_core.foundation`.
- **Reuses:** `models.py` AuditMixin/GUID/JSONField; `services/decisions.py` (C1 pattern);
  `authority_envelope.py` (write routes); `aos_core.sensitivity`.
- **Enables:** Slice 2 (Genome reads claims), Slice 3–5, and the design §20 MVP steps 1–8.

## Final Judge verdict

Pending operator approval. The keystone slice: it makes evidence first-class and moves C1/C3/C4 from
tested pure functions into the enforced write path, with C5 bridging existing data so nothing forks.
Scoped into three reviewable packages; the models+guards land first and are trusted before the API and
backfill build on them. Recommend acceptance; start AOS-EVIDENCE-MODELS-001 (bundled here).

## Implementation Status

Tracks the packages that realize this RFC (updated as each lands):

- **AOS-EVIDENCE-MODELS-001** (PR #211, merged) — the 10 evidence ORM models, migration `0028`, and
  `services/evidence.py` as the guarded write path (C1 `project_decided_claim`, C3 `may_mint`, C4
  `content_hash` + `before_update` immutability guard + permutation-invariant `claim_set_hash`).
- **AOS-EVIDENCE-API-001** (this PR) — the HTTP surface in `apps/api/app/routes/evidence.py` (thin
  wrappers over the guarded service), design §16:
  - `POST/GET /projects/{id}/sources`, `POST/GET /sources/{id}/versions`,
    `POST /source-versions/{id}/fragments`
  - `POST/GET /projects/{id}/claims` (`?truth_layer=` filter), `GET /claims/{id}` (with links +
    relationships), `POST /claims/{id}/evidence`, `POST /claims/{id}/relationships`
  - `POST/GET /projects/{id}/conflicts`, `PATCH /conflicts/{id}` (resolve)
  - `POST/GET /projects/{id}/corpus-snapshots`, `POST /decisions/{id}/project-claim` (C1)
  - Guard→HTTP mapping: service `ValueError` (C3) → 422; the public claims route rejects
    `minted_by=deterministic_tool`; `project_decided_claim` 404/409 (C1) propagate. No authority
    envelope (evidence ingestion is additive/advisory).
- **AOS-EVIDENCE-BACKFILL-001** (this PR) — the C5 adapter `services/evidence_backfill.py`:
  projects existing `RepositoryDNA` / `Decision` / `Recommendation` / `Evaluation` / `Risk` /
  `ResearchRun` rows into the claim model through the guarded `services/evidence.py` write path,
  plus `POST /projects/{id}/evidence-backfill`. Truth-layer mapping respects C3 (backfill mints as
  `deterministic_tool`, so only `observed`/`inferred`): DNA scan facts + Evaluation scores →
  `observed`; recommendations/research/risk/eval-findings/non-approved-decisions → `inferred`;
  **approved** decisions → `decided` via `project_decided_claim` (C1, `approval_process`).
  Idempotent + re-runnable (sources deduped by a `backfill://<kind>/<id>` canonical URI; claims by
  predicting the service's content hash) — a second run creates zero rows. With this, **Slice 1
  (Evidence Spine) is complete**: design §20 steps 1–8 are demonstrable.
- **AOS-EVIDENCE-UI-001** (queued) — the provenance UI.
