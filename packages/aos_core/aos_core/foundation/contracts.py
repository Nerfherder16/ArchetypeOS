"""Pydantic v2 contracts for every Foundation Intelligence entity (RFC-0017 Slice 0).

Fields and value-types are transcribed from ``docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md``
§3-§13's JSON blocks, enum-typed where a controlled vocabulary exists (``enums.py``).
All models are frozen (immutable) and reject unknown fields (``extra="forbid"``).

Reconciliation validators live on the models themselves:

- **C1** (``Claim``): ``truth_layer == "decided"`` requires ``derivation.method ==
  "approved"`` *and* ``decision_ref`` set; a non-decided claim must NOT carry a
  ``decision_ref``.
- **C3** (``Claim``): ``may_mint(minted_by, truth_layer)`` must hold at
  construction time — an invalid pairing fails fast, not at DB write.
- **C2 reuse links**: ``FoundationCandidate.recommendation_ref``,
  ``CandidateScore.evaluation_ref``, ``ValidationTask.result_refs`` name the
  reuse-vs-new targets in the type itself.

``sensitivity`` fields reuse ``aos_core.sensitivity.Sensitivity`` verbatim — no
shadow enum is defined here. The design's "privileged" legal compartment is
deferred to RFC-0024 and intentionally NOT modeled.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from ..sensitivity import Sensitivity
from .authority import AuthorityDomain
from .enums import (
    AnswerType,
    BaselineStatus,
    CandidateStatus,
    ClaimRelationship,
    ClaimStatus,
    ClaimType,
    ConflictStatus,
    ConflictType,
    Criticality,
    DerivationMethod,
    EvaluationCriterion,
    EvidenceRelationship,
    ExtractionMethod,
    FoundationDomain,
    GenomeDimension,
    GenomeStatus,
    IngestionMethod,
    Materiality,
    Polarity,
    Priority,
    QuestionStatus,
    RequirementType,
    Reversibility,
    SelectionRunState,
    SourceOrigin,
    SourceStatus,
    SourceType,
    Stability,
    StateView,
    Strength,
    TraitClassification,
    TruthLayer,
    ValidationStatus,
    ValidationType,
)
from .truth import MinterClass, may_mint


class _Frozen(BaseModel):
    """Shared base: immutable, unknown-field-rejecting."""

    model_config = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------
# Evidence domain
# --------------------------------------------------------------------------


class Locator(_Frozen):
    """design §4.4 — permissive; a fragment may locate code lines, PDF pages,
    spreadsheet ranges, video timestamps, JSON paths, or message ids."""

    path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    page: int | None = None
    section: str | None = None
    timestamp_start: str | None = None
    timestamp_end: str | None = None
    json_pointer: str | None = None


class EvidenceSource(_Frozen):
    """design §4.2."""

    id: str
    project_id: str
    source_type: SourceType
    title: str
    origin: SourceOrigin
    originator: str
    canonical_uri: str | None = None
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    authority_domains: list[AuthorityDomain] = []
    access_policy_id: str | None = None
    status: SourceStatus = SourceStatus.ACTIVE
    created_at: datetime | None = None
    minted_by: MinterClass


class EvidenceSourceVersion(_Frozen):
    """design §4.3 — immutable; corrections create new versions."""

    id: str
    source_id: str
    version_ref: str
    content_hash: str
    captured_at: datetime | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    supersedes_version_id: str | None = None
    ingestion_method: IngestionMethod
    parser_version: str | None = None
    minted_by: MinterClass


class EvidenceFragment(_Frozen):
    """design §4.4."""

    id: str
    source_version_id: str
    locator: Locator = Locator()
    content_hash: str
    excerpt: str
    extraction_method: ExtractionMethod
    extraction_confidence: float = 0.0
    minted_by: MinterClass


class ClaimScope(_Frozen):
    """design §4.5 — Claim.scope."""

    system_id: str | None = None
    repository_ids: list[str] = []
    component_ids: list[str] = []
    environment: str | None = None
    applicable_version: str | None = None


class Derivation(_Frozen):
    """design §4.5 — Claim.derivation."""

    method: DerivationMethod
    parent_claim_ids: list[str] = []


class Claim(_Frozen):
    """design §4.5 — the central reasoning primitive.

    C1 and C3 are enforced as a post-construction model validator.
    """

    id: str
    project_id: str
    statement: str
    claim_type: ClaimType
    truth_layer: TruthLayer
    domain: str
    scope: ClaimScope = ClaimScope()
    polarity: Polarity = Polarity.AFFIRMING
    confidence: float = 1.0
    materiality: Materiality = Materiality.MEDIUM
    status: ClaimStatus = ClaimStatus.ACTIVE
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    created_by: str
    derivation: Derivation
    minted_by: MinterClass
    decision_ref: str | None = None

    @model_validator(mode="after")
    def _check_c1_and_c3(self) -> "Claim":
        # C1 — a decided claim is a Decision projection.
        if self.truth_layer == TruthLayer.DECIDED:
            if self.derivation.method != DerivationMethod.APPROVED or self.decision_ref is None:
                raise ValueError(
                    "C1 violation: a 'decided' claim requires derivation.method='approved' "
                    "and a decision_ref"
                )
        else:
            if self.decision_ref is not None:
                raise ValueError("C1 violation: only a 'decided' claim may carry decision_ref")
        # C3 — deterministic-only-observed minter guard.
        if not may_mint(self.minted_by, self.truth_layer):
            raise ValueError(
                f"C3 violation: {self.minted_by.value!r} may not mint a {self.truth_layer.value!r} claim"
            )
        return self


class ClaimEvidenceLink(_Frozen):
    """design §4.6 — evidence has a relationship to the claim, not a bare attachment."""

    claim_id: str
    fragment_id: str
    relationship: EvidenceRelationship
    relevance: float = 1.0
    strength: Strength = Strength.MODERATE
    notes: str | None = None
    minted_by: MinterClass


class ClaimRelationshipEdge(_Frozen):
    """design §4.8 — the claim graph's edges."""

    from_claim_id: str
    to_claim_id: str
    relationship: ClaimRelationship
    notes: str | None = None
    minted_by: MinterClass


class EvidenceConflict(_Frozen):
    """design §4.9 — a contradiction that remains visible until explicitly resolved."""

    id: str
    project_id: str
    claim_ids: list[str]
    conflict_type: ConflictType
    materiality: Materiality
    status: ConflictStatus = ConflictStatus.OPEN
    resolution: str | None = None
    resolution_decision_id: str | None = None
    blocking_stages: list[str] = []
    minted_by: MinterClass


class RepositoryRef(_Frozen):
    """design §5 — CorpusSnapshot.repository_refs entry."""

    repository_id: str
    commit_sha: str
    branch: str | None = None


class CorpusSnapshot(_Frozen):
    """design §5 — the frozen analysis input set."""

    id: str
    project_id: str
    source_version_ids: list[str] = []
    repository_refs: list[RepositoryRef] = []
    claim_set_hash: str | None = None
    created_at: datetime | None = None
    created_by: str = "system"
    purpose: str


class OpenQuestion(_Frozen):
    """design §7."""

    id: str
    project_id: str
    genome_snapshot_id: str | None = None
    question: str
    affected_dimensions: list[GenomeDimension] = []
    affected_foundation_domains: list[FoundationDomain] = []
    materiality: Materiality
    reason: str
    answer_type: AnswerType
    status: QuestionStatus = QuestionStatus.OPEN
    answer_claim_id: str | None = None
    minted_by: MinterClass


# --------------------------------------------------------------------------
# Genome domain
# --------------------------------------------------------------------------


class Archetype(_Frozen):
    """design §6.6 — a readable summary over traits, not a substitute for them."""

    name: str
    confidence: float
    trait_ids: list[str] = []


class GenomeSnapshot(_Frozen):
    """design §6.3."""

    id: str
    project_id: str
    corpus_snapshot_id: str
    state_view: StateView
    version: int = 1
    status: GenomeStatus = GenomeStatus.DRAFT
    summary: str = ""
    primary_archetypes: list[Archetype] = []
    secondary_archetypes: list[Archetype] = []
    coverage: float = 0.0
    aggregate_confidence: float = 0.0
    open_question_count: int = 0
    critical_conflict_count: int = 0
    generated_by_run_id: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    minted_by: MinterClass


class GenomeTrait(_Frozen):
    """design §6.4 — an individual evidence-backed trait."""

    id: str
    genome_snapshot_id: str
    dimension: GenomeDimension
    trait_key: str
    value: bool | int | float | str
    value_type: str
    classification: TraitClassification = TraitClassification.UNKNOWN
    confidence: float = 0.0
    stability: Stability = Stability.UNKNOWN
    criticality: Criticality = Criticality.INFORMATIONAL
    rationale: str = ""
    supporting_claim_ids: list[str] = []
    opposing_claim_ids: list[str] = []
    source_methods: list[str] = []
    human_locked: bool = False
    minted_by: MinterClass


# --------------------------------------------------------------------------
# Foundation domain
# --------------------------------------------------------------------------


class FoundationRequirement(_Frozen):
    """design §8."""

    id: str
    project_id: str
    genome_snapshot_id: str | None = None
    requirement_type: RequirementType
    domain: FoundationDomain
    statement: str
    priority: Priority
    weight: float = 0.5
    veto_if_unsatisfied: bool = False
    claim_ids: list[str] = []
    verification_method: str
    minted_by: MinterClass


class FoundationCandidate(_Frozen):
    """design §9.3."""

    id: str
    selection_run_id: str
    name: str
    summary: str = ""
    status: CandidateStatus = CandidateStatus.DRAFT
    architecture_style: list[str] = []
    foundation_elements: list[str] = []
    assumption_claim_ids: list[str] = []
    satisfied_requirement_ids: list[str] = []
    unsatisfied_requirement_ids: list[str] = []
    hard_constraint_violations: list[str] = []
    risks: list[str] = []
    validation_tasks: list[str] = []
    estimated_cost: dict = {}
    estimated_effort: dict = {}
    reversibility: Reversibility = Reversibility.MEDIUM
    lock_in_profile: dict = {}
    score_summary: dict = {}
    confidence: float = 0.0
    recommendation_ref: str | None = None
    minted_by: MinterClass


class FoundationElement(_Frozen):
    """design §9.4."""

    id: str
    candidate_id: str
    domain: FoundationDomain
    title: str
    decision: str
    rationale: str = ""
    technology_refs: list[str] = []
    claim_ids: list[str] = []
    requirement_ids: list[str] = []
    alternatives_rejected: list[str] = []
    tradeoffs: list[str] = []
    risks: list[str] = []
    verification_method: str
    minted_by: MinterClass


class CandidateScore(_Frozen):
    """design §10.3 — the UI shows the score vector, not only one overall number."""

    candidate_id: str
    criterion: EvaluationCriterion
    raw_score: float
    weight: float
    confidence: float
    uncertainty_penalty: float = 0.0
    adjusted_score: float
    rationale: str = ""
    supporting_claim_ids: list[str] = []
    reviewer_agent_id: str | None = None
    evaluation_ref: str | None = None
    minted_by: MinterClass


class ValidationTask(_Frozen):
    """design §11 — prescribe validation rather than invent certainty."""

    id: str
    candidate_id: str
    title: str
    validation_type: ValidationType
    question: str
    method: str = ""
    success_criteria: list[str] = []
    failure_criteria: list[str] = []
    required_evidence: list[str] = []
    blocking: bool = False
    status: ValidationStatus = ValidationStatus.PROPOSED
    result_claim_ids: list[str] = []
    result_refs: list[str] = []
    minted_by: MinterClass


class FoundationBaseline(_Frozen):
    """design §12 Stage 14 — the approved, immutable Foundation Baseline."""

    id: str
    project_id: str
    candidate_id: str
    target_genome_snapshot_id: str
    version: str = "1.0"
    status: BaselineStatus = BaselineStatus.ACTIVE
    approved_decision_id: str
    corpus_snapshot_id: str
    approved_by: str
    approved_at: datetime | None = None
    effective_from: datetime | None = None
    review_triggers: list[str] = []
    baseline_hash: str | None = None
    minted_by: MinterClass


class SelectionStageEvent(_Frozen):
    """design §13 — one recorded transition of a Selection Run's state machine."""

    id: str
    selection_run_id: str
    actor: str
    timestamp: datetime | None = None
    previous_state: SelectionRunState | None = None
    new_state: SelectionRunState
    reason: str | None = None
    evidence_generated: list[str] = []
    gate_result: dict = {}
    authority_envelope: dict | None = None
