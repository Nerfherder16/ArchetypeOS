# Foundation Intelligence Design Review — System Genome, Evidence Model & Foundation-Selection Lifecycle

Date: 2026-07-12
Reviewer: Opus orchestrator (senior engineering reasoning lane)
Scope: senior architecture review of the operator-supplied conceptual design v0.1 (`docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md`) against the implemented ArchetypeOS codebase
Artifact type: strategic design review / RFC input note
Status: advisory; no runtime changes. Produced `docs/rfc/RFC-0016`.

## Verification Metadata

Verification Status: Verified with warnings
Verification Level: Level 1
Verification Method: Repository inspection. Delegated two parallel reconnaissance agents over `packages/aos_core/aos_core/` (models + services), `apps/api/alembic/versions/`, and `apps/worker/`, plus direct reads of the required-reading docs (Constitution context, data model, decision lifecycle, engine catalog, RFC process, current state) and direct grep verification of the specific file:line anchors cited below. No local runtime, Docker, Playwright, or test execution was performed in this lane.
Evidence: `packages/aos_core/aos_core/models.py` (evidence/confidence columns, `CouncilAgentOutput`, `ResearchRun`), `services/council.py` (evidence selectors + string-flatten contract), `services/llm_router.py` (egress guardrail), `services/authority.py` + `authority_envelope.py`, `services/decisions.py`, `repository_scanner.py`, `apps/api/alembic/versions/` (head `0027`), `docs/ENGINE_CATALOG.md`, `docs/DECISION_LIFECYCLE.md`, `docs/RFC_PROCESS.md`, `docs/V0_1_DATA_MODEL.md`, `docs/CURRENT_STATE.md`, `.archetype/context.md`, `.archetype/roadmap.md`.
Limitations: Not a live runtime pass. Model/table claims are from source inspection and grep, not from a running database schema dump. Effort/sequencing estimates are planning figures, not commitments.
Required Next Verifier: Engineering Council + operator, at RFC-0016 adjudication (RFC_PROCESS: Council Review → Final Judge).

## Executive Verdict

This is the right idea, aimed at the platform's single biggest structural gap, but specified
at a scale that violates ArchetypeOS's own change-control discipline and leaves five
load-bearing reconciliations undefined. **Accept in principle as a capability RFC series;
reject as a single unit of work.**

The design's §21 governing principle — an unbroken chain from source → claim → trait →
requirement → candidate → validation → approval — is literally the Constitution's thesis. The
core insight is confirmed by code: **evidence and confidence in ArchetypeOS are not entities.**
`evidence` is a JSON list column repeated on ~12 tables; `confidence` is a scalar `Float`
duplicated on ~10 (`packages/aos_core/aos_core/models.py`). There is no `Claim`, evidence link,
conflict entity, genome, foundation, or corpus snapshot anywhere in code. So this design is
*additive connective tissue*, not a rewrite — the strongest argument for it.

## Evidence: design assumptions vs. implemented reality

| Design assumption | Reality in code | Implication |
|---|---|---|
| "Already models decisions, research, recommendations, plans" | True and real; Alembic-migrated (head `0027`) | Reuse these; do not shadow |
| "Knowledge Graph stores claims, relationships, conflicts, provenance" (§14) | Doc-only; no implementation | The Evidence Graph *is* the unbuilt Knowledge Graph, made real |
| "Generic finding array is insufficient; agents need typed payloads" (§11) | Confirmed: `council.py` selectors produce `{kind, detail, ref}` (`:59,82,90,143`) but the contract flattens to string arrays (`:264-267`), stored untyped on `CouncilAgentOutput` (`models.py:635`) | Accurate critique on a real seam — extractable quick win |
| Conflicts / open questions are new | Already JSON lists on `ResearchRun` (`models.py:291-292`) | Precedent exists; promote to entities as a superset |
| Sensitivity / egress compartmentalization (§4.10) | Partly real (authority envelope; `llm_router` PRIVATE strips `FREE_HOSTED` `:134-135`; LES-021 isolation) | Primitives exist; claim-level ACLs are net-new → security-model change → RFC + Security review |
| Immutable, versioned evidence & baselines (§19.6, Stage 14) | No enforcement primitive; `AuditMixin` has a *mutable* `version` + `updated_at` | Immutability is aspirational; needs a real mechanism |

## What is genuinely strong (affirmed, adopted as AD-1…AD-15 in RFC-0016)

1. Claim-centric over document-centric; four truth layers kept strictly separate.
2. Authority / confidence / relevance / freshness as independent measures, with
   domain-specific authority (no universal source ranking).
3. Hard constraints evaluated before weighted scoring — prevents score-laundering an
   ineligible candidate.
4. High uncertainty produces validation tasks, not invented certainty (answers LES-023).
5. The §20 MVP scenario is a legitimate end-to-end vertical slice — kept as the acceptance spine.

## Concerns → the five reconciliations the design omits (locked in RFC-0016 as C1–C5)

- **C1 — `Claim("decided")` vs `Decision`.** Must be a projection of the existing `Decision`
  row, not a second home. Else approval state forks (LES-L09 drift class).
- **C2 — `FoundationCandidate`/`CandidateScore` vs `Recommendation`/`Evaluation`.** Decide
  reuse-vs-new explicitly; reuse by default ("fitness over familiarity" applied to our schema).
- **C3 — `truth_layer="observed"` integrity invariant.** Only the deterministic tier may mint
  `observed`; agents mint only `claimed`/`inferred`; `decided` via the approval path. Enforce
  in code + regression test. The single most important control in the design.
- **C4 — Immutability mechanism.** `content_hash` over canonical serialization + no-UPDATE
  guard + DB constraint + tests; reproducible `claim_set_hash`/`baseline_hash`.
- **C5 — Backfill.** Adapter projecting existing JSON evidence into read-only claim views so
  old and new models cannot diverge.

Secondary: `GenomeSnapshot.aggregate_confidence` must be coverage-calibrated, not averaged
(LES-023). Terminology collisions to namespace: "baseline" (Transfer Engine Verified Baseline
+ Alembic `0001_baseline`), "corpus" (`LocalCorpusSource`), "claim" (job-lease dataclass).

## Recommendation

Accept as a capability, reject as a single build. (1) Governing capability RFC (**RFC-0016**,
written) locking AD-1…AD-15 + C1–C5 + the mature-state target + slice→child-RFC map. (2) Slice
0 (contracts/fixtures — no UI/LLM) first. (3) Slice 1 (Evidence Spine) as the load-bearing
data-model RFC where C1–C5 become code. (4) Pull the typed-council-payload forward as an
independent quick win (`AOS-COUNCIL-TYPED-001`). (5) Defer Genome/Foundation/Baseline/Evolution
to downstream RFCs (RFC-0019…0023).

## Alternatives considered

- Build as specified, monolithically — rejected (violates one-PR-one-package + RFC gates;
  ~30-table Alembic churn with C1–C5 unresolved).
- Keep evidence as richer JSON — rejected (loses queryable/linkable/versioned claims).
- Slice 0 → Evidence Spine first, child-RFC series — chosen (matches house process; front-loads
  cheap high-leverage contracts; independent early win; reversible slices).

## Risk

Highest: C1/C2 two-sources-of-truth and C3 truth-layer integrity — if unaddressed the
capability *undermines* the Constitution instead of serving it. Security: claim-level
compartmentalization is a real ACL layer (gate behind Security Agent review). Cost:
corpus-wide extraction + council-per-candidate is LLM-heavy (deterministic-first, tiered via
`llm_router`). Overconfidence regression (LES-023) on aggregate genome confidence.

## Next steps

RFC-0016 drafted (this change set). On operator approval: start RFC-0017 (Slice 0 contracts) +
`AOS-COUNCIL-TYPED-001` in parallel; Slice 1 (RFC-0018 Evidence Spine) once Slice 0 lands.
Each slice is argued in its own child RFC before it is coded (RFC_PROCESS).
