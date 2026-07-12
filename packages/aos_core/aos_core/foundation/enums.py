"""Foundation Intelligence controlled vocabularies (RFC-0017 Slice 0).

One ``(str, Enum)`` per controlled vocabulary defined in
``docs/FOUNDATION_INTELLIGENCE_DESIGN_V0_1.md`` (the source of record). Values are
transcribed verbatim from the design's JSON blocks and prose lists so every later
slice (ORM columns, API DTOs, UI enums) imports the same vocabulary rather than
re-declaring it. This module is a pure leaf: stdlib only.

``Sensitivity`` is intentionally NOT redefined here — ``aos_core.sensitivity.Sensitivity``
is the single source (public/private/internal/confidential/restricted/secret). The
design's "privileged" legal compartment is deferred to RFC-0024.

``MinterClass`` (truth.py) and ``AuthorityDomain``/``AuthorityLevel`` (authority.py) live
in their own modules alongside the pure functions that use them.
"""
from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    """design §4.2 — the logical kind of an EvidenceSource."""

    REPOSITORY = "repository"
    DOCUMENT = "document"
    COMMUNICATION = "communication"
    SIMULATION = "simulation"
    TEST_RUN = "test_run"
    RUNTIME_RECORD = "runtime_record"
    EXTERNAL_REFERENCE = "external_reference"
    HUMAN_INPUT = "human_input"
    DIAGRAM = "diagram"
    DATASET = "dataset"


class SourceOrigin(str, Enum):
    """design §4.2 — how an EvidenceSource entered the system."""

    GITHUB = "github"
    UPLOAD = "upload"
    EMAIL = "email"
    LOCAL_FILESYSTEM = "local_filesystem"
    WEB = "web"
    CONNECTOR = "connector"
    MANUAL = "manual"
    GENERATED = "generated"


class SourceStatus(str, Enum):
    """design §4.2 — EvidenceSource lifecycle status."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"
    UNAVAILABLE = "unavailable"


class IngestionMethod(str, Enum):
    """design §4.3 — how an EvidenceSourceVersion was captured."""

    CONNECTOR = "connector"
    UPLOAD = "upload"
    SCAN = "scan"
    MANUAL = "manual"
    GENERATED = "generated"


class ExtractionMethod(str, Enum):
    """design §4.4 — how an EvidenceFragment was extracted."""

    DETERMINISTIC = "deterministic"
    PARSER = "parser"
    AGENT = "agent"
    HUMAN = "human"


class TruthLayer(str, Enum):
    """design §3 — the shared truth model. Must never be silently merged."""

    OBSERVED = "observed"
    CLAIMED = "claimed"
    INFERRED = "inferred"
    DECIDED = "decided"


class ClaimType(str, Enum):
    """design §4.5 — claim classification controlled vocabulary."""

    FACT = "fact"
    REQUIREMENT = "requirement"
    CONSTRAINT = "constraint"
    PREFERENCE = "preference"
    HYPOTHESIS = "hypothesis"
    FINDING = "finding"
    RISK = "risk"
    ASSUMPTION = "assumption"
    DECISION_CANDIDATE = "decision_candidate"
    DEFINITION = "definition"


class Polarity(str, Enum):
    """design §4.5 — Claim.polarity."""

    AFFIRMING = "affirming"
    NEGATING = "negating"
    QUALIFYING = "qualifying"


class Materiality(str, Enum):
    """design §4.5 / §4.9 — how much a claim or conflict matters."""

    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClaimStatus(str, Enum):
    """design §4.5 — Claim.status."""

    ACTIVE = "active"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class DerivationMethod(str, Enum):
    """design §4.5 — Claim.derivation.method."""

    DIRECT = "direct"
    EXTRACTED = "extracted"
    AGGREGATED = "aggregated"
    INFERRED = "inferred"
    APPROVED = "approved"


class EvidenceRelationship(str, Enum):
    """design §4.6 — ClaimEvidenceLink.relationship."""

    SUPPORTS = "supports"
    OPPOSES = "opposes"
    QUALIFIES = "qualifies"
    ORIGINATES = "originates"
    VERIFIES = "verifies"
    INVALIDATES = "invalidates"


class ClaimRelationship(str, Enum):
    """design §4.8 — the claim graph's supported relationship kinds."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    REFINES = "refines"
    DUPLICATES = "duplicates"
    DEPENDS_ON = "depends_on"
    DERIVED_FROM = "derived_from"
    IMPLEMENTS = "implements"
    VIOLATES = "violates"
    APPLIES_TO = "applies_to"
    VALIDATED_BY = "validated_by"
    INVALIDATED_BY = "invalidated_by"


class Strength(str, Enum):
    """design §4.6 — ClaimEvidenceLink.strength."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    DIRECT = "direct"


class ConflictType(str, Enum):
    """design §4.9 — EvidenceConflict.conflict_type."""

    DIRECT_CONTRADICTION = "direct_contradiction"
    SCOPE_MISMATCH = "scope_mismatch"
    TEMPORAL_CONFLICT = "temporal_conflict"
    AUTHORITY_CONFLICT = "authority_conflict"
    IMPLEMENTATION_DRIFT = "implementation_drift"
    AMBIGUITY = "ambiguity"


class ConflictStatus(str, Enum):
    """design §4.9 — EvidenceConflict.status."""

    OPEN = "open"
    ACCEPTED_EXCEPTION = "accepted_exception"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


class StateView(str, Enum):
    """design §6.2 — which system state a GenomeSnapshot describes."""

    CURRENT = "current"
    INTENDED = "intended"
    TARGET = "target"
    CANDIDATE = "candidate"


class GenomeStatus(str, Enum):
    """design §6.3 — GenomeSnapshot.status."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class GenomeDimension(str, Enum):
    """design §6.5 — the 16 Genome dimensions (A-P), as stable snake_case keys."""

    MISSION_PRODUCT_FORM = "mission_product_form"
    DOMAIN = "domain"
    LIFECYCLE_MATURITY = "lifecycle_maturity"
    SYSTEM_COMPOSITION = "system_composition"
    RUNTIME_TOPOLOGY = "runtime_topology"
    DEPLOYMENT_OWNERSHIP = "deployment_ownership"
    WORKLOAD_CHARACTERISTICS = "workload_characteristics"
    DATA_PROFILE = "data_profile"
    INTEGRATION_PROFILE = "integration_profile"
    AI_AUTONOMY = "ai_autonomy"
    ASSURANCE_CRITICALITY = "assurance_criticality"
    SECURITY_PRIVACY = "security_privacy"
    RELIABILITY_CONTINUITY = "reliability_continuity"
    ORGANIZATIONAL_CONTEXT = "organizational_context"
    ECONOMIC_DELIVERY_CONSTRAINTS = "economic_delivery_constraints"
    CHANGE_PROFILE = "change_profile"


class TraitClassification(str, Enum):
    """design §6.4 — GenomeTrait.classification."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    CONDITIONAL = "conditional"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class Stability(str, Enum):
    """design §6.4 — GenomeTrait.stability."""

    STABLE = "stable"
    EVOLVING = "evolving"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class Criticality(str, Enum):
    """design §6.4 — GenomeTrait.criticality."""

    INFORMATIONAL = "informational"
    IMPORTANT = "important"
    FOUNDATION_SHAPING = "foundation_shaping"


class AnswerType(str, Enum):
    """design §7 — OpenQuestion.answer_type."""

    BOOLEAN = "boolean"
    CHOICE = "choice"
    NUMBER = "number"
    TEXT = "text"
    DOCUMENT_REQUEST = "document_request"


class QuestionStatus(str, Enum):
    """design §7 — OpenQuestion.status."""

    OPEN = "open"
    ANSWERED = "answered"
    DEFERRED = "deferred"
    UNANSWERABLE = "unanswerable"


class RequirementType(str, Enum):
    """design §8 — FoundationRequirement.requirement_type."""

    HARD_CONSTRAINT = "hard_constraint"
    REQUIRED_CAPABILITY = "required_capability"
    QUALITY_ATTRIBUTE = "quality_attribute"
    PREFERENCE = "preference"
    OPTIMIZATION_GOAL = "optimization_goal"


class Priority(str, Enum):
    """design §8 — FoundationRequirement.priority."""

    MUST = "must"
    SHOULD = "should"
    COULD = "could"


class FoundationDomain(str, Enum):
    """design §9.2 — the 16 foundation domains, as stable snake_case keys."""

    PRODUCT_BOUNDARY = "product_boundary"
    ARCHITECTURE = "architecture"
    RUNTIME = "runtime"
    DEPLOYMENT = "deployment"
    DATA = "data"
    INTEGRATION = "integration"
    IDENTITY_AUTHORITY = "identity_authority"
    SECURITY_PRIVACY = "security_privacy"
    RELIABILITY = "reliability"
    OBSERVABILITY = "observability"
    VERIFICATION = "verification"
    DEVELOPMENT_WORKFLOW = "development_workflow"
    AGENT_GOVERNANCE = "agent_governance"
    OPERATIONS = "operations"
    ECONOMICS = "economics"
    MIGRATION_EVOLUTION = "migration_evolution"


class CandidateStatus(str, Enum):
    """design §9.3 — FoundationCandidate.status."""

    DRAFT = "draft"
    ELIGIBLE = "eligible"
    CHALLENGED = "challenged"
    VALIDATION_REQUIRED = "validation_required"
    SELECTABLE = "selectable"
    REJECTED = "rejected"
    SELECTED = "selected"


class Reversibility(str, Enum):
    """design §9.3 — FoundationCandidate.reversibility."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvaluationCriterion(str, Enum):
    """design §10.2 — the 20 candidate evaluation criteria, as snake_case keys."""

    REQUIREMENT_COVERAGE = "requirement_coverage"
    ARCHITECTURAL_COHERENCE = "architectural_coherence"
    SECURITY_FITNESS = "security_fitness"
    PRIVACY_COMPLIANCE_FITNESS = "privacy_compliance_fitness"
    RELIABILITY_FITNESS = "reliability_fitness"
    OPERATIONAL_FEASIBILITY = "operational_feasibility"
    TEAM_CAPABILITY_FIT = "team_capability_fit"
    COST_FIT = "cost_fit"
    DELIVERY_SPEED = "delivery_speed"
    PERFORMANCE_FITNESS = "performance_fitness"
    SCALABILITY_FITNESS = "scalability_fitness"
    MAINTAINABILITY = "maintainability"
    TESTABILITY = "testability"
    OBSERVABILITY = "observability"
    REVERSIBILITY = "reversibility"
    VENDOR_LOCK_IN = "vendor_lock_in"
    EXISTING_ASSET_REUSE = "existing_asset_reuse"
    MIGRATION_COMPLEXITY = "migration_complexity"
    EVIDENCE_STRENGTH = "evidence_strength"
    RESIDUAL_UNCERTAINTY = "residual_uncertainty"


class ValidationType(str, Enum):
    """design §11 — ValidationTask.validation_type."""

    PROTOTYPE = "prototype"
    BENCHMARK = "benchmark"
    SIMULATION = "simulation"
    SECURITY_REVIEW = "security_review"
    LEGAL_REVIEW = "legal_review"
    USER_TEST = "user_test"
    VENDOR_CHECK = "vendor_check"
    INTEGRATION_SPIKE = "integration_spike"


class ValidationStatus(str, Enum):
    """design §11 — ValidationTask.status."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class BaselineStatus(str, Enum):
    """design §12 Stage 14 — FoundationBaseline.status."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class SelectionRunState(str, Enum):
    """design §13 — the 22 persisted Selection Run states."""

    DRAFT = "draft"
    INTAKE_COMPLETE = "intake_complete"
    CORPUS_FROZEN = "corpus_frozen"
    EVIDENCE_EXTRACTED = "evidence_extracted"
    CURRENT_STATE_RECONSTRUCTED = "current_state_reconstructed"
    INTENT_RECONSTRUCTED = "intent_reconstructed"
    RECONCILED = "reconciled"
    GENOME_REVIEW = "genome_review"
    REQUIREMENTS_COMPILED = "requirements_compiled"
    CANDIDATES_GENERATED = "candidates_generated"
    ELIGIBILITY_REVIEW = "eligibility_review"
    COUNCIL_REVIEW = "council_review"
    VALIDATION_REQUIRED = "validation_required"
    VALIDATION_COMPLETE = "validation_complete"
    READY_FOR_SELECTION = "ready_for_selection"
    SELECTED = "selected"
    BASELINED = "baselined"
    EXECUTION_COMPILED = "execution_compiled"
    MONITORING = "monitoring"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
