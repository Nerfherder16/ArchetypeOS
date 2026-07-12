from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, event, inspect, text
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
    # AOS-AUTHORITY-HARDEN-001: the repository's data-sensitivity policy. Egress of
    # its content (e.g. distillation to a model provider) derives the authority
    # envelope's sensitivity from HERE, instead of hardcoding "public" — a private
    # repository's content therefore requires approval to egress.
    sensitivity: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="repositories")
    dna: Mapped["RepositoryDNA | None"] = relationship(back_populates="repository", cascade="all, delete-orphan")
    capabilities: Mapped[list["RepositoryCapability"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )


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


class RepositoryCapability(AuditMixin, Base):
    """A single named, reuse-oriented capability extracted from a repository (RFC-0013).

    Distillation's reasoned tier already names the concrete, reusable capabilities a
    *different* project could borrow (``{name, description, provenance}``); Slice 1
    only rendered them into the vault markdown. This table persists them at
    **capability granularity** so the Transfer Engine can match a reuse need against a
    *single capability's* embedding (high cosine) instead of a whole-product blob
    (noise) — the granularity fix RFC-0013 identifies. One row per capability; a repo
    has several. ``embedding`` reuses the RFC-0010 dialect-variant column (real
    ``VECTOR(384)`` on postgres, benign NULL JSON on sqlite), embedding
    ``name + " " + description``. Rows are replaced wholesale on every re-distill
    (the capability set is a pure function of the current source), so no per-row
    version drift accumulates.
    """

    __tablename__ = "repository_capabilities"
    __table_args__ = (
        Index("ix_repository_capabilities_repository_id", "repository_id"),
    )

    repository_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("repositories.id"), nullable=False
    )
    # The vault page this capability was rendered into — evidence provenance; nullable
    # so a capability can outlive a page row without a hard FK failure.
    knowledge_page_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("knowledge_pages.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # File path(s) the capability lives in — every capability is grounded to at least
    # one cited file (``_drop_uncited_capabilities``); this is what a recommendation
    # points a borrower at.
    provenance: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingColumn, nullable=True)

    repository: Mapped[Repository] = relationship(back_populates="capabilities")


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


class ImplementationPlan(AuditMixin, Base):
    """A governed, draft-first implementation plan for an approved Decision.

    RFC-0015 Design §1 (AOS-BUILD-PLAN-001): the right-of-decision half of the
    Build Intelligence loop. Drafted only from a ``Decision`` whose ``status``
    is already ``approved`` (``services/build_plan.py:plan_from_decision``);
    status rides ``AuditMixin.status`` with the same vocab as ``Decision``
    (``draft``/``approved``/``rejected``/``superseded``) so the governance gate
    is uniform. **No job_type, no execution** — that is AOS-BUILD-EXEC-001.
    """

    __tablename__ = "implementation_plans"

    decision_id: Mapped[str] = mapped_column(GUID(), ForeignKey("decisions.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str | None] = mapped_column(Text)
    tasks: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    acceptance_criteria: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    verification_requirements: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    target_repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    risk: Mapped[str | None] = mapped_column(Text)
    effort: Mapped[str | None] = mapped_column(String(128))
    evidence: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
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
    # AOS-JOB-FENCING-001: an opaque fencing token minted on every successful claim.
    # ``claimed_by`` alone is not a fence — a worker id (``hostname:pid``) can recur,
    # and a stale worker that lost its lease could still complete/fail a job another
    # worker has since re-claimed. Every worker-side state transition (renew, complete,
    # fail, retry) is a compare-and-swap on this token, so a claim reclaimed by the
    # reaper or another worker (which mints a NEW token) invalidates the old owner.
    claim_token: Mapped[str | None] = mapped_column(String(64))
    # AOS-NODE-EXECUTION-001: routing binds a job to the node allowed to run it.
    # ``required_capability``/``sensitivity``/``requires_write`` are the execution
    # requirements DERIVED SERVER-SIDE at origination (from the job registry, never
    # trusted from the client). ``assigned_node_id`` is the node routing chose;
    # ``routing_status`` is ``unrouted`` → ``routed`` / ``no_eligible_node``;
    # ``routing_explanation`` is the deterministic Control-Tower reason; ``routed_at``
    # stamps the decision. A worker may only claim a job assigned to its own node.
    required_capability: Mapped[str | None] = mapped_column(String(128))
    sensitivity: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    requires_write: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_node_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("nodes.id"), index=True)
    routing_status: Mapped[str] = mapped_column(String(32), default="unrouted", nullable=False)
    routing_explanation: Mapped[str | None] = mapped_column(Text)
    routed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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


class ScheduleFire(AuditMixin, Base):
    """One materialized firing of a :class:`Schedule` (AOS-SCHEDULER-RELIABILITY-001).

    Unique on ``(schedule_id, nominal_fire_at)`` so a schedule's occurrence fires
    EXACTLY once — even across scheduler replicas or a crash-and-retry: the second
    attempt hits the unique constraint and is skipped instead of enqueuing a
    duplicate job (finding P0-2). ``nominal_fire_at`` is the scheduled time, not
    the wall-clock tick, so cadence is anchored and cannot drift forward.
    """

    __tablename__ = "schedule_fires"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id", "nominal_fire_at", name="uq_schedule_fires_schedule_nominal"
        ),
    )

    schedule_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("schedules.id"), nullable=False, index=True
    )
    nominal_fire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    job_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("jobs.id"), index=True)


class ActionRequest(AuditMixin, Base):
    """The mandatory execution envelope for a high-impact action (AOS-AUTHORITY-ENVELOPE-001, P0-6).

    The authority evaluator was advisory — nothing compelled an execution path
    through it. Now a high-impact action (write/deploy/destructive/sensitive egress)
    must be created here first: ``request_action`` records it and runs the policy;
    approval flips ``execution_state`` to ``authorized``; and the execution
    chokepoint (``enqueue_job``) refuses to run a high-impact action without an
    authorized envelope. Low-impact actions auto-authorize.
    """

    __tablename__ = "action_requests"

    action_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    agent: Mapped[str | None] = mapped_column(String(128))
    project_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("projects.id"), index=True)
    # AOS-AUTHORITY-HARDEN-001: bind the envelope to the concrete target so an
    # approval for one repository/payload cannot authorize another.
    repository_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("repositories.id"), index=True)
    target: Mapped[str | None] = mapped_column(Text)
    sensitivity: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    requested_capability: Mapped[str | None] = mapped_column(String(128))
    payload_digest: Mapped[str | None] = mapped_column(String(128))
    # allow | needs_approval
    policy_decision: Mapped[str] = mapped_column(String(32), default="allow", nullable=False)
    # pending | approved | rejected | auto_approved
    approval_state: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    # requested | authorized | executed | rejected
    execution_state: Mapped[str] = mapped_column(String(32), default="requested", nullable=False, index=True)
    # AOS-AUTHORITY-HARDEN-001: execution linkage (which job consumed this envelope)
    # and an expiry so a pending/authorized envelope does not live forever.
    job_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("jobs.id"), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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


class NodeCredential(AuditMixin, Base):
    """A per-node service credential (AOS-NODE-IDENTITY-001, finding P0-5).

    Issued during operator-approved enrollment; only the SHA-256 hash is stored.
    A node presents its token on heartbeat/claim so an unauthenticated client can
    no longer report false health or impersonate a node. One live credential per
    node (unique ``node_id``); ``revoked_at``/``rotated_at`` support rotation and
    revocation.
    """

    __tablename__ = "node_credentials"

    node_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("nodes.id"), nullable=False, unique=True, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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


# ---------------------------------------------------------------------------
# Evidence spine (RFC-0018, AOS-EVIDENCE-MODELS-001) — the claim-centric
# evidence graph as first-class, queryable, versioned tables. Columns store
# ``aos_core.foundation.enums``/``aos_core.sensitivity`` values as ``String``;
# JSON only for the contracts' open structures (locator/scope/derivation/
# authority_domains/claim_ids/blocking_stages/affected_*). The ONLY write path
# is ``services/evidence.py`` — it builds each row through its RFC-0017
# Pydantic contract first (C1/C3 validators run there too, defense in depth),
# computes ``content_hash``/``claim_set_hash`` (C4), then persists the ORM row.
# A ``before_update`` guard below (``_assert_content_immutable``) refuses an
# UPDATE that touches a content field on any of the five immutable row kinds
# (Source/SourceVersion/Fragment/Claim/CorpusSnapshot) — status/annotation
# transitions (e.g. a conflict's status, a claim's status) are unaffected.
# ---------------------------------------------------------------------------


class EvidenceSource(AuditMixin, Base):
    """design §4.2 — a logical evidence source (repo, doc, diagram, ...).

    ``status`` (AuditMixin) carries ``SourceStatus`` (active/superseded/
    withdrawn/unavailable). The RFC-0017 contract has no ``content_hash``
    field for this entity, so this column is a pure C4 audit hash of the
    contract's content projection — computed by ``services/evidence.py``.
    """

    __tablename__ = "evidence_sources"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    origin: Mapped[str] = mapped_column(String(64), nullable=False)
    originator: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_uri: Mapped[str | None] = mapped_column(Text)
    sensitivity: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    authority_domains: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    access_policy_id: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    minted_by: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)


class EvidenceSourceVersion(AuditMixin, Base):
    """design §4.3 — append-only; a correction creates a NEW version row.

    ``content_hash`` here is the RFC-0017 contract's own field — the hash of
    the underlying source *content* (e.g. a file/blob checksum), supplied by
    the caller at ingestion time — distinct from the C4 audit-hash mechanism
    (this entity's contract already carries its content anchor, so no second
    hash is derived from the row).
    """

    __tablename__ = "evidence_source_versions"

    source_id: Mapped[str] = mapped_column(GUID(), ForeignKey("evidence_sources.id"), nullable=False, index=True)
    version_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_version_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("evidence_source_versions.id"), index=True
    )
    ingestion_method: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(128))
    minted_by: Mapped[str] = mapped_column(String(32), nullable=False)


class EvidenceFragment(AuditMixin, Base):
    """design §4.4 — append-only; a locatable slice of a source version.

    ``content_hash`` is the contract's own field (hash of the extracted
    excerpt), caller-supplied — same rationale as ``EvidenceSourceVersion``.
    """

    __tablename__ = "evidence_fragments"

    source_version_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("evidence_source_versions.id"), nullable=False, index=True
    )
    locator: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    minted_by: Mapped[str] = mapped_column(String(32), nullable=False)


class Claim(AuditMixin, Base):
    """design §4.5 — the central reasoning primitive (RFC-0016 C1/C3 apply).

    ``status`` (AuditMixin) carries ``ClaimStatus`` (active/disputed/
    superseded/rejected/resolved). ``decision_id`` is the C1 link: only
    ``services.evidence.project_decided_claim`` sets it, from an **approved**
    ``Decision``. The contract has no ``content_hash`` field, so this column
    is a pure C4 audit hash of the contract's content projection.
    """

    __tablename__ = "claims"
    __table_args__ = (Index("ix_claims_project_id_truth_layer", "project_id", "truth_layer"),)

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(64), nullable=False)
    truth_layer: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)
    polarity: Mapped[str] = mapped_column(String(32), default="affirming", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    materiality: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    derivation: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)
    minted_by: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("decisions.id"), index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)


class ClaimEvidenceLink(AuditMixin, Base):
    """design §4.6 — evidence has a relationship to the claim, not a bare attachment.

    Junction table: surrogate id (AuditMixin) + a unique constraint on
    ``(claim_id, fragment_id, relationship)`` (RFC-0018 open question #2,
    resolved). No ``content_hash`` — junction rows carry no independent content.
    """

    __tablename__ = "claim_evidence_links"
    __table_args__ = (
        UniqueConstraint("claim_id", "fragment_id", "relationship", name="uq_claim_evidence_links_claim_fragment_rel"),
    )

    claim_id: Mapped[str] = mapped_column(GUID(), ForeignKey("claims.id"), nullable=False, index=True)
    fragment_id: Mapped[str] = mapped_column(GUID(), ForeignKey("evidence_fragments.id"), nullable=False, index=True)
    relationship: Mapped[str] = mapped_column(String(32), nullable=False)
    relevance: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    strength: Mapped[str] = mapped_column(String(32), default="moderate", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    minted_by: Mapped[str] = mapped_column(String(32), nullable=False)


class ClaimRelationship(AuditMixin, Base):
    """design §4.8 — the claim graph's edges (supports/contradicts/supersedes/...)."""

    __tablename__ = "claim_relationships"

    from_claim_id: Mapped[str] = mapped_column(GUID(), ForeignKey("claims.id"), nullable=False, index=True)
    to_claim_id: Mapped[str] = mapped_column(GUID(), ForeignKey("claims.id"), nullable=False, index=True)
    relationship: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    minted_by: Mapped[str] = mapped_column(String(32), nullable=False)


class EvidenceConflict(AuditMixin, Base):
    """design §4.9 — a contradiction that remains visible until explicitly resolved.

    ``status`` (AuditMixin) carries ``ConflictStatus``; ``services.evidence.
    open_conflict`` sets it to ``open`` (overriding AuditMixin's ``active``
    default) so a conflict stays visible until a later, explicit resolution
    transition sets ``status="resolved"``/``resolution_decision_id`` (the C1
    decision link for the resolution).
    """

    __tablename__ = "evidence_conflicts"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    claim_ids: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(64), nullable=False)
    materiality: Mapped[str] = mapped_column(String(32), nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolution_decision_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("decisions.id"), index=True)
    blocking_stages: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    minted_by: Mapped[str] = mapped_column(String(32), nullable=False)


class CorpusSnapshot(AuditMixin, Base):
    """design §5 — the frozen analysis input set. Immutable once created.

    ``claim_set_hash`` is ``set_hash`` over the project's member claim
    ``content_hash`` values at freeze time (``services.evidence.freeze_corpus``)
    — permutation-invariant, so it does not depend on ``source_version_ids``
    order. The contract has no ``content_hash`` field (it has
    ``claim_set_hash`` instead), so there is no separate audit-hash column here.
    """

    __tablename__ = "corpus_snapshots"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    source_version_ids: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    repository_refs: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    claim_set_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)


class CorpusSnapshotSource(AuditMixin, Base):
    """design §5 — normalized many-to-many: a snapshot's source-version membership.

    Queryable membership (not only the JSON ``source_version_ids`` list on
    ``CorpusSnapshot``) so "which snapshots include version X" is a plain join.
    """

    __tablename__ = "corpus_snapshot_sources"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id", "source_version_id", name="uq_corpus_snapshot_sources_snapshot_version"
        ),
    )

    snapshot_id: Mapped[str] = mapped_column(GUID(), ForeignKey("corpus_snapshots.id"), nullable=False, index=True)
    source_version_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("evidence_source_versions.id"), nullable=False, index=True
    )


class OpenQuestion(AuditMixin, Base):
    """design §7 — a materially significant unresolved question.

    ``status`` (AuditMixin) carries ``QuestionStatus`` (open/answered/deferred/
    unanswerable); ``genome_snapshot_id`` is now a real FK into
    ``genome_snapshots`` (RFC-0019, AOS-GENOME-MODELS-001 wires the table this
    slice adds). ``answer_claim_id`` links the claim that answered this
    question, once one exists.
    """

    __tablename__ = "open_questions"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    genome_snapshot_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("genome_snapshots.id"), index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    affected_dimensions: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    affected_foundation_domains: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    materiality: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    answer_type: Mapped[str] = mapped_column(String(32), nullable=False)
    answer_claim_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("claims.id"), index=True)
    minted_by: Mapped[str] = mapped_column(String(32), nullable=False)


# ---------------------------------------------------------------------------
# System Genome (RFC-0019, AOS-GENOME-MODELS-001) — the versioned,
# evidence-backed classification of the engineered system across the design's
# 16 GenomeDimensions (``aos_core.foundation.enums``). Derived deterministically
# from ``claims`` (AD-4, RFC-0016) by ``services/genome_rules.py`` +
# ``services/genome.py`` — NEVER from ``RepositoryDNA`` directly (DNA already
# reaches here as ``observed`` claims via the C5 backfill, RFC-0018 #214).
# Columns store ``aos_core.foundation.enums`` values as ``String``; JSON only
# for the open structures (``source_methods``/``trait_ids`` lists, the delta
# ``changes`` diff). The write path is ``services/genome.py``.
# ---------------------------------------------------------------------------


class GenomeSnapshot(AuditMixin, Base):
    """design §6.2-6.3 — a versioned system classification for one ``state_view``.

    ``status`` (AuditMixin) carries ``GenomeStatus`` (draft/reviewed/approved/
    superseded). Invariant (service-enforced, ``services/genome.py``): at most
    one non-superseded snapshot per ``(project_id, state_view)`` — generating a
    new one supersedes the prior. Approved snapshots are immutable: a later
    ``generate_genome`` call creates a NEW row and only flips the prior's
    ``status`` to ``superseded``; it never rewrites an approved row's traits.
    """

    __tablename__ = "genome_snapshots"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    corpus_snapshot_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("corpus_snapshots.id"), index=True)
    state_view: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # NB: no explicit `version` column — AuditMixin already provides one
    # (Integer, default=1). Redeclaring it collides at declarative-mapping time
    # (DuplicateColumnError in the compose/container import path, though it can
    # import-OK locally depending on import order — LES-042). The genome
    # snapshot "version N" semantics reuse the mixin column.
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    coverage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    aggregate_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    open_question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_conflict_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GenomeTrait(AuditMixin, Base):
    """design §6.4 — a single evidence-backed trait within a ``GenomeSnapshot``.

    No trait exists without provenance or an explicit ``unknown``
    classification (design §6.4; ``services/genome.py`` enforces this for every
    FOUNDATION_SHAPING dimension). Indexed on ``(genome_snapshot_id,
    dimension)`` — the common "traits for this snapshot's dimension X" query.
    """

    __tablename__ = "genome_traits"
    __table_args__ = (Index("ix_genome_traits_snapshot_dimension", "genome_snapshot_id", "dimension"),)

    genome_snapshot_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("genome_snapshots.id"), nullable=False, index=True
    )
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    trait_key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[object | None] = mapped_column(JSONField(), nullable=True)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    stability: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    criticality: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    source_methods: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)
    human_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class GenomeTraitClaim(AuditMixin, Base):
    """design §6.4 — the normalized trait<->claim provenance link.

    Keeps ``supporting_claim_ids``/``opposing_claim_ids`` queryable (per-row,
    joinable) rather than JSON blobs on ``GenomeTrait`` (design §15 — the same
    rationale as ``ClaimEvidenceLink`` for claims/fragments).
    """

    __tablename__ = "genome_trait_claims"
    __table_args__ = (
        UniqueConstraint("trait_id", "claim_id", "polarity", name="uq_genome_trait_claims_trait_claim_polarity"),
    )

    trait_id: Mapped[str] = mapped_column(GUID(), ForeignKey("genome_traits.id"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(GUID(), ForeignKey("claims.id"), nullable=False, index=True)
    polarity: Mapped[str] = mapped_column(String(32), nullable=False)


class SystemArchetype(AuditMixin, Base):
    """design §6.6 — a small, readable rollup of trait combinations.

    A summary, never a substitute for the underlying traits (design §6.6).
    """

    __tablename__ = "system_archetypes"

    genome_snapshot_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("genome_snapshots.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trait_ids: Mapped[list] = mapped_column(JSONField(), default=list, nullable=False)


class GenomeDelta(AuditMixin, Base):
    """design §6.7 — a pure diff between two ``GenomeSnapshot`` rows (``compare_genomes``).

    ``changes`` holds added/removed/changed traits plus coverage/confidence
    deltas (JSON — an open structure, like other delta/diff payloads in this
    module).
    """

    __tablename__ = "genome_deltas"

    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("projects.id"), nullable=False, index=True)
    from_snapshot_id: Mapped[str] = mapped_column(GUID(), ForeignKey("genome_snapshots.id"), nullable=False, index=True)
    to_snapshot_id: Mapped[str] = mapped_column(GUID(), ForeignKey("genome_snapshots.id"), nullable=False, index=True)
    changes: Mapped[dict] = mapped_column(JSONField(), default=dict, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)


# C4 — immutable-content guard. Each entry names the fields that constitute the
# row's *content* (mirroring its RFC-0017 contract's CONTENT_FIELDS projection,
# minus surrogate/audit columns the contract doesn't have at all, e.g.
# AuditMixin's own created_by/meta which aren't part of any evidence contract).
# A ``before_update`` UPDATE that touches any of these is refused — corrections
# go through a new row (``add_source_version``) or an explicit status/annotation
# transition, never an in-place content edit.
_EVIDENCE_IMMUTABLE_CONTENT_FIELDS: dict[type, frozenset[str]] = {
    EvidenceSource: frozenset(
        {
            "project_id", "source_type", "title", "origin", "originator", "canonical_uri",
            "sensitivity", "authority_domains", "access_policy_id", "minted_by", "content_hash",
        }
    ),
    EvidenceSourceVersion: frozenset(
        {
            "source_id", "version_ref", "content_hash", "captured_at", "effective_from",
            "effective_until", "supersedes_version_id", "ingestion_method", "parser_version",
            "minted_by",
        }
    ),
    EvidenceFragment: frozenset(
        {
            "source_version_id", "locator", "content_hash", "excerpt",
            "extraction_method", "extraction_confidence", "minted_by",
        }
    ),
    Claim: frozenset(
        {
            "project_id", "statement", "claim_type", "truth_layer", "domain", "scope", "polarity",
            "confidence", "materiality", "valid_from", "valid_until", "created_by", "derivation",
            "minted_by", "decision_id", "content_hash",
        }
    ),
    CorpusSnapshot: frozenset(
        {"project_id", "source_version_ids", "repository_refs", "claim_set_hash", "created_by", "purpose"}
    ),
}


class ImmutableContentError(ValueError):
    """Raised when an UPDATE attempts to change a content field of an immutable evidence row (C4)."""


def _assert_evidence_content_immutable(mapper, connection, target) -> None:
    fields = _EVIDENCE_IMMUTABLE_CONTENT_FIELDS.get(type(target))
    if not fields:
        return
    state = inspect(target)
    changed = [attr for attr in fields if state.attrs[attr].history.has_changes()]
    if changed:
        raise ImmutableContentError(
            f"C4 violation: cannot UPDATE immutable content field(s) {sorted(changed)} on "
            f"{type(target).__name__} id={target.id!r}; corrections require a new row "
            "(e.g. add_source_version) or an explicit status/annotation transition, not an "
            "in-place content edit."
        )


for _evidence_model in _EVIDENCE_IMMUTABLE_CONTENT_FIELDS:
    event.listen(_evidence_model, "before_update", _assert_evidence_content_immutable)
