"""Hermetic (sqlite, no torch, no Postgres) tests for the RFC-0010 embedding seam.

Part 1 (AOS-EMBED-001) ships the vector-store + semantic-retrieval infra without
torch. These tests pin the invariants that keep it hermetic and behaviour-preserving:

- the :class:`EmbeddingProvider` seam — the deterministic embedder returns ``None``
  (``name``/``dim`` correct), and ``get_embedder`` resolves it / errors on unknown;
- ``distill_repository`` with the deterministic embedder leaves ``embedding`` NULL
  and behaves exactly as before;
- ``recommend_reuse`` with the deterministic embedder is byte-identical to the
  lexical Layer-0 path;
- the dialect gate: even a *fake* embedder that returns a vector falls back to
  lexical on sqlite (the semantic path is Postgres-only).
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aos_core.config import EMBEDDING_DIM, Settings
from aos_core.database import Base
from aos_core.embeddings import DeterministicEmbedder, EmbeddingProvider, get_embedder
from aos_core.models import KnowledgePage, Project, Repository, RepositoryDNA
from aos_core.services.transfer import recommend_reuse


class _FakeVectorEmbedder:
    """A non-torch fake that returns a fixed unit-ish vector (for the dialect-gate test)."""

    name = "fake"
    dim = EMBEDDING_DIM

    def embed(self, text: str) -> list[float] | None:
        return [1.0] + [0.0] * (EMBEDDING_DIM - 1)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _seed_repo(session: Session, *, project_name: str, repo_name: str, slug: str, purpose: str,
               frameworks: list | None = None) -> tuple[str, str]:
    project = Project(name=project_name, slug=slug)
    session.add(project)
    session.flush()
    repo = Repository(project_id=project.id, name=repo_name, local_path=slug)
    session.add(repo)
    session.flush()
    session.add(RepositoryDNA(repository_id=repo.id, purpose=purpose, frameworks=frameworks or []))
    session.add(
        KnowledgePage(
            project_id=project.id,
            title=repo_name,
            vault_path=f"wiki/repositories/{slug}.md",
            page_type="repository",
            validation_state="derived",
            source_refs=[{"type": "repository", "id": repo.id}, {"type": "vault_file", "ref": f"wiki/repositories/{slug}.md"}],
        )
    )
    session.commit()
    return project.id, repo.id


def _seed_portfolio(session: Session) -> None:
    _seed_repo(session, project_name="AiGentOS", repo_name="provider-abstraction", slug="provider-abstraction",
               purpose="A unified LLM provider abstraction layer for routing prompts across multiple model backends.",
               frameworks=["pydantic"])
    _seed_repo(session, project_name="Ledger", repo_name="payments-gateway", slug="payments-gateway",
               purpose="A Stripe billing and invoicing gateway handling subscriptions and webhooks.",
               frameworks=["express"])
    _seed_repo(session, project_name="Marketing", repo_name="landing-styles", slug="landing-styles",
               purpose="A collection of Tailwind CSS styles and layout components for marketing pages.",
               frameworks=["tailwind"])


# --- the seam ---------------------------------------------------------------


def test_deterministic_embedder_is_none_no_torch() -> None:
    emb = DeterministicEmbedder()
    assert emb.name == "deterministic"
    assert emb.dim == EMBEDDING_DIM == 384
    assert emb.embed("anything at all") is None
    # It satisfies the runtime-checkable protocol.
    assert isinstance(emb, EmbeddingProvider)


def test_get_embedder_resolves_deterministic_default() -> None:
    assert isinstance(get_embedder(Settings()), DeterministicEmbedder)
    assert isinstance(get_embedder(Settings(embedding_provider="deterministic")), DeterministicEmbedder)


def test_get_embedder_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_embedder(Settings(embedding_provider="sentence_transformers"))


def test_no_torch_import_in_embeddings_module() -> None:
    import sys

    import aos_core.embeddings  # noqa: F401

    assert "torch" not in sys.modules, "the embeddings seam must not import torch (Part 1 invariant)"


# --- recommend_reuse: deterministic == lexical, dialect gate ----------------


def test_recommend_reuse_deterministic_equals_lexical(db: Session) -> None:
    _seed_portfolio(db)
    need = "LLM provider abstraction to route prompts across model backends"

    default = recommend_reuse(db, need=need)
    deterministic = recommend_reuse(db, need=need, embedder=DeterministicEmbedder())

    assert default == deterministic
    assert default[0]["source_repository"] == "provider-abstraction"
    # Confidence is the lexical coverage score, and matched terms name the overlap.
    assert 0.0 < default[0]["confidence"] <= 1.0
    assert "provider" in default[0]["matched_terms"]


def test_sqlite_dialect_gate_falls_back_even_with_vector_embedder(db: Session) -> None:
    _seed_portfolio(db)
    need = "LLM provider abstraction to route prompts across model backends"

    lexical = recommend_reuse(db, need=need, embedder=DeterministicEmbedder())
    # A fake embedder returns a real vector, but on sqlite the semantic path is
    # gated off (dialect != postgresql) → identical lexical output.
    with_vector = recommend_reuse(db, need=need, embedder=_FakeVectorEmbedder())

    assert with_vector == lexical


def test_distill_leaves_embedding_null_with_deterministic_embedder(tmp_path) -> None:
    from app.main import settings
    from aos_core.services.distillation import distill_repository

    prev_repo_root, prev_knowledge_root = settings.repository_root, settings.knowledge_root
    settings.repository_root = tmp_path / "repositories"
    settings.knowledge_root = tmp_path / "knowledge"
    (settings.repository_root / "widget").mkdir(parents=True)
    (settings.repository_root / "widget" / "README.md").write_text(
        "# Widget Toolkit\n\nA reusable library for building command-line widgets.\n",
        encoding="utf-8",
    )

    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    try:
        project = Project(name="Distill", slug="distill-embed")
        session.add(project)
        session.flush()
        repo = Repository(project_id=project.id, name="widget", local_path="widget")
        session.add(repo)
        session.flush()
        session.add(RepositoryDNA(repository_id=repo.id))
        session.commit()

        page = distill_repository(
            session,
            repository_id=repo.id,
            knowledge_root=settings.knowledge_root,
            embedder=DeterministicEmbedder(),
        )
        # The deterministic embedder returns None → the column stays NULL.
        assert page.embedding is None
        # Unchanged behaviour otherwise: a derived, re-syncable repository page.
        assert page.page_type == "repository"
        assert page.validation_state == "derived"
        assert page.title == "Widget Toolkit"
    finally:
        session.close()
        engine.dispose()
        settings.repository_root, settings.knowledge_root = prev_repo_root, prev_knowledge_root
