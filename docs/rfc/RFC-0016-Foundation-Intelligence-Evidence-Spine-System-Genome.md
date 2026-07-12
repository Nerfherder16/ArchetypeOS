# RFC-0016 — Foundation Intelligence: Evidence Spine, System Genome & Foundation-Selection Lifecycle

## Status

Proposed (2026-07-12). This is the **governing capability RFC** for the operator-supplied
conceptual design filed at `docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md` (the "source of
record"), adjudicated by the senior review at
`knowledge/wiki/reviews/2026-07-12-foundation-intelligence-design-review.md`. It **accepts
the capability and rejects it as a single unit of work**: it promotes the design's §19
principles to architectural decisions, adds five load-bearing reconciliations the design
leaves open (C1–C5), fixes the mature-state target, and carves the work into slice-scoped
child RFCs. It defines **no table schemas** — each Evidence/Genome/Foundation slice is its
own data-model RFC beneath this one. Nothing here changes the schema; this RFC is the gate
those RFCs pass through.

## Summary

ArchetypeOS's evidence and confidence are **not first-class**. `evidence` is a
`JSONField()` list column repeated on ~12 tables (`packages/aos_core/aos_core/models.py:111,
165, 180, 194, 223, 350, 544-545, 558, 573, 586`) and `confidence` is a scalar `Float`
duplicated on ~10. There is no `Claim`, no evidence link, no conflict entity, no genome, no
foundation, no corpus snapshot in code (grep-confirmed). The platform can therefore state a
recommendation but cannot render the **traceable chain from source → claim → trait →
requirement → candidate → validation → approval** that the Constitution demands and that
the design's §21 names as the whole point.

This RFC introduces **Foundation Intelligence**: a claim-centric *evidence spine*, a
multi-dimensional *System Genome*, and a governed *foundation-selection state machine*,
delivered as **seven governed, individually-shippable slices (0–6)** that reuse the existing
substrate — the durable job queue (RFC-0014), the `Provider` seam and deterministic-in-CI
stance (RFC-0005), the enforced Authority envelope (`services/authority_envelope.py`), the
deterministic scanner (`repository_scanner.py`), the rule-based Final Judge
(`council.py:synthesize_verdict`), and the decision→plan loop (RFC-0015). The governing
constraints are unchanged: **claim-centric, truth-layer-separated, evidence-immutable,
conflicts-visible, hard-constraints-before-scores, uncertainty-becomes-validation, and
human approval before any baseline.** No new runtime service is introduced for Slices 0–1;
this is a data-model + service-layer capability, not a new process.

The end state is one traceable spine:

```
Source → SourceVersion → Fragment → Claim (observed|claimed|inferred|decided)
→ [conflicts kept visible] → CorpusSnapshot (frozen)
→ GenomeTrait → GenomeSnapshot (current|intended|target)
→ FoundationRequirement (hard constraint | quality | preference)
→ FoundationCandidate + FoundationElement → deterministic eligibility
→ typed Council challenge → ValidationTask → Final Judge dossier
→ human approval → immutable FoundationBaseline
→ derived Decisions + ImplementationPlans (RFC-0015) → PR Guardian drift checks
```

## Problem

Verified against `main` (file-anchored):

- **Evidence is denormalized, not linkable.** `evidence`/`confidence` live as JSON/scalar
  columns on domain rows (`models.py`, above). There is no way to ask "what supports this?",
  "what opposes it?", "which source, which version, which line?", or "is this observed or
  merely asserted?". The design's claim graph does not exist.
- **The Knowledge Graph is doc-only.** `ENGINE_CATALOG.md` promises "Knowledge Graph stores
  relationships between … decisions, repositories, … risks, and research," but there is **no
  implementation** (recon-confirmed). The design's §14 assumes an engine that was never built.
- **Council findings are string-flattened.** The council selectors genuinely produce typed
  evidence items `{kind, detail, ref}` (`services/council.py:59, 82, 90, 143, 167-192`), but
  the agent contract asks for and stores **"findings (array of strings), evidence (array of
  strings)"** (`council.py:264-267`), persisted as untyped `JSONField()` arrays on
  `CouncilAgentOutput` (`models.py:624-642`). The `{kind, detail, ref}` structure is
  discarded before storage. Foundation adjudication needs the type/ref back.
- **Conflicts & open questions are second-class.** They exist only as JSON list columns on
  `ResearchRun` (`models.py:291-292`) — never linkable to two specific claims, never a
  reviewable inbox, never a foundation blocker.
- **Nothing is immutable.** `AuditMixin` carries a *mutable* `version` int + `updated_at`;
  no append-only guarantee, no content hash, no corpus freeze. "Evidence is immutable"
  (design §19.6) has no enforcement primitive today.
- **DNA is repo-scoped; the system is not.** `RepositoryDNA` (`models.py:97`) describes one
  repository's code. No entity describes the *engineered system* across repositories,
  hardware, human workflow, vendor, and legal constraints — the design's central boundary.

## Goals

- A claim-centric **Evidence Spine** where every material statement is a `Claim` with a
  truth layer, linked to a `Fragment` of a versioned `Source`, with support/opposition
  links and visible conflicts — the queryable substrate the whole capability stands on.
- A **System Genome** of evidence-backed traits across the design's dimensions, in separate
  `current` / `intended` / `target` snapshots, with coverage- and confidence-honest quality
  indicators (never an over-confident genome over weak evidence — LES-023).
- A **persisted foundation-selection state machine** in which hard constraints are evaluated
  before weighted scores, uncertainty produces `ValidationTask`s rather than invented
  certainty, and the selected foundation becomes an **immutable, human-approved, versioned
  `FoundationBaseline`** from which Decisions and plans (RFC-0015) derive.
- **Reuse, not shadow:** the capability *connects* `RepositoryDNA`, `Decision`,
  `Recommendation`, `Evaluation`, `ResearchRun`, the Council, and Build Intelligence — it
  does not duplicate them (C1–C2 below).
- Hermetic in CI: the deterministic tier drives extraction and classification offline;
  agent/LLM extraction attaches behind the `Provider` seam on an authed node.

## Non-goals

- **No schemas in this RFC.** Every table is defined in its slice's child RFC. This document
  fixes boundaries and invariants only.
- **No new authority model.** Selection/approval/exception/baseline writes reuse
  `services/authority.py` (`ActionClass`) + `services/authority_envelope.py`, already
  enforced at `enqueue_job` (`services/jobs.py`).
- **No new job-durability work.** Extraction/genome/candidate jobs declare an idempotency
  strategy and inherit RFC-0014's outbox/leases.
- **No autonomous action.** Every state transition that writes is advisory/draft by default;
  baseline approval is a mandatory human gate (design §13, Constitution IX/XIX).
- **No agent-minted `observed` claims** (see C3) and **no automatic baseline rewrite** —
  drift *proposes* a review; a human reopens selection (design Stage 16).
- **Not the whole design at once.** Slices 2–6 are deferred to their own RFCs; only the
  overarching decisions (this RFC) and Slice 0/Slice 1 boundaries are in immediate scope.

## Design

### Mature-state target (per the "design to mature-state" roadmap rule)

The mature state is the traceable spine in the Summary, persisted as **normalized relational
entities** (identity, status, versioning, relationships, provenance, approval, queryable
dimensions, lifecycle transitions) with **JSONB reserved** for extensible locators,
domain-specific scoring detail, typed agent payloads, and element configuration — exactly
the design's §15 guidance, and consistent with `V0_1_DATA_MODEL.md`'s "normalize
many-to-many evidence links after v0.1." Every slice below is a strict **subset** of this
target: a permanent layer later slices extend, never scaffolding torn out. No genome is
stored as one JSON blob; traits and claim links stay independently queryable and versioned.

### The §19 principles, promoted to architectural decisions (AD-1 … AD-15)

The design's §19 list is **adopted verbatim as binding architecture decisions** for this
capability (AD-1 claim-centric; AD-2 four separate truth layers; AD-3 separate current/
intended/target snapshots; AD-4 DNA is evidence *feeding* the Genome, not the Genome; AD-5
authority/confidence/relevance/freshness independent; AD-6 evidence immutable + versioned;
AD-7 conflicts visible until resolved; AD-8 hard constraints before weighted scores; AD-9
scores never replace human judgment; AD-10 uncertainty → validation; AD-11 lifecycle is a
persisted state machine; AD-12 approval → immutable versioned baseline; AD-13 sensitive
evidence compartmentalized; AD-14 every foundation element traces to claims/requirements/
verification; AD-15 plans derive from approved foundations, not raw prompts). These are not
re-litigated per slice — they are the acceptance frame every slice is checked against.

### The five reconciliations the design leaves open — LOCKED here (C1–C5)

These are the decisions §19 omits. Each is a two-sources-of-truth hazard — the exact drift
class LES-L09 was written about — and each is **binding on Slice 1**.

- **C1 — `Claim(truth_layer="decided")` is a projection of `Decision`, never a second home.**
  A decided claim MUST carry `derivation.method="approved"` and reference the governing
  `Decision.id`; it is created/updated only by the existing approval path
  (`services/decisions.py`). Approval state lives in `Decision`; the claim mirrors, it does
  not own. No endpoint may mint a `decided` claim directly.
- **C2 — Foundation entities reuse existing models where they already fit; new tables require
  an explicit reuse-vs-new decision in the slice RFC.** Default reuse targets:
  `FoundationCandidate` links to (does not replace) `Recommendation`; `CandidateScore`
  reuses `Evaluation(evaluation_type="foundation_score")` unless the score-vector shape
  proves it can't; `ValidationResult` becomes `Benchmark`/`Experiment`/`Evaluation` rows
  where those fit. Any net-new table must name, in its RFC, the existing model it was
  measured against and why reuse failed — "fitness over familiarity," applied to our own
  schema.
- **C3 — The `observed` truth-layer is deterministic-only; enforced in code + regression
  test.** Only the deterministic tier (repository scanner, lockfile/manifest parsers, test
  runners, authenticated runtime records) may mint `truth_layer="observed"`. Agents/LLMs may
  mint only `claimed` or `inferred`; `decided` flows only through C1. This invariant has a
  **named enforcement point** (a `create_claim` guard keyed on `created_by` provenance
  class) and a regression test, mirroring the deterministic-floor discipline the platform
  already enforces elsewhere. **This is the single most important control in the capability**
  — without it, truth layers collapse and the chain is worthless.
- **C4 — Immutability is a mechanism, not a label.** Evidence rows (`Source`, `SourceVersion`,
  `Fragment`, `Claim` bodies) and `CorpusSnapshot`/`FoundationBaseline` are append-only:
  every immutable row carries a `content_hash` over a **canonical, deterministic
  serialization** (spec defined in Slice 0), a service-layer no-UPDATE guard, and a DB
  constraint where practical. Corrections create a new version linked by
  `supersedes_version_id`; `claim_set_hash`/`baseline_hash` are reproducible from the
  canonical serialization or they are not trusted.
- **C5 — Existing JSON evidence is bridged, not stranded.** Slice 1 ships an adapter that can
  project existing `evidence`/`confidence` JSON on `RepositoryDNA`, `Decision`,
  `Recommendation`, `Evaluation`, `Risk`, `ResearchRun` into read-only `Claim`/`Fragment`
  views (lazily or via backfill), so the spine reflects reality on day one and the two
  models cannot diverge. The Evidence Graph **is** the long-promised Knowledge Graph made
  real (resolves the design §14 assumption); `ENGINE_CATALOG.md` is updated to say so.

### Slice → child-RFC map (each slice is one child RFC + its own work packages/PRs)

| Slice | Child RFC | Scope (design ref) | Adds tables? | Gate |
|---|---|---|---|---|
| **0 — Vocabulary & Contracts** | RFC-0017 | Canonical enums, JSON Schemas, Pydantic schemas, lifecycle transition table, authority-domain rules, **C4 canonical-serialization spec**, fixtures (§18 Slice 0) | No | No UI, no LLM; contracts only |
| **1 — Evidence Spine** | RFC-0018 | Sources, source versions, fragments, claims, claim-evidence links, claim relationships, conflicts, corpus snapshots, read APIs, provenance UI, **C1/C3/C4/C5** (§4–§5, §18 Slice 1) | Yes (evidence domain) | The prerequisite for everything else |
| **2 — System Genome MVP** | RFC-0019 | Genome snapshots, traits, current/intended separation, DNA ingestion, deterministic + manual traits, coverage/confidence, open questions, comparison (§6–§7) | Yes (genome domain) | Deterministic rules + human review before agent classification |
| **3 — Requirements & Candidates** | RFC-0020 | Requirement compilation, hard constraints, candidates, elements, manual creation, candidate-generation job, score vectors, **C2** (§8–§10) | Some (C2-gated) | Hard constraints have source claims + verification methods |
| **4 — Council & Validation** | RFC-0021 | **Typed** specialist reviews, objection tracking, validation tasks, eligibility, Final Judge dossier, human selection (§10–§13) | Some | Blocking objections resolved / accepted / converted to validation |
| **5 — Foundation Baseline** | RFC-0022 | Immutable baseline, Decision + build-plan linkage (RFC-0015), review triggers, comparison, drift events (§14–§15) | Yes (baseline domain) | Baseline immutable; human approval mandatory |
| **6 — Continuous Evolution** | RFC-0023 | New-evidence impact, staleness, genome deltas, baseline-review recommendations, PR Guardian baseline checks (§16) | Some | Drift proposes review; never auto-rewrites |

**Independent quick win (parallelizable, not blocked on the spine):** `AOS-COUNCIL-TYPED-001`
— restore `{kind, detail, ref}` typed payloads through `CouncilAgentOutput` by widening the
agent contract (`council.py:264-267`) and the stored shape (`models.py:635-637`) from string
arrays to typed objects, keeping backward-compatible reads. This is the design's §11 critique,
lands on a confirmed seam, and delivers value before Slice 4 needs it. It is its own work
package + PR under this RFC.

### Routed delivery plan (model routing per CLAUDE.md)

Opus orchestrates, decides the reconciliations, and adversarially reviews; mechanical build
routes to the cheapest tier that clears the bar; builder ≠ verifier. Concurrency: each slice
runs in its own worktree/branch; slices are file-disjoint from the current AOS-REVIEW-002
runtime-integrity wave (this is BRAIN/data-model work).

| Package | Slice | Blocked by | Build tier | Verify tier | Effort |
|---|---|---|---|---|---|
| RFC-0017 contracts + fixtures | 0 | this RFC accepted | Sonnet (schemas/enums) + deterministic scaffolds | Opus review + schema tests | S–M |
| RFC-0018 Evidence Spine | 1 | RFC-0017 | Opus designs C1/C3/C4/C5 guards; Sonnet builds tables/APIs/UI | Opus (integrity-critical) + hermetic tests | L (3–5 PRs) |
| AOS-COUNCIL-TYPED-001 | — | none (ready) | Sonnet | Opus + council tests | S–M |
| RFC-0019 Genome MVP | 2 | Slice 1 | Sonnet (deterministic traits) | Opus + coverage-calibration test (LES-023) | L |
| RFC-0020 Requirements/Candidates | 3 | Slice 2 | Opus designs C2; Sonnet builds | Opus + eligibility tests | L |
| RFC-0021 Council & Validation | 4 | Slice 3 + COUNCIL-TYPED | Sonnet | Opus (adjudication-critical) | L |
| RFC-0022 Baseline | 5 | Slice 4 | Sonnet | Opus + immutability tests (C4) | M–L |
| RFC-0023 Evolution | 6 | Slice 5 | Sonnet | Opus | M |

**Sequencing.** On acceptance: RFC-0017 (Slice 0) starts immediately and
`AOS-COUNCIL-TYPED-001` runs in parallel (disjoint files). Slice 1 begins once Slice 0's
contracts land — it is the load-bearing slice and where C1–C5 become code. Slices 2–6 are
strictly sequential supersets, each its own RFC argued before it is coded (RFC_PROCESS).
Each package = one work spec + one PR (roadmap non-negotiable).

## Alternatives considered

- **Build the design as specified, monolithically.** Rejected: ~30 tables across three
  domains + a 22-state machine + six UI surfaces in one unit violates "one PR = one work
  package" and "no scope expansion without an RFC," and commits ~30 Alembic migrations with
  C1–C5 unresolved — schema thrash guaranteed.
- **Keep evidence as richer JSON; skip the entity model.** Rejected: the entire value is
  *queryable, linkable, versioned* claims and conflicts. Richer JSON re-creates today's
  dead-end (no support/opposition queries, no cross-source dedup, no provenance chain).
- **Slice 0 → Evidence Spine first, as a child-RFC series (chosen).** Front-loads the cheap
  high-leverage contract work, forces C1–C5 before any expensive building, yields an
  independent early win (typed council payloads), and keeps every slice independently
  valuable and reversible. Matches how v0.1 bootstrapped (data-model doc before endpoints).
- **Reuse `RepositoryDNA` as the Genome.** Rejected: violates AD-4 — DNA is one repository's
  code; the Genome is the engineered system across repositories, hardware, humans, vendors,
  and legal constraints. DNA *feeds* traits; it is not the Genome.

## Evidence

- `packages/aos_core/aos_core/models.py:111,165,180,194,223,350,544-545,558,573,586` —
  `evidence` as repeated `JSONField()` columns; `confidence` as scalar `Float` — the
  denormalization this capability replaces.
- `models.py:624-642` (`CouncilAgentOutput` untyped `findings/evidence/concerns`) +
  `services/council.py:59,82,90,143,167-192` (selectors *produce* `{kind, detail, ref}`) +
  `council.py:264-267` (contract flattens to string arrays) — the §11 typed-payload seam.
- `models.py:291-292` (`ResearchRun.conflicts/open_questions` as JSON) — the second-class
  conflict/open-question precedent this promotes to entities (C-consistent superset).
- `services/authority.py` (`ActionClass`, `requires_approval`) + `authority_envelope.py`
  (`request_action`/`authorize_action`/`consume_action`) enforced at `services/jobs.py`
  `enqueue_job` — the reused approval rail (AD-13, baseline gate).
- `services/decisions.py` (draft→approved/rejected, `needs_evidence` 409) — the approval path
  C1 projects from; the `needs_evidence` abstention gate is the model for hard-constraint
  blocking.
- `services/council.py:synthesize_verdict` (rule-based Final Judge, `ABSTAIN_CONFIDENCE`,
  unsupported-claims detection) — the adjudicator the Stage-13 dossier extends.
- `repository_scanner.py:scan_repository` (read-only, deterministic) — the sole legitimate
  minter of `observed` claims (C3).
- Current Alembic head `apps/api/alembic/versions/0027_implementation_plans.py` — new slices
  start at `0028`, additive, single head preserved.
- `ENGINE_CATALOG.md` "Knowledge Graph" (doc-only, no implementation) — the assumption C5
  resolves by making the Evidence Graph the real Knowledge Graph.
- `docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md` — the source of record; `knowledge/wiki/
  reviews/2026-07-12-foundation-intelligence-design-review.md` — the senior review.
- RFC-0005 (`Provider` seam, deterministic-in-CI), RFC-0014 (durable jobs), RFC-0015
  (Decision→Plan) — the reused substrate.

## Security impact

- **New access-control surface (design §4.10) is real and gated.** Claim-level sensitivity
  inheritance, per-agent capability restrictions on claim reads, redacted derivative claims,
  and a privileged/legal compartment are a genuine ACL layer — a **security-model change
  requiring Security Agent council review** before Slice 1's sensitivity work lands. The
  primitives exist (source `sensitivity` on `Repository` `models.py:74`; the `llm_router`
  PRIVATE-strips-`FREE_HOSTED` egress guardrail `services/llm_router.py:134-135`; LES-021
  provider context isolation), but half-built claim ACLs are worse than none — the
  compartmentalization sub-slice is explicitly gated and may be deferred within Slice 1
  without blocking the non-sensitive spine.
- **No new external surface in CI/default.** Deterministic tier drives extraction offline;
  agent extraction runs behind the `Provider` seam on the operator's authed node.
- **Every selection/approval/exception/baseline write** originates through the Authority
  envelope; baseline approval is a mandatory human gate. No autonomy introduced.
- C3 protects integrity: an LLM cannot launder an assertion into `observed`.

## Compliance impact

- Strongly governance-positive: this capability **is** the auditable traceability chain
  (design §21) — source → claim → trait → requirement → candidate → validation → approval —
  as durable, queryable rows. It directly serves the Constitution's evidence-over-opinion,
  verification-over-inference, human-approval, and memory articles. Immutable, hash-anchored
  evidence and baselines (C4) give reproducible audit. `selection_stage_events` records
  actor/timestamp/prev→new/reason/gate for every transition.

## Migration plan

- No migration in this RFC (contracts + decisions only). Each slice adds additive migrations
  from head `0028+`, single Alembic head preserved, `import aos_core.models` in each,
  validated by the no-drift autogenerate probe + compose-smoke `alembic upgrade head` on
  fresh Postgres.
- C5 backfill/adapter ships in Slice 1: existing `evidence`/`confidence` JSON is projected
  into read-only `Claim`/`Fragment` views so the spine reflects current data without a
  destructive rewrite; the projection is idempotent and re-runnable.
- Terminology namespacing to avoid collisions: `FoundationBaseline` (distinct from the
  Transfer Engine's "Verified Baseline" and Alembic `0001_baseline`), `CorpusSnapshot`
  (distinct from the runtime `LocalCorpusSource`), foundation `Claim` (distinct from the
  `services/jobs.py` job-lease `Claim` dataclass).

## Risks

- **C1/C2 two-sources-of-truth (highest).** If a decided claim or a candidate score forks
  from its `Decision`/`Recommendation`/`Evaluation` owner, the capability *undermines* the
  Constitution. Mitigation: C1 projection-only + C2 explicit reuse-vs-new gate, enforced in
  Slice 1/3 with tests.
- **C3 truth-layer integrity (highest).** Mitigation: deterministic-only `observed` guard +
  regression test, named enforcement point, Opus-designed.
- **Overconfidence regression (LES-023).** `GenomeSnapshot.aggregate_confidence` must be
  coverage-calibrated, never a naive average; Slice 2 ships a calibration test.
- **Cost.** Corpus-wide extraction + council-per-candidate is LLM-heavy. Mitigation:
  deterministic-first extraction via `llm_router`; agent extraction only where parsers can't
  reach; per-task tiering.
- **Scope creep across the runtime-integrity wave.** Mitigation: BRAIN/data-model files only;
  file-disjoint from AOS-REVIEW-002; each slice its own worktree.
- **State-machine sprawl (22 statuses).** Mitigation: data-driven transition table (Slice 0)
  + owned-transition CAS reused from `services/jobs.py`; `selection_stage_events` as the log.

## Acceptance criteria (this RFC)

- Operator approves the capability and the Slice 0/1-first sequencing.
- AD-1…AD-15 adopted as the binding acceptance frame; C1–C5 each carry a locked decision and
  a named verification method (test/guard/review) before Slice 1 code lands.
- Each slice maps to exactly one child RFC (RFC-0017…RFC-0023), argued before coded, each
  delivered as its own work spec(s) + PR(s) with builder ≠ verifier.
- The design's §20 scenario is adopted as the **capability MVP acceptance test** (spanning
  Slices 1–5) and referenced by each slice RFC's acceptance section.
- No slice introduces a table that duplicates an existing entity without an explicit
  reuse-vs-new decision (C2); no path mints an `observed` claim from a non-deterministic
  source (C3); no immutable row is UPDATE-able (C4).
- `AOS-COUNCIL-TYPED-001` may proceed independently of the spine.
- The claim-level compartmentalization sub-slice passes Security Agent council review before
  landing.

## Open questions

1. **`CandidateScore` reuse of `Evaluation` vs new table (C2).** Leaning reuse
   (`evaluation_type="foundation_score"`, score vector in JSON `findings`); confirm the
   vector/criterion shape fits at RFC-0020 time.
2. **`ValidationTask`/`ValidationResult` vs existing `Benchmark`/`Experiment`/`Evaluation`.**
   Leaning: `ValidationTask` is a new lightweight queueable entity, but its *result* projects
   into `Benchmark`/`Experiment` rows (which already carry evidence). Resolve at RFC-0021.
3. **Corpus freeze granularity** — per-selection-run vs per-project reusable snapshot. Leaning
   per-run immutable snapshot referencing shared `SourceVersion` rows. Resolve at RFC-0018.
4. **Claim-level sensitivity: deferred sub-slice or Slice-1 blocker?** Leaning: ship the
   non-sensitive spine first, gate the compartment behind Security Agent review as a Slice-1
   tail sub-slice. Confirm with the operator.
5. **Genome trait derivation:** how much is deterministic rules over DNA/architecture vs
   agent classification in Slice 2 (design says deterministic + human first). Resolve at
   RFC-0019.

## Dependencies

- **Reuses (live today):** RFC-0005 `Provider` seam + deterministic-in-CI; RFC-0014 durable
  jobs; RFC-0015 Decision→Plan; `services/authority.py` + `authority_envelope.py` (enforced
  at `enqueue_job`); `repository_scanner.py`; `services/council.py` +
  `synthesize_verdict`; `services/decisions.py`; `llm_router.py` egress guardrail.
- **Blocks:** all of Slices 1–6 (each child RFC references this one); implementation plans
  ultimately derive from `FoundationBaseline` via RFC-0015 (AD-15).
- **Enables:** the §21 traceable chain as a first-class, queryable, auditable artifact — the
  core of ArchetypeOS as an Engineering Intelligence Platform.

## Final Judge verdict

Pending operator approval. Scoped so the load-bearing, integrity-critical work (the
reconciliations C1–C5 and the Evidence Spine) is argued and locked before any schema is
written, the safe/high-leverage contract work (Slice 0) and the independent typed-council
win ship immediately, and every downstream slice is a strict superset argued in its own RFC.
Evidence over inference; conflicting evidence stays visible; hard constraints gate scores;
uncertainty becomes validation; human approval owns the baseline; local-first preserved.
Recommend acceptance and start RFC-0017 (Slice 0) + `AOS-COUNCIL-TYPED-001` on approval.
