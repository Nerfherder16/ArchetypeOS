import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Pin runtime settings before any app import so the suite is hermetic when a
# local .env exists (docker-network hostnames are unreachable from the host).
# Environment variables take precedence over .env in pydantic-settings.
os.environ["DATABASE_URL"] = "sqlite:///./archetypeos_worker_dev.db"
os.environ["REDIS_URL"] = "redis://localhost:9999/0"

import app.worker as worker  # noqa: E402
from aos_core.config import get_settings  # noqa: E402
from aos_core.database import Base  # noqa: E402
from aos_core.models import Artifact, CouncilReview, Job, KnowledgePage, NightlyDigest, Project, Repository, RepositoryDNA, ResearchNote  # noqa: E402


def test_worker_queue_name_is_stable():
    assert worker.QUEUE == "archetypeos:jobs"


class FakeRedis:
    """Captures lpush calls so the retry path needs no real Redis."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append(value)

    def lrange(self, name: str, start: int, end: int) -> list[str]:
        return list(self.queue)


@pytest.fixture()
def worker_db(tmp_path, monkeypatch) -> Generator[sessionmaker, None, None]:
    # Point run_scan at a tmp repository_root / artifact_root.
    repository_root = tmp_path / "repositories"
    repository_root.mkdir()
    artifact_root = tmp_path / "artifacts"
    monkeypatch.setenv("REPOSITORY_ROOT", str(repository_root))
    monkeypatch.setenv("ARTIFACT_ROOT", str(artifact_root))
    get_settings.cache_clear()

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    # Point the worker module (mark_job / run_job / handle_failure) at the test DB.
    monkeypatch.setattr(worker, "SessionLocal", testing_session_local)

    try:
        yield testing_session_local
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        get_settings.cache_clear()


def _make_demo_repo(repository_root, name: str = "demo") -> str:
    repo_dir = repository_root / name
    repo_dir.mkdir()
    (repo_dir / "example.py").write_text("print('hello')\n", encoding="utf-8")
    (repo_dir / "requirements.txt").write_text("redis\n", encoding="utf-8")
    return name


def test_run_scan_job(worker_db):
    settings = get_settings()
    local_path = _make_demo_repo(settings.repository_root)

    with worker_db() as db:
        project = Project(name="Demo", slug="demo")
        db.add(project)
        db.flush()
        repository = Repository(project_id=project.id, name="demo", local_path=local_path)
        db.add(repository)
        db.flush()
        job = Job(job_type="repository_scan", status="queued", project_id=project.id, repository_id=repository.id)
        db.add(job)
        db.commit()
        job_id = job.id
        repository_id = repository.id

    worker.run_job(job_id)

    with worker_db() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed"
        assert job.result["scanned"] == repository_id
        assert job.result["artifact"]
        artifact = (
            db.query(Artifact)
            .filter(Artifact.repository_id == repository_id, Artifact.artifact_type == "repository_scan")
            .first()
        )
        assert artifact is not None
        dna = db.query(RepositoryDNA).filter(RepositoryDNA.repository_id == repository_id).first()
        assert dna is not None


def test_run_digest_job(worker_db):
    with worker_db() as db:
        project = Project(name="Digest", slug="digest")
        db.add(project)
        db.flush()
        job = Job(job_type="project_digest", status="queued", project_id=project.id)
        db.add(job)
        db.commit()
        job_id = job.id
        project_id = project.id

    worker.run_job(job_id)

    with worker_db() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed"
        assert job.result["digest_id"]
        digest = db.query(NightlyDigest).filter(NightlyDigest.project_id == project_id).first()
        assert digest is not None
        assert job.result["digest_id"] == digest.id


def test_council_review_dispatch(worker_db):
    # The worker runs the council (deterministic provider) and completes the job
    # with {review_id, verdict}, persisting the review linked to the job.
    with worker_db() as db:
        project = Project(name="Council", slug="council-worker")
        db.add(project)
        db.flush()
        repository = Repository(project_id=project.id, name="svc", local_path="svc")
        db.add(repository)
        db.flush()
        db.add(
            RepositoryDNA(
                repository_id=repository.id,
                language_mix={"python": 1.0},
                frameworks=["fastapi"],
                risk_flags=["missing tests"],
            )
        )
        job = Job(
            job_type="council_review",
            status="queued",
            project_id=project.id,
            payload={"question": "Is this ready?"},
        )
        db.add(job)
        db.commit()
        job_id = job.id
        project_id = project.id

    worker.run_job(job_id)

    with worker_db() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed"
        review_id = job.result["review_id"]
        assert review_id
        assert job.result["verdict"]
        review = db.get(CouncilReview, review_id)
        assert review is not None
        assert review.project_id == project_id
        assert review.job_id == job_id
        assert len(review.agent_outputs) == 4


def test_council_review_multi_model_records_agent_models(worker_db, monkeypatch):
    # AOS-LLM-EVAL-001: the worker's council_review job goes through
    # council_provider; with a multi-model pool each agent output records a
    # DISTINCT model. Patch the selector to a spread fake (no network).
    import json
    import types

    class _SpreadFake:
        name = "rotating"

        def __init__(self, models):
            self._m = models
            self._i = 0

        def generate(self, *, system, prompt, max_tokens=1024, response_format=None):
            m = self._m[self._i % len(self._m)]
            self._i += 1
            text = json.dumps({
                "summary": f"via {m}", "findings": [f"f-{m}"], "evidence": ["e"],
                "concerns": [], "confidence": 0.7, "status": "Complete",
            })
            return types.SimpleNamespace(
                text=text, provider="openai_compatible", model=m, finish_reason="stop"
            )

    from app.handlers import council_review as council_handler

    monkeypatch.setattr(
        council_handler, "council_provider",
        lambda settings, sink=None: _SpreadFake(["groq-70b", "gemini", "cerebras-120b", "mistral"]),
    )

    with worker_db() as db:
        project = Project(name="MM", slug="mm-council")
        db.add(project)
        db.flush()
        repository = Repository(project_id=project.id, name="svc", local_path="svc")
        db.add(repository)
        db.flush()
        db.add(RepositoryDNA(repository_id=repository.id, language_mix={"python": 1.0},
                             frameworks=["fastapi"], risk_flags=["missing tests"]))
        job = Job(job_type="council_review", status="queued", project_id=project.id,
                  payload={"question": "Ready?"})
        db.add(job)
        db.commit()
        job_id = job.id

    worker.run_job(job_id)

    with worker_db() as db:
        review = db.get(CouncilReview, db.get(Job, job_id).result["review_id"])
        models = [o.agent_model for o in review.agent_outputs]
        assert all(models), "each agent output records its model through the worker"
        assert len(set(models)) == 4, "four agents ran on four distinct models"
        assert review.provider == "rotating"


def test_research_dispatch(worker_db):
    # The worker runs the research engine (deterministic, hermetic) over the
    # project's local corpus and completes the job with {note_id}, persisting the
    # ResearchNote (RFC-0011 slice-1).
    with worker_db() as db:
        project = Project(name="Research", slug="research-worker")
        db.add(project)
        db.flush()
        db.add(
            KnowledgePage(
                project_id=project.id,
                title="asyncpg postgres connection pooling",
                vault_path="vault/repos/asyncpg.md",
                page_type="repository",
            )
        )
        job = Job(
            job_type="research",
            status="queued",
            project_id=project.id,
            payload={"question": "Should we adopt asyncpg for postgres pooling?", "sensitivity": "public"},
        )
        db.add(job)
        db.commit()
        job_id = job.id
        project_id = project.id

    worker.run_job(job_id)

    with worker_db() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed"
        note_id = job.result["note_id"]
        assert note_id
        note = db.get(ResearchNote, note_id)
        assert note is not None
        assert note.project_id == project_id
        assert note.sources  # the corpus page was gathered, scored, and ranked
        assert note.confidence > 0.0


def test_research_run_dispatch(worker_db):
    # AOS-RESEARCH-003: the worker executes a persisted research plan through its
    # phases and completes the job with {run_id}, persisting the ResearchRun.
    from aos_core.models import ResearchRun
    from aos_core.services.llm_router import Sensitivity
    from aos_core.services.research_plan import create_research_plan

    with worker_db() as db:
        project = Project(name="Research Run", slug="research-run-worker")
        db.add(project)
        db.flush()
        db.add(
            KnowledgePage(
                project_id=project.id,
                title="qdrant vector database sharding guide",
                vault_path="vault/repos/qdrant.md",
                page_type="repository",
            )
        )
        db.commit()
        plan = create_research_plan(
            db, project_id=project.id, question="qdrant vector database sharding", sensitivity=Sensitivity.PUBLIC
        )
        job = Job(
            job_type="research_run",
            status="queued",
            project_id=project.id,
            payload={"plan_id": plan.id},
        )
        db.add(job)
        db.commit()
        job_id = job.id
        plan_id = plan.id

    worker.run_job(job_id)

    with worker_db() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed"
        run_id = job.result["run_id"]
        run = db.get(ResearchRun, run_id)
        assert run is not None
        assert run.plan_id == plan_id
        assert run.job_id == job_id
        assert [p["phase"] for p in run.phases] == ["plan", "search", "fetch", "verify", "synthesize"]


def test_test_job_backward_compat(worker_db):
    with worker_db() as db:
        job = Job(job_type="test", status="queued")
        db.add(job)
        db.commit()
        job_id = job.id

    worker.run_job(job_id)

    with worker_db() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed"
        assert job.result["message"] == "test job completed"
        assert job.result["worker"] == "archetypeos-worker"


def test_retry_then_fail(worker_db):
    # A repository_scan with a bogus repository_id: run_scan raises HTTPException(404).
    with worker_db() as db:
        job = Job(job_type="repository_scan", status="queued", repository_id="00000000-0000-0000-0000-000000000000")
        db.add(job)
        db.commit()
        job_id = job.id

    client = FakeRedis()
    # Mirror main()'s try/except across attempts until exhaustion.
    for _ in range(worker.MAX_ATTEMPTS):
        try:
            worker.run_job(job_id)
        except Exception as exc:
            worker.handle_failure(job_id, client, str(exc))

    with worker_db() as db:
        job = db.get(Job, job_id)
        # Slice 3: retry-budget exhaustion lands in dead_letter, not a bare "failed".
        assert job.status == "dead_letter"
        assert job.attempts == worker.MAX_ATTEMPTS
        assert job.error
    # Re-enqueued on every attempt except the final (dead-lettered) one.
    assert len(client.queue) == worker.MAX_ATTEMPTS - 1


def test_drain_outbox_delivers_deferred_jobs(worker_db):
    # AOS-JOBS-RELIABILITY-001: the worker tick drains undelivered job-outbox rows
    # so a job whose origination-time delivery was deferred (Redis was down) still
    # reaches the queue once the broker is reachable.
    from aos_core.models import JobOutbox

    with worker_db() as db:
        job = Job(job_type="test", status="queued")
        db.add(job)
        db.flush()
        db.add(JobOutbox(job_id=job.id))  # undelivered
        db.commit()
        job_id = job.id

    client = FakeRedis()
    assert worker.drain_outbox(client) == 1
    assert client.queue == [job_id]

    with worker_db() as db:
        assert db.query(JobOutbox).filter_by(job_id=job_id).one().delivered_at is not None


def test_digest_idempotent_on_rerun(worker_db):
    # AOS-JOBS-RELIABILITY-001 Slice 3: re-running a handler for the same job (as a
    # crash-recovery redelivery would) returns the existing output, never a duplicate.
    from aos_core.models import NightlyDigest

    with worker_db() as db:
        project = Project(name="Idem", slug="idem-digest")
        db.add(project)
        db.flush()
        job = Job(job_type="project_digest", status="running", project_id=project.id)
        db.add(job)
        db.commit()
        job_id = job.id

    with worker_db() as db:
        job = db.get(Job, job_id)
        from app.handlers.project_digest import run as run_digest

        first = run_digest(job, db)
        second = run_digest(job, db)
        assert first["digest_id"] == second["digest_id"]
        assert db.query(NightlyDigest).filter(NightlyDigest.job_id == job_id).count() == 1


def test_research_idempotent_on_rerun(worker_db):
    from aos_core.models import ResearchNote

    with worker_db() as db:
        project = Project(name="IdemR", slug="idem-research")
        db.add(project)
        db.flush()
        db.add(
            KnowledgePage(
                project_id=project.id,
                title="asyncpg pooling",
                vault_path="vault/repos/asyncpg.md",
                page_type="repository",
            )
        )
        job = Job(
            job_type="research",
            status="running",
            project_id=project.id,
            payload={"question": "adopt asyncpg?", "sensitivity": "public"},
        )
        db.add(job)
        db.commit()
        job_id = job.id

    with worker_db() as db:
        job = db.get(Job, job_id)
        from app.handlers.research import run as run_research

        first = run_research(job, db)
        second = run_research(job, db)
        assert first["note_id"] == second["note_id"]
        assert db.query(ResearchNote).filter(ResearchNote.job_id == job_id).count() == 1


def test_research_note_job_id_unique_backstop(worker_db):
    # The unique(job_id) constraint is the hard backstop behind the get-or-create
    # guard: a second note for the same job cannot be committed.
    import pytest as _pytest
    from sqlalchemy.exc import IntegrityError

    from aos_core.models import ResearchNote

    with worker_db() as db:
        project = Project(name="Uniq", slug="uniq-note")
        db.add(project)
        db.flush()
        job = Job(job_type="research", status="running", project_id=project.id)
        db.add(job)
        db.commit()
        db.add(ResearchNote(project_id=project.id, title="a", job_id=job.id))
        db.commit()
        db.add(ResearchNote(project_id=project.id, title="b", job_id=job.id))
        with _pytest.raises(IntegrityError):
            db.commit()


def test_reap_requeues_crashed_job(worker_db):
    # AOS-JOBS-RELIABILITY-001 Slice 2: a worker that died mid-job leaves a running
    # row with an expired lease; worker.reap recovers it (re-queues + redelivers),
    # closing the crash-recovery half of finding P0-1.
    from datetime import datetime, timezone

    from aos_core.models import JobOutbox

    dead_past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with worker_db() as db:
        job = Job(
            job_type="test",
            status="running",
            attempts=1,
            claimed_by="dead-worker",
            lease_expires_at=dead_past,
        )
        db.add(job)
        db.flush()
        db.add(JobOutbox(job_id=job.id, delivered_at=dead_past))  # already delivered once
        db.commit()
        job_id = job.id

    client = FakeRedis()
    assert worker.reap(client) == 1
    assert client.queue == [job_id]

    with worker_db() as db:
        row = db.get(Job, job_id)
        assert row.status == "queued"
        assert row.claimed_by is None and row.lease_expires_at is None


def test_reconcile_restores_job_stranded_from_broker(worker_db):
    # AOS-JOBS-RELIABILITY-001 Slice 4: a job marked queued and previously delivered
    # whose id is no longer in the broker list (Redis was flushed) is re-armed and
    # redelivered — the gap the outbox alone cannot see.
    from datetime import datetime, timezone

    from aos_core.models import JobOutbox

    with worker_db() as db:
        job = Job(job_type="test", status="queued")
        db.add(job)
        db.flush()
        # Outbox says delivered, but the broker (empty FakeRedis) has lost the id.
        db.add(JobOutbox(job_id=job.id, delivered_at=datetime(2026, 7, 11, tzinfo=timezone.utc)))
        db.commit()
        job_id = job.id

    client = FakeRedis()  # empty: the id is not in the queue
    summary = worker.reconcile_now(client)
    assert summary["restored"] == 1
    assert client.queue == [job_id]  # redelivered

    # Idempotent: once it is back in the queue, a second sweep restores nothing.
    assert worker.reconcile_now(client)["restored"] == 0


def test_register_self_registers_node_with_handler_capabilities(worker_db):
    # AOS-NODE-AGENT-001: the worker joins the node registry with its handlers'
    # capabilities so the control plane can route capability-declared work to it.
    from aos_core.models import Node, NodeCapability

    node_id = worker.register_self()
    with worker_db() as db:
        node = db.get(Node, node_id)
        assert node is not None
        assert node.name == worker.WORKER_ID
        caps = {
            c.capability
            for c in db.query(NodeCapability).filter(NodeCapability.node_id == node_id).all()
        }
        assert {"scan", "digest", "council", "research", "noop"} <= caps
        assert node.node_status == "healthy"
        assert node.last_seen_at is not None


def test_queue_is_single_sourced_from_core():
    # The worker's QUEUE must be the shared aos_core constant, not a local
    # literal (RFC-0007 / AOS-SCHED-001: one job-origination source of truth).
    from aos_core.services.jobs import QUEUE as CORE_QUEUE

    assert worker.QUEUE is CORE_QUEUE


def test_registry_loads_all_handlers_from_modules():
    # AOS-WORKER-HANDLERS-001: dispatch is assembled from per-type modules, not a
    # central source block (finding P1-1 / PR #179 hotspot).
    from app.handlers.registry import load_handlers

    reg = load_handlers()
    assert {
        "repository_scan",
        "project_digest",
        "council_review",
        "research",
        "research_run",
        "test",
    } <= set(reg)


def test_handler_spec_declares_richer_metadata():
    from app.handlers.registry import IDEMPOTENCY_STRATEGIES

    for spec in worker.JOB_HANDLERS.values():
        assert spec.capability
        assert spec.sensitivity in {"public", "private"}
        assert spec.timeout_seconds > 0
        assert spec.max_attempts >= 1
        assert spec.idempotency_strategy in IDEMPOTENCY_STRATEGIES
        assert isinstance(spec.result_schema, tuple)


def test_handler_registry_declares_capabilities():
    # AOS-WORKER-ROUTER-001: dispatch is a self-registering handler registry;
    # each handler declares capability + sensitivity (ready for NodeCapability
    # matching), not a hardcoded if/elif chain.
    registry = worker.JOB_HANDLERS
    assert {"repository_scan", "project_digest", "council_review", "research", "test"} <= set(registry)
    for spec in registry.values():
        assert spec.capability, "each handler declares a capability"
        assert spec.sensitivity in {"public", "private"}


def test_unknown_job_type_fails_clearly(worker_db):
    # AOS-WORKER-ROUTER-001: an unknown job type fails with a legible error
    # (previously it silently completed as a 'test' job).
    with worker_db() as db:
        job = Job(job_type="totally-unknown-kind", status="queued")
        db.add(job)
        db.commit()
        job_id = job.id

    worker.run_job(job_id)

    with worker_db() as db:
        job = db.get(Job, job_id)
        assert job.status == "failed"
        assert "totally-unknown-kind" in (job.error or "")
