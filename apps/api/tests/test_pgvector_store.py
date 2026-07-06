"""Postgres+pgvector-gated tests for the RFC-0010 semantic retrieval path (AOS-EMBED-001).

Gated by ``@pytest.mark.pgvector`` and skipped unless ``AOS_TEST_DATABASE_URL``
points at a **postgresql** database with the ``vector`` extension available (the CI
"Vector store tests" job provides one via a ``pgvector/pgvector:pg16`` service). NO
torch: the vectors are synthetic and the embedder is a hand-written fake, so the
whole pgvector SQL / ordering / calibration path is exercised off the torch tier.

It asserts the three things Part 1 must prove on real Postgres:
  1. ``embedding <=> need_vec`` ordering ranks the semantically-closest repo first;
  2. a lexical-miss / semantic-hit repo (zero lexical overlap) is surfaced — the
     lexical floor would have dropped it;
  3. the reported confidence is calibrated (``0..1``, not a raw cosine) and lexical
     ``matched_terms`` provenance is intact when there is lexical overlap.
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
from aos_core.models import KnowledgePage, Project, Repository, RepositoryDNA
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
    """A length-``EMBEDDING_DIM`` unit vector from a sparse ``{index: weight}`` spec."""
    vec = [0.0] * EMBEDDING_DIM
    for i, w in components.items():
        vec[i] = w
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


# Synthetic corpus of unit vectors (dim 384). e0 is the "query axis".
_VEC_ON_AXIS = _unit({0: 1.0})                       # cos(need)=1.0  → distance 0.0
_VEC_60_DEG = _unit({0: 0.5, 1: math.sqrt(3) / 2})   # cos(need)=0.5  → distance 0.5
_VEC_ORTHOGONAL = _unit({2: 1.0})                    # cos(need)=0.0  → distance 1.0


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


def _seed(session: Session, *, repo_name: str, slug: str, purpose: str, embedding: list[float]) -> None:
    project = Project(name=repo_name, slug=slug)
    session.add(project)
    session.flush()
    repo = Repository(project_id=project.id, name=repo_name, local_path=slug)
    session.add(repo)
    session.flush()
    session.add(RepositoryDNA(repository_id=repo.id, purpose=purpose))
    session.add(
        KnowledgePage(
            project_id=project.id,
            title=repo_name,
            vault_path=f"wiki/repositories/{slug}.md",
            page_type="repository",
            validation_state="derived",
            source_refs=[{"type": "repository", "id": repo.id}, {"type": "vault_file", "ref": f"wiki/repositories/{slug}.md"}],
            embedding=embedding,
        )
    )
    session.commit()


def test_cosine_ordering_and_lexical_miss_semantic_hit(pg_session: Session) -> None:
    # Two repos with ZERO lexical overlap with the need — pure lexical would drop
    # both. "near" sits on the query axis (distance 0), "far" at 60° (distance 0.5).
    _seed(pg_session, repo_name="near-repo", slug="near-repo",
          purpose="quokka platypus", embedding=_VEC_ON_AXIS)
    _seed(pg_session, repo_name="far-repo", slug="far-repo",
          purpose="marmot capybara", embedding=_VEC_60_DEG)

    results = recommend_reuse(pg_session, need="xyzzy plugh frobnicate", embedder=_FakeAxisEmbedder())

    names = [r["source_repository"] for r in results]
    # Lexical-miss / semantic-hit: both surface (the lexical floor would have
    # dropped them), and the semantically-closest (<=>) repo ranks first.
    assert "near-repo" in names and "far-repo" in names
    assert names.index("near-repo") < names.index("far-repo")

    near = next(r for r in results if r["source_repository"] == "near-repo")
    # Calibrated, NOT a raw cosine: distance 0 → sem 1.0, coverage 0 →
    # confidence = 0.6*1.0 + 0.4*0 = 0.6 (never emits the raw 1.0 similarity).
    assert 0.0 < near["confidence"] <= 1.0
    assert near["confidence"] == pytest.approx(0.6, abs=1e-4)
    # A pure semantic hit has no lexical matched terms (honest provenance).
    assert near["matched_terms"] == []


def test_semantic_confidence_keeps_lexical_provenance(pg_session: Session) -> None:
    # A repo with BOTH lexical overlap and a close embedding: the blend is floored
    # at the lexical coverage and the matched-term provenance is intact.
    _seed(pg_session, repo_name="kube", slug="kube",
          purpose="container orchestration platform", embedding=_VEC_60_DEG)
    # A distractor: orthogonal embedding + no lexical overlap → dropped (conf 0).
    _seed(pg_session, repo_name="noise", slug="noise",
          purpose="unrelated ledger billing", embedding=_VEC_ORTHOGONAL)

    results = recommend_reuse(pg_session, need="container orchestration scheduling", embedder=_FakeAxisEmbedder())

    names = [r["source_repository"] for r in results]
    assert "kube" in names
    assert "noise" not in names  # orthogonal + lexical miss → confidence 0 → dropped
    kube = next(r for r in results if r["source_repository"] == "kube")
    # Lexical coverage = 2/3 (container, orchestration of 3 need terms); blend with
    # sem 0.5 is 0.6*0.5 + 0.4*0.6667 = 0.5667, floored up to the coverage 0.6667.
    assert kube["confidence"] == pytest.approx(2 / 3, abs=1e-3)
    assert "container" in kube["matched_terms"]
    assert "orchestration" in kube["matched_terms"]
