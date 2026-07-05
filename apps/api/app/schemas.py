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
    language_mix: dict
    package_managers: list
    deployment_files: list
    risk_flags: list
    scan_summary: dict
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
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
