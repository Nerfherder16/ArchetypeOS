from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator
from pgvector.sqlalchemy import Vector
from .config import EMBEDDING_DIM
from .database import Base

# RFC-0010: a dialect-variant embedding column type. On postgresql it is a real
# pgvector ``VECTOR(384)`` (indexable with cosine ops); on sqlite it degrades to a
# benign JSON column so ``Base.metadata.create_all`` — which every hermetic
# CI/unit test runs on sqlite — emits no ``VECTOR`` DDL (sqlite would reject it).
# The sqlite variant is always NULL and never queried; the semantic path is gated
# on ``dialect == "postgresql"``.
EmbeddingColumn = Vector(EMBEDDING_DIM).with_variant(JSON(), "sqlite")


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
    # AOS-SELFHEAL (per-project MVP): opt this project into the nightly audit loop.
    # The dispatcher runs the repo-state (coherence) probe against every enabled
    # project's repo and posts a heartbeat keyed to the project. Default off.
    audits_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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
    # AOS-JOBS-RELIABILITY-001 Slice 3: a unique job_id makes the note the single
    # output of its originating job, so a redelivered research job cannot create a
    # duplicate note (finding P0-3). NULL job_id (notes created outside a job) is
    # exempt — Postgres treats NULLs as distinct.
    __table_args__ = (UniqueConstraint("job_id", name="uq_research_notes_job_id"),)

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    findings: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    freshness: Mapped[str | None] = mapped_column(String(128))
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    job_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("jobs.id"), index=True)


class ResearchPlan(AuditMixin, Base):
    """A persisted, multi-phase research plan (AOS-RESEARCH-003, Finding 15).

    The plan is recorded BEFORE any source is fetched: it captures the question,
    its sensitivity, the source types the investigation requires, the search
    queries to run, the verification steps to apply, and the synthesis policy.
    A ResearchRun (later slice) executes a plan and records what it found. Note:
    ``plan_status`` (not ``status``) avoids clashing with AuditMixin.status.
    """

    __tablename__ = "research_plans"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    plan_status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    required_source_types: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    search_queries: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    verification_steps: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    synthesis_policy: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)


class ResearchRun(AuditMixin, Base):
    """One execution of a :class:`ResearchPlan` (AOS-RESEARCH-003, criteria 2-5).

    Records the phases it ran (plan → search → fetch → verify → synthesize), every
    source it considered with an accept/reject decision AND a reason, the findings
    (each citing an accepted source), the conflicting evidence kept visible (not
    flattened), a calibrated confidence, and the open questions the run could not
    resolve (which the executor turns into follow-up plans). ``run_status`` (not
    ``status``) avoids the AuditMixin.status clash; ``job_id`` links the async job.
    """

    __tablename__ = "research_runs"
    # AOS-JOBS-RELIABILITY-001 Slice 3: one run per originating job (finding P0-3).
    __table_args__ = (UniqueConstraint("job_id", name="uq_research_runs_job_id"),)

    plan_id: Mapped[str] = mapped_column(GUID(), ForeignKey("research_plans.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    job_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("jobs.id"), index=True)
    run_status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    phases: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    sources: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    findings: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    conflicts: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    open_questions: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class AuditHeartbeat(AuditMixin, Base):
    """The last-run heartbeat of a nightly self-learn probe (observability).

    Each probe (conflict / toil / coherence / session-pain / ...) posts a heartbeat
    on every run — ``clean`` / ``findings`` / ``failed`` — so the operator can tell
    a clean night from a MISSED run without reading logs. One row per routine
    (upserted), carrying the run day and, when it opened a review PR, its url.
    ``heartbeat_status`` (not ``status``) avoids the AuditMixin.status clash.
    """

    __tablename__ = "audit_heartbeats"
    # One row per (routine, project). A global routine (the ArchetypeOS self-audit)
    # has project_id NULL; a per-project audit scopes the same routine to a project
    # so their heartbeats never collide. project_id is a soft reference (no FK) —
    # a status board must survive a probe posting for a since-deleted project.
    #
    # AOS-NODE-CONSTRAINTS-001 (finding P1-3): the composite unique above does NOT
    # constrain the global rows, because SQL treats NULLs as distinct — two
    # (routine, NULL) inserts would both succeed. A partial unique index on
    # ``routine WHERE project_id IS NULL`` enforces the one-global-row-per-routine
    # invariant the service relies on.
    __table_args__ = (
        UniqueConstraint("routine", "project_id", name="uq_audit_heartbeats_routine_project"),
        Index(
            "uq_audit_heartbeats_routine_global",
            "routine",
            unique=True,
            sqlite_where=text("project_id IS NULL"),
            postgresql_where=text("project_id IS NULL"),
        ),
    )

    routine: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(GUID(), nullable=True, index=True)
    heartbeat_status: Mapped[str] = mapped_column(String(32), nullable=False)
    day: Mapped[str] = mapped_column(String(32), nullable=False)
    pr_url: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)


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

    project_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    vault_path: Mapped[str] = mapped_column(Text, nullable=False)
    page_type: Mapped[str] = mapped_column(String(128), nullable=False)
    validation_state: Mapped[str] = mapped_column(String(128), default="raw", nullable=False)
    source_refs: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128))
    # RFC-0010 semantic index: nullable pgvector embedding (NULL on sqlite / the
    # deterministic tier → lexical fallback). Populated by ``distill_repository``
    # only when a real embedder returns a vector (AOS-EMBED-002).
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingColumn, nullable=True)


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
    # AOS-JOBS-RELIABILITY-001 Slice 2 (RFC-0014): a worker takes a time-boxed lease
    # when it claims a job. If the worker dies, the lease expires and the reaper
    # recovers the job — closing the crash-recovery half of finding P0-1.
    claimed_by: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobOutbox(AuditMixin, Base):
    """Transactional outbox for job delivery (AOS-JOBS-RELIABILITY-001, RFC-0014).

    Written in the SAME transaction as its ``Job`` so origination is atomic: a
    ``Job`` never exists without a delivery intent. A dispatcher publishes
    undelivered rows to the Redis queue and stamps ``delivered_at``; a Redis
    outage after the job commits can therefore no longer orphan a queued job —
    the row stays undelivered and is retried, rather than lost (finding P0-1).
    """

    __tablename__ = "job_outbox"

    job_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("jobs.id"), nullable=False, unique=True, index=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Schedule(AuditMixin, Base):
    __tablename__ = "schedules"

    project_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


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
    # AOS-JOBS-RELIABILITY-001 Slice 3: one digest per originating job (finding P0-3).
    __table_args__ = (UniqueConstraint("job_id", name="uq_nightly_digests_job_id"),)

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    digest_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    recommendations: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    repeated_tasks: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    job_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("jobs.id"), index=True)


class CouncilReview(AuditMixin, Base):
    __tablename__ = "council_reviews"
    # AOS-JOBS-RELIABILITY-001 Slice 3: one review per originating job (finding P0-3).
    __table_args__ = (UniqueConstraint("job_id", name="uq_council_reviews_job_id"),)

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    question: Mapped[str | None] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String(64), default="Insufficient evidence", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    agreements: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    disagreements: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    unsupported_claims: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    follow_up: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(128))
    job_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("jobs.id"), index=True)

    agent_outputs: Mapped[list["CouncilAgentOutput"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class CouncilAgentOutput(AuditMixin, Base):
    __tablename__ = "council_agent_outputs"

    # Note: the agent workflow status (Waiting / Running / Needs Evidence /
    # Blocked / Complete / Escalated / Rejected) is carried by the inherited
    # AuditMixin.status column (String(64), indexed) — set explicitly by the
    # council service — so there is no duplicate status column.
    review_id: Mapped[str] = mapped_column(GUID(), ForeignKey("council_reviews.id"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    findings: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    concerns: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Which model produced this agent's output — the diversity signal for a
    # multi-model council (AOS-LLM-EVAL-001). Nullable: legacy rows + single-model
    # councils may leave it empty.
    agent_model: Mapped[str | None] = mapped_column(String(128))

    review: Mapped["CouncilReview"] = relationship(back_populates="agent_outputs")


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


class UsageEvent(AuditMixin, Base):
    """LLM usage ledger row (AOS-USAGE-001).

    One row per reasoned ``generate()`` (the deterministic CI floor records
    none). ``tier`` is derived from the provider name + config
    (claude / local / free); tokens/cost carry the provider's real numbers, or an
    explicitly ``estimated`` fallback. Local-first: the ledger starts recording
    from deploy (no historical backfill). ``ts`` is the moment of the call and is
    the column the usage summary windows on.
    """

    __tablename__ = "usage_events"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str | None] = mapped_column(String(255))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    estimated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agent: Mapped[str | None] = mapped_column(String(128))
    session: Mapped[str | None] = mapped_column(String(128))
    context: Mapped[str | None] = mapped_column(String(128))


class VoiceInboxItem(AuditMixin, Base):
    """A review-first draft produced by a Voice Command Center turn (AOS-VOICE-001).

    Voice mode captures and prepares work; it never performs destructive actions
    directly (VOICE_COMMAND_CENTER.md). Every voice turn lands here as a draft for
    later review/approval in the dashboard. ``project_id`` links a resolved project
    (nullable — a turn may not name one); ``detected_project`` keeps the raw guess.
    """

    __tablename__ = "voice_inbox_items"

    project_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("projects.id"), index=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    detected_intent: Mapped[str] = mapped_column(String(64), default="idea_capture", nullable=False, index=True)
    detected_project: Mapped[str | None] = mapped_column(String(255))
    suggested_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    required_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    review_state: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    source_device: Mapped[str] = mapped_column(String(128), default="unknown", nullable=False)
    reply_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # AOS-VOICE-005: when an item is approved, its intent may promote it into a
    # concrete draft entity (research_note / decision). These record that linkage;
    # NULL until a mapped intent is approved on an item with a resolved project.
    promoted_kind: Mapped[str | None] = mapped_column(String(64))
    promoted_id: Mapped[str | None] = mapped_column(GUID())


class Node(AuditMixin, Base):
    """A registered execution node in the distributed runtime (AOS-NODE-001).

    The control plane routes capability-declared work to eligible nodes. Nodes are
    read-only by default (``write_access=False``) and carry a ``max_sensitivity``
    ceiling so private work is never routed to a node that should not see it.
    """

    __tablename__ = "nodes"

    # AOS-NODE-CONSTRAINTS-001 (finding P1-3): a node's name is its logical identity;
    # a unique constraint stops a concurrent register-by-name race from creating
    # duplicate logical nodes.
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    node_type: Mapped[str] = mapped_column(String(64), default="worker", nullable=False)
    endpoint: Mapped[str | None] = mapped_column(Text)
    # Operational health, distinct from AuditMixin.status (record lifecycle).
    node_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False, index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_sensitivity: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    write_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    capabilities: Mapped[list["NodeCapability"]] = relationship(
        back_populates="node", cascade="all, delete-orphan"
    )


class NodeCapability(AuditMixin, Base):
    __tablename__ = "node_capabilities"
    # AOS-NODE-CONSTRAINTS-001 (finding P1-3): a node declares each capability once.
    __table_args__ = (
        UniqueConstraint("node_id", "capability", name="uq_node_capabilities_node_capability"),
    )

    node_id: Mapped[str] = mapped_column(GUID(), ForeignKey("nodes.id"), nullable=False, index=True)
    capability: Mapped[str] = mapped_column(String(128), nullable=False)
    capability_version: Mapped[str | None] = mapped_column(String(64))
    capability_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    limits: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)

    node: Mapped["Node"] = relationship(back_populates="capabilities")


class NodeHeartbeat(AuditMixin, Base):
    __tablename__ = "node_heartbeats"

    node_id: Mapped[str] = mapped_column(GUID(), ForeignKey("nodes.id"), nullable=False, index=True)
    health: Mapped[str] = mapped_column(String(32), default="healthy", nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)


class Connector(AuditMixin, Base):
    """A governed external connection in the connector registry (AOS-CONNECTOR-001).

    Connectors define where data goes, so ArchetypeOS governs them as first-class
    assets (eval Finding 9). The static governance attributes (type/tier/privacy
    class/egress/browser-exposed/quota) come from a declarative catalog; ``configured``
    is recomputed from settings on each sync (never hand-maintained), and health is
    recorded by a probe into ``last_health_status``/``last_error``.
    """

    __tablename__ = "connectors"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    connector_type: Mapped[str] = mapped_column(String(64), default="llm", nullable=False)
    tier: Mapped[str] = mapped_column(String(64), default="external", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Derived from settings on every sync: does this connector have its config?
    configured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # "private_ok" (may receive private data) vs "public_only" (must not).
    privacy_class: Mapped[str] = mapped_column(String(32), default="public_only", nullable=False)
    # Does data leave the local/tailnet network for this connector?
    egress_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Is a credential/URL for this connector shipped to the browser (e.g. VITE_*)?
    browser_exposed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quota_policy: Mapped[str] = mapped_column(String(128), default="unmetered", nullable=False)
    # Operational health, distinct from AuditMixin.status (record lifecycle).
    last_health_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False, index=True)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
