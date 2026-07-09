from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    name: str
    slug: str | None = None
    description: str | None = None


class ProjectRead(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
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


class RepositoryRead(BaseModel):
    id: str
    project_id: str
    name: str
    local_path: str
    default_branch: str | None
    remote_url: str | None
    is_read_only: bool
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

    model_config = {"from_attributes": True}


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
