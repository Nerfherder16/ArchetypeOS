import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Pin runtime settings before any app import so the suite is hermetic when a
# local .env exists (its docker-network hostnames are unreachable from the
# host — AOS-LOCAL-001 finding). Environment variables take precedence over
# .env in pydantic-settings, so this forces the same defaults CI runs with.
# Redis is pinned to a dead port, not 6379: health tests assert the degraded
# state, which must hold even on machines running a real local Redis.
os.environ["DATABASE_URL"] = "sqlite:///./archetypeos_dev.db"
os.environ["REDIS_URL"] = "redis://localhost:9999/0"
os.environ["ARTIFACT_ROOT"] = "./data/artifacts"
os.environ["REPOSITORY_ROOT"] = "./repositories"


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    from aos_core.database import Base, get_db
    from app.main import app, settings

    repository_root = tmp_path / "repositories"
    repository_root.mkdir()
    settings.repository_root = repository_root
    settings.artifact_root = tmp_path / "artifacts"

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """A bare in-memory session for service-level tests (no HTTP layer)."""
    import aos_core.models  # noqa: F401 — register every table on Base.metadata
    from aos_core.database import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
