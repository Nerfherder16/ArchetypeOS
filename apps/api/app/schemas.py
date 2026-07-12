from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    name: str
    slug: str | None = None
    description: str | None = None


class ProjectUpdate(BaseModel):
    # Partial update — only the fields provided are changed. MVP surface: the
    # per-project nightly-audit toggle.
    audits_enabled: bool | None = None


class ProjectRead(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    audits_enabled: bool
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryCreate(BaseModel):
    name: str
    local_path: str
    default_branch: str | None = None
    remote_url: str | None = None
    # AOS-AUTHORITY-HARDEN-001: data-sensitivity policy; drives egress approval.
    sensitivity: str = "public"


class RepositoryRead(BaseModel):
    id: str
    project_id: str
    name: str
    local_path: str
    default_branch: str | None
    remote_url: str | None
    is_read_only: bool
    sensitivity: str
    status: str
    last_scanned_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    project_id: str | None = None
    repository_id: str | None = None
    job_type: str
    payload: dict = Field(default_factory=dict)
    priority: int = 100


class JobRead(BaseModel):
    id: str
    project_id: str | None
    repository_id: str | None
    job_type: str
    status: str
    priority: int
    payload: dict
    result: dict | None
    error: str | None
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempts: int
    # AOS-NODE-EXECUTION-001: routing decision, surfaced for the Control Tower audit.
    required_capability: str | None = None
    sensitivity: str = "public"
    requires_write: bool = False
    assigned_node_id: str | None = None
    routing_status: str = "unrouted"
    routing_explanation: str | None = None
    routed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    name: str
    job_type: str
    interval_seconds: int
    payload: dict = Field(default_factory=dict)
    enabled: bool = True


class ScheduleRead(BaseModel):
    id: str
    project_id: str | None
    name: str
    job_type: str
    interval_seconds: int
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleUpdate(BaseModel):
    name: str | None = None
    interval_seconds: int | None = None
    enabled: bool | None = None


class ArtifactCreate(BaseModel):
    project_id: str
    repository_id: str | None = None
    job_id: str | None = None
    artifact_type: str
    name: str
    path: str
    content_type: str | None = None
    checksum: str | None = None
    size_bytes: int | None = None
    summary: str | None = None


class ArtifactRead(ArtifactCreate):
    id: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryScanRead(BaseModel):
    repository_id: str
    summary: dict
    dna: dict
    architecture_nodes: list[dict]
    architecture_edges: list[dict]
    artifacts: list[dict]


class RepositoryDnaRead(BaseModel):
    repository_id: str
    purpose: str | None
    maturity: str | None
    language_mix: dict
    package_managers: list
    frameworks: list
    runtime_services: list
    deployment_files: list
    risk_flags: list
    scan_summary: dict
    evidence: list
    confidence: float
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArchitectureNodeRead(BaseModel):
    id: str
    project_id: str
    repository_id: str | None
    label: str
    type: str
    parent_id: str | None
    confidence: float
    evidence: list
    risks: list
    manual_correction: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArchitectureEdgeRead(BaseModel):
    id: str
    project_id: str
    repository_id: str | None
    from_node_id: str
    to_node_id: str
    type: str
    confidence: float
    evidence: list
    manual_correction: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArchitectureGraphRead(BaseModel):
    nodes: list[ArchitectureNodeRead]
    edges: list[ArchitectureEdgeRead]


class ArchitectureCorrectionUpdate(BaseModel):
    manual_correction: str | None = None


class DecisionCreate(BaseModel):
    title: str
    context: str | None = None
    decision: str | None = None
    alternatives: list = Field(default_factory=list)
    tradeoffs: list = Field(default_factory=list)
    consequences: list = Field(default_factory=list)
    evidence: list = Field(default_factory=list)
    confidence: float = 0.0
    research_note_ids: list[str] = Field(default_factory=list)


class DecisionRead(BaseModel):
    id: str
    project_id: str
    title: str
    context: str | None
    decision: str | None
    alternatives: list
    tradeoffs: list
    consequences: list
    evidence: list
    confidence: float
    status: str
    approved_by: str | None
    approved_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DecisionApprove(BaseModel):
    approver: str
    rationale: str | None = None


class DecisionReject(BaseModel):
    approver: str
    rationale: str


# AOS-EVOLVE-001 (RFC-0015 Wave C) — Evolution Engine: staleness + re-evaluation.
class DecisionStaleness(BaseModel):
    decision_id: str
    title: str
    reason: str
    age_days: int | None = None


class DecisionReevaluate(BaseModel):
    reason: str | None = None


# AOS-BUILD-PLAN-001 (RFC-0015 Design §1) — Decision → Plan.
class ImplementationPlanRead(BaseModel):
    id: str
    decision_id: str
    project_id: str
    title: str
    objective: str | None
    tasks: list
    acceptance_criteria: list
    verification_requirements: list
    target_repository_id: str | None
    risk: str | None
    effort: str | None
    evidence: list
    status: str
    approved_by: str | None
    approved_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImplementationPlanApprove(BaseModel):
    approver: str
    rationale: str | None = None


class ResearchNoteCreate(BaseModel):
    title: str
    question: str | None = None
    summary: str | None = None
    sources: list = Field(default_factory=list)
    findings: list = Field(default_factory=list)
    freshness: str | None = None
    confidence: float = 0.0


class ResearchNoteRead(BaseModel):
    id: str
    project_id: str
    title: str
    question: str | None
    summary: str | None
    sources: list
    findings: list
    freshness: str | None
    confidence: float
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# AOS-RESEARCH-003 — multi-phase research plans.
class ResearchPlanCreate(BaseModel):
    question: str
    sensitivity: str = "public"


class ResearchPlanRead(BaseModel):
    id: str
    project_id: str
    question: str
    sensitivity: str
    plan_status: str
    required_source_types: list
    search_queries: list
    verification_steps: list
    synthesis_policy: dict
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResearchRunRead(BaseModel):
    id: str
    plan_id: str
    project_id: str
    job_id: str | None
    run_status: str
    phases: list
    sources: list
    findings: list
    conflicts: list
    open_questions: list
    confidence: float
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceDecisionRequest(BaseModel):
    accepted: bool
    reason: str


# AOS-SELFHEAL observability — nightly-probe heartbeats.
class AuditHeartbeatCreate(BaseModel):
    routine: str
    status: str
    day: str
    pr_url: str | None = None
    detail: str | None = None
    project_id: str | None = None


class AuditHeartbeatRead(BaseModel):
    id: str
    routine: str
    project_id: str | None
    heartbeat_status: str
    day: str
    pr_url: str | None
    detail: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResearchRequest(BaseModel):
    question: str
    sensitivity: str = "public"


class RecommendationCreate(BaseModel):
    title: str
    recommendation: str
    rationale: str | None = None
    alternatives: list = Field(default_factory=list)
    pros: list = Field(default_factory=list)
    cons: list = Field(default_factory=list)
    risk: str | None = None
    effort: str | None = None
    dependencies: list = Field(default_factory=list)
    acceptance_criteria: list = Field(default_factory=list)
    evidence: list
    confidence: float = 0.0

    @field_validator("evidence")
    @classmethod
    def evidence_must_not_be_empty(cls, value: list) -> list:
        if not value:
            raise ValueError("Recommendations require evidence field")
        return value


class RecommendationRead(BaseModel):
    id: str
    project_id: str
    title: str
    recommendation: str | None
    rationale: str | None
    alternatives: list
    pros: list
    cons: list
    risk: str | None
    effort: str | None
    dependencies: list
    acceptance_criteria: list
    evidence: list
    confidence: float
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransferRequest(BaseModel):
    need: str


class TransferRecommendationRead(BaseModel):
    source_repository: str
    source_project_id: str | None
    reusable_asset: str
    reason: str
    matched_terms: list
    evidence: list
    required_changes: str | None
    risks: str | None
    confidence: float


class NightlyDigestRead(BaseModel):
    id: str
    project_id: str
    digest_date: datetime
    summary: str | None
    changes: list
    recommendations: list
    repeated_tasks: list
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgePageRead(BaseModel):
    id: str
    project_id: str | None
    title: str
    vault_path: str
    page_type: str
    validation_state: str
    source_refs: list
    checksum: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSyncResult(BaseModel):
    synced: int
    created: int
    updated: int
    open_lessons: int


class CouncilReviewCreate(BaseModel):
    question: str


class CouncilAgentOutputRead(BaseModel):
    id: str
    review_id: str
    agent_name: str
    agent_type: str
    status: str
    summary: str | None
    findings: list
    evidence: list
    concerns: list
    confidence: float
    agent_model: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CouncilReviewRead(BaseModel):
    id: str
    project_id: str
    question: str | None
    verdict: str
    confidence: float
    agreements: list
    disagreements: list
    unsupported_claims: list
    follow_up: list
    provider: str | None
    job_id: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    agent_outputs: list[CouncilAgentOutputRead] = []

    model_config = {"from_attributes": True}


class VoiceTurnCreate(BaseModel):
    transcript: str
    source_device: str = "unknown"
    project_id: str | None = None

    @field_validator("transcript")
    @classmethod
    def _transcript_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("transcript must not be empty")
        return value.strip()


class VoiceSpeakRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _text_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("text must not be empty")
        return value.strip()


class VoiceInboxUpdate(BaseModel):
    review_state: str

    @field_validator("review_state")
    @classmethod
    def _valid_review_state(cls, value: str) -> str:
        allowed = {"pending", "approved", "dismissed"}
        candidate = (value or "").strip().lower()
        if candidate not in allowed:
            raise ValueError(f"review_state must be one of {sorted(allowed)}")
        return candidate


class VoiceInboxItemRead(BaseModel):
    id: str
    project_id: str | None = None
    transcript: str
    summary: str
    detected_intent: str
    detected_project: str | None = None
    suggested_action: str
    confidence: float
    required_review: bool
    review_state: str
    source_device: str
    reply_text: str
    promoted_kind: str | None = None
    promoted_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NodeCapabilityInput(BaseModel):
    capability: str
    version: str | None = None
    limits: dict = {}


class NodeRegister(BaseModel):
    name: str
    node_type: str = "worker"
    endpoint: str | None = None
    max_sensitivity: str = "public"
    write_access: bool = False
    capabilities: list[NodeCapabilityInput] = []

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("name must not be empty")
        return value.strip()


class NodeCapabilityRead(BaseModel):
    id: str
    capability: str
    capability_version: str | None = None
    capability_status: str
    limits: dict

    model_config = {"from_attributes": True}


class NodeRead(BaseModel):
    id: str
    name: str
    node_type: str
    endpoint: str | None = None
    node_status: str
    last_seen_at: datetime | None = None
    max_sensitivity: str
    write_access: bool
    capabilities: list[NodeCapabilityRead] = []
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    # AOS-AUTH-BOUNDARY-001: the operator who last enrolled/rotated/revoked (audit).
    updated_by: str

    model_config = {"from_attributes": True}


class NodeEnrollRead(NodeRead):
    # AOS-NODE-IDENTITY-001 (P0-5): the plaintext node token, shown ONCE at
    # enrollment (only its hash is stored). The node presents it on heartbeat/claim.
    token: str


class RoutingDecisionRead(BaseModel):
    # AOS-NODE-AGENT-001 (P1-2): the capability-routing decision + a human-readable
    # explanation for the Control Tower.
    node_id: str | None = None
    node_name: str | None = None
    eligible_node_ids: list[str] = []
    explanation: str


class NodeHeartbeatCreate(BaseModel):
    health: str = "healthy"
    metrics: dict = {}


class NodeHeartbeatRead(BaseModel):
    id: str
    node_id: str
    health: str
    observed_at: datetime
    metrics: dict

    model_config = {"from_attributes": True}


class ConnectorRead(BaseModel):
    id: str
    name: str
    connector_type: str
    tier: str
    enabled: bool
    configured: bool
    # AOS-CONNECTOR-RUNTIME-001 (P0-4): decomposed status — credential present vs
    # actually reachable (a non-empty default URL is configured but may be down).
    credential_present: bool = False
    reachable: bool | None = None
    privacy_class: str
    egress_allowed: bool
    browser_exposed: bool
    quota_policy: str
    last_health_status: str
    last_error: str | None = None
    last_checked_at: datetime | None = None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectorHealthUpdate(BaseModel):
    status: str = "healthy"
    error: str | None = None


class ActionClassRead(BaseModel):
    name: str
    level: int
    always_requires_approval: bool
    description: str


class AuthorityEvaluateRequest(BaseModel):
    action_type: str
    target: str | None = None
    sensitivity: str = "public"
    capability: str | None = None


class AuthorityDecisionRead(BaseModel):
    action_type: str
    action_level: int
    requires_approval: bool
    sensitivity: str
    reason: str


class ActionRequestCreate(BaseModel):
    action_class: str
    actor: str = "system"
    agent: str | None = None
    project_id: str | None = None
    target: str | None = None
    sensitivity: str = "public"
    requested_capability: str | None = None
    payload_digest: str | None = None


class ActionRequestRead(BaseModel):
    id: str
    action_class: str
    actor: str
    agent: str | None = None
    project_id: str | None = None
    target: str | None = None
    sensitivity: str
    requested_capability: str | None = None
    payload_digest: str | None = None
    policy_decision: str
    approval_state: str
    execution_state: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    # AOS-AUTH-BOUNDARY-001: the operator who approved/rejected (audit trail).
    updated_by: str
    # AOS-AUTHORITY-HARDEN-001: binding + execution linkage + expiry.
    repository_id: str | None = None
    job_id: str | None = None
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


# AOS-EVIDENCE-API-001 (RFC-0018 Evidence Spine HTTP API) — thin DTOs over
# services/evidence.py. Enum-like fields (minted_by, source_type, truth_layer,
# ...) are plain `str` here (matching house style elsewhere in this file); the
# service layer coerces/validates them against the real enums.


class EvidenceSourceCreate(BaseModel):
    minted_by: str
    source_type: str
    title: str
    origin: str
    originator: str
    canonical_uri: str | None = None
    sensitivity: str = "internal"
    authority_domains: list[str] = Field(default_factory=list)
    access_policy_id: str | None = None
    status: str = "active"
    created_by: str = "system"


class EvidenceSourceRead(BaseModel):
    id: str
    project_id: str
    source_type: str
    title: str
    origin: str
    originator: str
    canonical_uri: str | None
    sensitivity: str
    authority_domains: list
    access_policy_id: str | None
    minted_by: str
    content_hash: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class EvidenceSourceVersionCreate(BaseModel):
    minted_by: str
    version_ref: str
    content_hash: str
    ingestion_method: str
    captured_at: datetime | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    supersedes_version_id: str | None = None
    parser_version: str | None = None
    created_by: str = "system"


class EvidenceSourceVersionRead(BaseModel):
    id: str
    source_id: str
    version_ref: str
    content_hash: str
    captured_at: datetime | None
    effective_from: datetime | None
    effective_until: datetime | None
    supersedes_version_id: str | None
    ingestion_method: str
    parser_version: str | None
    minted_by: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class EvidenceFragmentCreate(BaseModel):
    minted_by: str
    content_hash: str
    excerpt: str
    extraction_method: str
    locator: dict = Field(default_factory=dict)
    extraction_confidence: float = 0.0
    created_by: str = "system"


class EvidenceFragmentRead(BaseModel):
    id: str
    source_version_id: str
    locator: dict
    content_hash: str
    excerpt: str
    extraction_method: str
    extraction_confidence: float
    minted_by: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class ClaimCreate(BaseModel):
    minted_by: str
    truth_layer: str
    statement: str
    claim_type: str
    domain: str
    created_by: str
    derivation: dict
    scope: dict | None = None
    polarity: str = "affirming"
    confidence: float = 1.0
    materiality: str = "medium"
    status: str = "active"
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class ClaimRead(BaseModel):
    id: str
    project_id: str
    statement: str
    claim_type: str
    truth_layer: str
    domain: str
    scope: dict
    polarity: str
    confidence: float
    materiality: str
    valid_from: datetime | None
    valid_until: datetime | None
    derivation: dict
    minted_by: str
    decision_id: str | None
    content_hash: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class ClaimEvidenceLinkCreate(BaseModel):
    fragment_id: str
    minted_by: str
    relationship: str
    relevance: float = 1.0
    strength: str = "moderate"
    notes: str | None = None
    created_by: str = "system"


class ClaimEvidenceLinkRead(BaseModel):
    id: str
    claim_id: str
    fragment_id: str
    relationship: str
    relevance: float
    strength: str
    notes: str | None
    minted_by: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class ClaimRelationshipCreate(BaseModel):
    to_claim_id: str
    minted_by: str
    relationship: str
    notes: str | None = None
    created_by: str = "system"


class ClaimRelationshipRead(BaseModel):
    id: str
    from_claim_id: str
    to_claim_id: str
    relationship: str
    notes: str | None
    minted_by: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class ClaimDetailRead(ClaimRead):
    # GET /claims/{claim_id}: the claim plus its evidence links and claim
    # relationships (both directions — this claim as `from` or as `to`).
    evidence_links: list[ClaimEvidenceLinkRead] = Field(default_factory=list)
    relationships: list[ClaimRelationshipRead] = Field(default_factory=list)


class EvidenceConflictCreate(BaseModel):
    claim_ids: list[str]
    minted_by: str
    conflict_type: str
    materiality: str
    blocking_stages: list[str] = Field(default_factory=list)
    created_by: str = "system"


class EvidenceConflictRead(BaseModel):
    id: str
    project_id: str
    claim_ids: list
    conflict_type: str
    materiality: str
    resolution: str | None
    resolution_decision_id: str | None
    blocking_stages: list
    minted_by: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class EvidenceConflictResolve(BaseModel):
    # status transitions to "resolved" or "accepted_exception" (ConflictStatus);
    # not a content field (RFC-0018 leaves EvidenceConflict un-hashed/un-guarded).
    status: str
    resolution: str
    resolution_decision_id: str | None = None


class CorpusSnapshotCreate(BaseModel):
    source_version_ids: list[str] = Field(default_factory=list)
    purpose: str
    repository_refs: list[dict] = Field(default_factory=list)
    created_by: str = "system"


class CorpusSnapshotRead(BaseModel):
    id: str
    project_id: str
    source_version_ids: list
    repository_refs: list
    claim_set_hash: str | None
    purpose: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


# AOS-GENOME-API-001 (RFC-0019 §16 HTTP surface) — thin DTOs over
# services/genome.py. Enum-like fields (state_view, classification, ...) are
# plain `str` here (house style, matching the Evidence Spine DTOs above); the
# service layer coerces/validates them against the real
# aos_core.foundation.enums values.


class GenomeGenerateRequest(BaseModel):
    state_view: str
    corpus_snapshot_id: str | None = None
    generated_by: str | None = None
    created_by: str = "system"


class GenomeSnapshotRead(BaseModel):
    id: str
    project_id: str
    corpus_snapshot_id: str | None
    state_view: str
    summary: str
    coverage: float
    aggregate_confidence: float
    open_question_count: int
    critical_conflict_count: int
    generated_by: str
    approved_by: str | None
    approved_at: datetime | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class GenomeTraitRead(BaseModel):
    id: str
    genome_snapshot_id: str
    dimension: str
    trait_key: str
    value: object | None
    value_type: str
    classification: str
    confidence: float
    stability: str
    criticality: str
    rationale: str
    source_methods: list
    human_locked: bool
    supporting_claim_ids: list[str] = Field(default_factory=list)
    opposing_claim_ids: list[str] = Field(default_factory=list)
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class SystemArchetypeRead(BaseModel):
    id: str
    genome_snapshot_id: str
    name: str
    tier: str
    confidence: float
    trait_ids: list
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class GenomeSnapshotDetailRead(GenomeSnapshotRead):
    # GET /genomes/{genome_id}: the snapshot plus its traits (each with
    # supporting/opposing claim ids) and rolled-up archetypes.
    traits: list[GenomeTraitRead] = Field(default_factory=list)
    archetypes: list[SystemArchetypeRead] = Field(default_factory=list)


class GenomeReviewRequest(BaseModel):
    reviewer: str = "system"


class GenomeApproveRequest(BaseModel):
    approver: str
    rationale: str | None = None


class OpenQuestionRead(BaseModel):
    id: str
    project_id: str
    genome_snapshot_id: str | None
    question: str
    affected_dimensions: list
    affected_foundation_domains: list
    materiality: str
    reason: str
    answer_type: str
    answer_claim_id: str | None
    minted_by: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class GenomeDeltaRead(BaseModel):
    id: str
    project_id: str
    from_snapshot_id: str
    to_snapshot_id: str
    changes: dict
    summary: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class ApprovalRecordRead(BaseModel):
    id: str
    project_id: str | None = None
    actor: str | None = None
    agent: str | None = None
    tool: str | None = None
    action_level: int
    requested_capability: str | None = None
    target: str | None = None
    reason: str | None = None
    approval_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# AOS-FOUNDATION-API-001 (RFC-0020 design §16 HTTP surface) — thin DTOs over
# services/foundation.py. Enum-like fields (state, requirement_type, domain,
# priority, status, criterion, ...) are plain `str` here (house style, matching
# the Evidence Spine / Genome DTOs above); the service layer coerces/validates
# them against the real aos_core.foundation.enums values. Every action route
# (compile-requirements/generate-candidates/evaluate-eligibility/score) takes a
# single `actor` field — the API-level name for whichever `created_by`/`actor`
# kwarg the matching services/foundation.py function expects.


class FoundationRunCreate(BaseModel):
    target_genome_snapshot_id: str
    corpus_snapshot_id: str | None = None
    created_by: str = "system"


class FoundationRunActionRequest(BaseModel):
    actor: str = "system"


class FoundationSelectionRunRead(BaseModel):
    id: str
    project_id: str
    target_genome_snapshot_id: str
    corpus_snapshot_id: str | None
    state: str
    summary: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class FoundationRequirementRead(BaseModel):
    id: str
    selection_run_id: str
    genome_snapshot_id: str | None
    requirement_type: str
    domain: str
    statement: str
    priority: str
    weight: float
    veto_if_unsatisfied: bool
    verification_method: str
    claim_ids: list
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class FoundationCandidateCreate(BaseModel):
    name: str
    summary: str = ""
    architecture_style: list[str] = Field(default_factory=list)
    reversibility: str = "medium"
    recommendation_ref: str | None = None
    created_by: str = "system"


class FoundationCandidateRead(BaseModel):
    id: str
    selection_run_id: str
    name: str
    summary: str
    architecture_style: list
    recommendation_ref: str | None
    assumption_claim_ids: list
    satisfied_requirement_ids: list
    unsatisfied_requirement_ids: list
    hard_constraint_violations: list
    reversibility: str
    lock_in_profile: dict
    estimated_cost: dict
    estimated_effort: dict
    score_summary: dict
    confidence: float
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class FoundationElementCreate(BaseModel):
    domain: str
    title: str
    decision: str
    verification_method: str
    rationale: str = ""
    technology_refs: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    alternatives_rejected: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    created_by: str = "system"


class FoundationElementRead(BaseModel):
    id: str
    candidate_id: str
    domain: str
    title: str
    decision: str
    rationale: str
    technology_refs: list
    claim_ids: list
    requirement_ids: list
    alternatives_rejected: list
    tradeoffs: list
    risks: list
    verification_method: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class FoundationScoreRead(BaseModel):
    id: str
    candidate_id: str
    criterion: str
    raw_score: float
    weight: float
    confidence: float
    uncertainty_penalty: float
    adjusted_score: float
    rationale: str
    supporting_claim_ids: list
    evaluation_ref: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class FoundationRunDetailRead(FoundationSelectionRunRead):
    # GET /foundation-runs/{run_id}: the run plus its compiled requirements and
    # generated/authored candidates.
    requirements: list[FoundationRequirementRead] = Field(default_factory=list)
    candidates: list[FoundationCandidateRead] = Field(default_factory=list)


class FoundationCandidateDetailRead(FoundationCandidateRead):
    # GET /candidates/{candidate_id}: the candidate plus its elements and its
    # design §10.3 score vector (FoundationScore rows — never a lone scalar).
    elements: list[FoundationElementRead] = Field(default_factory=list)
    scores: list[FoundationScoreRead] = Field(default_factory=list)
