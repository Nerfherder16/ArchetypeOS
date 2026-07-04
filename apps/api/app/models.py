from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator
from .database import Base


class GUID(TypeDecorator):
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(String(36))


class JSONField(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class AuditMixin:
    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_id)
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    meta: Mapped[dict] = mapped_column("metadata", JSONField(), default=dict, nullable=False)


class Project(AuditMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("slug", name="uq_projects_slug"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    repositories: Mapped[list["Repository"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Repository(AuditMixin, Base):
    __tablename__ = "repositories"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    default_branch: Mapped[str | None] = mapped_column(String(255))
    remote_url: Mapped[str | None] = mapped_column(Text)
    is_read_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="repositories")
    dna: Mapped["RepositoryDNA | None"] = relationship(back_populates="repository", cascade="all, delete-orphan")


class RepositoryDNA(AuditMixin, Base):
    __tablename__ = "repository_dna"

    repository_id: Mapped[str] = mapped_column(GUID(), ForeignKey("repositories.id"), nullable=False, unique=True, index=True)
    purpose: Mapped[str | None] = mapped_column(Text)
    maturity: Mapped[str | None] = mapped_column(String(128))
    language_mix: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)
    package_managers: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    frameworks: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    runtime_services: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    deployment_files: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    risk_flags: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    scan_summary: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="dna")


class ArchitectureNode(AuditMixin, Base):
    __tablename__ = "architecture_nodes"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("architecture_nodes.id"), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    risks: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    related_decision_ids: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    manual_correction: Mapped[str | None] = mapped_column(Text)


class ArchitectureEdge(AuditMixin, Base):
    __tablename__ = "architecture_edges"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    from_node_id: Mapped[str] = mapped_column(GUID(), ForeignKey("architecture_nodes.id"), nullable=False, index=True)
    to_node_id: Mapped[str] = mapped_column(GUID(), ForeignKey("architecture_nodes.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    manual_correction: Mapped[str | None] = mapped_column(Text)


class Decision(AuditMixin, Base):
    __tablename__ = "decisions"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str | None] = mapped_column(Text)
    alternatives: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    tradeoffs: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    consequences: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ResearchNote(AuditMixin, Base):
    __tablename__ = "research_notes"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    findings: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    freshness: Mapped[str | None] = mapped_column(String(128))
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class Recommendation(AuditMixin, Base):
    __tablename__ = "recommendations"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)
    alternatives: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    pros: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    cons: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    risk: Mapped[str | None] = mapped_column(Text)
    effort: Mapped[str | None] = mapped_column(String(128))
    dependencies: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    acceptance_criteria: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class Artifact(AuditMixin, Base):
    __tablename__ = "artifacts"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    job_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("jobs.id"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))
    checksum: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)


class KnowledgePage(AuditMixin, Base):
    __tablename__ = "knowledge_pages"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    vault_path: Mapped[str] = mapped_column(Text, nullable=False)
    page_type: Mapped[str] = mapped_column(String(128), nullable=False)
    validation_state: Mapped[str] = mapped_column(String(128), default="raw", nullable=False)
    source_refs: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128))


class Job(AuditMixin, Base):
    __tablename__ = "jobs"

    project_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("projects.id"), index=True)
    repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    job_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSONField())
    error: Mapped[str | None] = mapped_column(Text)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Agent(AuditMixin, Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    agent_type: Mapped[str] = mapped_column(String(128), nullable=False)
    capabilities: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    authority_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Engine(AuditMixin, Base):
    __tablename__ = "engines"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    engine_type: Mapped[str] = mapped_column(String(128), nullable=False)
    capabilities: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    inputs: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    outputs: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)


class Evaluation(AuditMixin, Base):
    __tablename__ = "evaluations"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    evaluation_type: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    findings: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)


class Risk(AuditMixin, Base):
    __tablename__ = "risks"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(64))
    likelihood: Mapped[str | None] = mapped_column(String(64))
    mitigation: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(128))


class Benchmark(AuditMixin, Base):
    __tablename__ = "benchmarks"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    benchmark_type: Mapped[str | None] = mapped_column(String(128))
    metric: Mapped[str | None] = mapped_column(String(128))
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(64))
    environment: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)


class Experiment(AuditMixin, Base):
    __tablename__ = "experiments"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    hypothesis: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    conclusion: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)


class NightlyDigest(AuditMixin, Base):
    __tablename__ = "nightly_digests"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    digest_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    recommendations: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    repeated_tasks: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)


class AuthorityGrant(AuditMixin, Base):
    __tablename__ = "authority_grants"

    project_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("projects.id"), index=True)
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    capability: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[str | None] = mapped_column(Text)
    authority_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approver: Mapped[str | None] = mapped_column(String(128))
    reason: Mapped[str | None] = mapped_column(Text)


class ApprovalRecord(AuditMixin, Base):
    __tablename__ = "approval_records"

    project_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("projects.id"), index=True)
    authority_grant_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("authority_grants.id"), index=True)
    actor: Mapped[str | None] = mapped_column(String(128))
    agent: Mapped[str | None] = mapped_column(String(128))
    tool: Mapped[str | None] = mapped_column(String(128))
    action_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requested_capability: Mapped[str | None] = mapped_column(String(255))
    target: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    approval_status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False)
    output: Mapped[dict | None] = mapped_column(JSONField())
    rollback_notes: Mapped[str | None] = mapped_column(Text)
