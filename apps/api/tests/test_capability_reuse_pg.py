"""Postgres+pgvector-gated tests for the RFC-0013 capability semantic path (Slice 4).

Gated by ``@pytest.mark.pgvector`` and skipped unless ``AOS_TEST_DATABASE_URL``
points at a **postgresql** database with the ``vector`` extension (the CI "Vector
store tests" job provides one via ``pgvector/pgvector:pg16``). NO torch: the
capability vectors are synthetic and the embedder is a hand-written fake, so the
per-capability ``embedding <=> need_vec`` ordering + calibration + best-per-repo
aggregation are exercised off the torch tier.

This is the assertion the whole RFC hinges on: a reuse need matches a *single
capability's* vector (high cosine), aggregates to that repo, and cites the named
capability + its file — where matching the whole-product blob returned noise.
"""

from __future__ import annotations

import math
import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from aos_core.config import EMBEDDING_DIM
from aos_core.database import Base
from aos_core.models import (
    KnowledgePage,
    Project,
    Repository,
    RepositoryCapability,
    RepositoryDNA,
)
from aos_core.services.transfer import recommend_reuse

pytestmark = pytest.mark.pgvector

_DB_URL = os.environ.get("AOS_TEST_DATABASE_URL", "")


def _is_postgres(url: str) -> bool:
    if not url:
        return False
    try:
        return make_url(url).get_backend_name() == "postgresql"
    except Exception:
        return False


def _unit(components: dict[int, float]) -> list[float]:
    vec = [0.0] * EMBEDDING_DIM
    for i, w in components.items():
        vec[i] = w
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


_VEC_ON_AXIS = _unit({0: 1.0})                       # cos(need)=1.0 → distance 0.0
_VEC_60_DEG = _unit({0: 0.5, 1: math.sqrt(3) / 2})   # cos(need)=0.5 → distance 0.5
_VEC_ORTHOGONAL = _unit({2: 1.0})                    # cos(need)=0.0 → distance 1.0


class _FakeAxisEmbedder:
    """Returns the query-axis vector for any need (deterministic, NO torch)."""

    name = "fake"
    dim = EMBEDDING_DIM

    def embed(self, text: str) -> list[float] | None:
        return list(_VEC_ON_AXIS)


@pytest.fixture()
def pg_session() -> Generator[Session, None, None]:
    if not _is_postgres(_DB_URL):
        pytest.skip("AOS_TEST_DATABASE_URL not set to a postgresql database")
    engine = create_engine(_DB_URL, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _seed_repo_with_capabilities(
    session: Session, *, repo_name: str, slug: str, purpose: str, capabilities: list[dict]
) -> None:
    """Seed a project+repo+DNA+page and one RepositoryCapability per spec (with embedding)."""
    project = Project(name=repo_name, slug=slug)
    session.add(project)
    session.flush()
    repo = Repository(project_id=project.id, name=repo_name, local_path=slug)
    session.add(repo)
    session.flush()
    session.add(RepositoryDNA(repository_id=repo.id, purpose=purpose))
    page = KnowledgePage(
        project_id=project.id,
        title=repo_name,
        vault_path=f"wiki/repositories/{slug}.md",
        page_type="repository",
        validation_state="reasoned",
        source_refs=[{"type": "repository", "id": repo.id}],
    )
    session.add(page)
    session.flush()
    for cap in capabilities:
        session.add(
            RepositoryCapability(
                repository_id=repo.id,
                knowledge_page_id=page.id,
                name=cap["name"],
                description=cap.get("description", ""),
                provenance=cap.get("provenance", []),
                embedding=cap["embedding"],
            )
        )
    session.commit()


def test_capability_cosine_ordering_and_citation(pg_session: Session) -> None:
    # Both repos have product purposes with ZERO lexical overlap with the need — only
    # the per-capability vector separates them. "near" capability sits on the query
    # axis (distance 0), "far" at 60° (distance 0.5).
    _seed_repo_with_capabilities(
        pg_session, repo_name="agent-os", slug="agent-os", purpose="quokka platypus",
        capabilities=[{"name": "agent tool-calling loop", "description": "drives tools",
                       "provenance": ["agent/loop.py"], "embedding": _VEC_ON_AXIS}],
    )
    _seed_repo_with_capabilities(
        pg_session, repo_name="side-repo", slug="side-repo", purpose="marmot capybara",
        capabilities=[{"name": "config loader", "description": "loads config",
                       "provenance": ["conf.py"], "embedding": _VEC_60_DEG}],
    )

    results = recommend_reuse(pg_session, need="xyzzy plugh frobnicate", embedder=_FakeAxisEmbedder())

    names = [r["source_repository"] for r in results]
    assert "agent-os" in names and "side-repo" in names
    assert names.index("agent-os") < names.index("side-repo")

    near = next(r for r in results if r["source_repository"] == "agent-os")
    # Capability path recommendation cites the specific capability + its file.
    assert near["capability"] == "agent tool-calling loop"
    assert near["capability_provenance"] == ["agent/loop.py"]
    assert "agent/loop.py" in near["reusable_asset"]
    assert any(e.get("type") == "capability" for e in near["evidence"])
    # Calibrated (distance 0 → sem 1.0, coverage 0 → 0.6*1.0 = 0.6), never a raw cosine.
    assert near["confidence"] == pytest.approx(0.6, abs=1e-4)


def test_best_capability_per_repo_on_postgres(pg_session: Session) -> None:
    # One repo, two capabilities: a close one (on-axis) and a far one (orthogonal).
    # The repo must appear once, represented by its strongest capability.
    _seed_repo_with_capabilities(
        pg_session, repo_name="multi", slug="multi", purpose="unrelated purpose",
        capabilities=[
            {"name": "strong match", "description": "d", "provenance": ["a.py"], "embedding": _VEC_ON_AXIS},
            {"name": "weak match", "description": "d", "provenance": ["b.py"], "embedding": _VEC_ORTHOGONAL},
        ],
    )
    results = recommend_reuse(pg_session, need="xyzzy plugh", embedder=_FakeAxisEmbedder())
    multi = [r for r in results if r["source_repository"] == "multi"]
    assert len(multi) == 1
    assert multi[0]["capability"] == "strong match"


def test_capability_lexical_provenance_kept_on_postgres(pg_session: Session) -> None:
    # A capability with BOTH lexical overlap and a close embedding: the blend floors
    # at the lexical coverage and keeps the matched-term provenance.
    _seed_repo_with_capabilities(
        pg_session, repo_name="router", slug="router", purpose="a web service",
        capabilities=[{"name": "provider routing abstraction",
                       "description": "routing across providers",
                       "provenance": ["llm/router.py"], "embedding": _VEC_60_DEG}],
    )
    results = recommend_reuse(pg_session, need="provider routing abstraction", embedder=_FakeAxisEmbedder())
    top = next(r for r in results if r["source_repository"] == "router")
    # coverage = 3/3 (provider, routing, abstraction); floored up over the 0.5 sem blend.
    assert top["confidence"] == pytest.approx(1.0, abs=1e-3)
    assert "routing" in top["matched_terms"]
