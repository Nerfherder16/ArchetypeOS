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
from aos_core.models import Artifact, Job, NightlyDigest, Project, Repository, RepositoryDNA  # noqa: E402


def test_worker_queue_name_is_stable():
    assert worker.QUEUE == "archetypeos:jobs"


class FakeRedis:
    """Captures lpush calls so the retry path needs no real Redis."""

    def __init__(self) -> None:
        self.queue: list[str] = []

    def lpush(self, name: str, value: str) -> None:
        self.queue.append(value)


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
        assert job.status == "failed"
        assert job.attempts == worker.MAX_ATTEMPTS
        assert job.error
    # Re-enqueued on every attempt except the final (failing) one.
    assert len(client.queue) == worker.MAX_ATTEMPTS - 1
