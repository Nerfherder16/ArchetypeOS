"""Capability-level reuse matching (RFC-0013 Slices 2-4) — hermetic sqlite tests.

Slice 1 already extracts named ``{name, description, provenance}`` capabilities in
distillation; these tests cover the rest of RFC-0013:

- **Slice 2/3 persistence** (``_persist_capabilities``): a reasoned run stores one
  ``RepositoryCapability`` row per capability with a per-capability embedding; a
  deterministic re-distill (empty narrative) leaves prior rows untouched; a reasoned
  re-run replaces wholesale.
- **Slice 4 matching** (``recommend_reuse`` capability path): a need matches at
  capability granularity, cites the specific capability + its file, aggregates to the
  best capability per repo, respects ``exclude_project_id``, and — crucially — is a
  strict superset: with no capabilities extracted, behaviour is byte-for-byte the
  pre-RFC-0013 repo-level lexical path (no regression); when capabilities exist but the
  need matches none, it falls back to that same floor.

Hermetic: in-memory sqlite, a fake embedder, no model/network/vault I/O. The semantic
(pgvector) path is covered in ``test_capability_reuse_pg.py``.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aos_core.database import Base
from aos_core.models import (
    KnowledgePage,
    Project,
    Repository,
    RepositoryCapability,
    RepositoryDNA,
)
from aos_core.services.distillation import _persist_capabilities
from aos_core.services.transfer import recommend_reuse


class _NoneEmbedder:
    """The deterministic tier: ``embed`` always returns ``None`` (column stays NULL)."""

    name = "deterministic"
    dim = 384

    def embed(self, text: str):  # noqa: D401 - test stub
        return None


class _CountingEmbedder:
    """Returns a constant unit-ish vector and counts calls (proves per-capability embeds)."""

    name = "fake"
    dim = 384

    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed(self, text: str):
        self.calls.append(text)
        return [0.1] * self.dim


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


def _seed_repo(
    session: Session,
    *,
    project_name: str,
    repo_name: str,
    slug: str,
    purpose: str,
    language_mix: dict | None = None,
    frameworks: list | None = None,
) -> tuple[Project, Repository, KnowledgePage]:
    project = Project(name=project_name, slug=slug)
    session.add(project)
    session.flush()
    repo = Repository(project_id=project.id, name=repo_name, local_path=slug)
    session.add(repo)
    session.flush()
    session.add(
        RepositoryDNA(
            repository_id=repo.id,
            purpose=purpose,
            language_mix=language_mix or {},
            frameworks=frameworks or [],
        )
    )
    page = KnowledgePage(
        project_id=project.id,
        title=repo_name,
        vault_path=f"wiki/repositories/{slug}.md",
        page_type="repository",
        validation_state="reasoned",
        source_refs=[{"type": "repository", "id": repo.id}],
    )
    session.add(page)
    session.commit()
    return project, repo, page


def _add_capabilities(
    session: Session, repo: Repository, page: KnowledgePage, caps: list[dict], embedder=None
) -> int:
    written = _persist_capabilities(
        session, repo, page, {"capabilities": caps}, embedder or _NoneEmbedder()
    )
    session.commit()
    return written


# --- Slice 2/3: persistence -------------------------------------------------


def test_persist_stores_one_row_per_capability_with_embedding(db: Session) -> None:
    _, repo, page = _seed_repo(
        db, project_name="AiGentOS", repo_name="agent-core", slug="agent-core",
        purpose="An agent framework.",
    )
    embedder = _CountingEmbedder()
    written = _add_capabilities(
        db, repo, page,
        [
            {"name": "agent tool-calling loop", "description": "drives tools", "provenance": ["agent/loop.py"]},
            {"name": "approval queue", "description": "human gate", "provenance": ["agent/queue.py"]},
        ],
        embedder=embedder,
    )
    assert written == 2
    rows = db.query(RepositoryCapability).filter_by(repository_id=repo.id).all()
    assert {r.name for r in rows} == {"agent tool-calling loop", "approval queue"}
    # Each capability embedded its own `name + " " + description`, linked to the page.
    assert embedder.calls == ["agent tool-calling loop drives tools", "approval queue human gate"]
    assert all(r.embedding is not None for r in rows)
    assert all(r.knowledge_page_id == page.id for r in rows)


def test_persist_reasoned_rerun_replaces_wholesale(db: Session) -> None:
    _, repo, page = _seed_repo(
        db, project_name="AiGentOS", repo_name="agent-core", slug="agent-core", purpose="x",
    )
    _add_capabilities(db, repo, page, [{"name": "old capability", "provenance": ["a.py"]}])
    _add_capabilities(db, repo, page, [{"name": "new capability", "provenance": ["b.py"]}])
    rows = db.query(RepositoryCapability).filter_by(repository_id=repo.id).all()
    assert [r.name for r in rows] == ["new capability"]  # stale row gone, not accumulated


def test_persist_empty_narrative_leaves_prior_rows_untouched(db: Session) -> None:
    """A deterministic re-distill (narrative {}) must not wipe reasoned capabilities."""
    _, repo, page = _seed_repo(
        db, project_name="AiGentOS", repo_name="agent-core", slug="agent-core", purpose="x",
    )
    _add_capabilities(db, repo, page, [{"name": "kept capability", "provenance": ["a.py"]}])
    written = _persist_capabilities(db, repo, page, {}, _NoneEmbedder())  # empty narrative
    db.commit()
    assert written == 0
    rows = db.query(RepositoryCapability).filter_by(repository_id=repo.id).all()
    assert [r.name for r in rows] == ["kept capability"]


def test_persist_skips_nameless_capability(db: Session) -> None:
    _, repo, page = _seed_repo(
        db, project_name="AiGentOS", repo_name="agent-core", slug="agent-core", purpose="x",
    )
    written = _add_capabilities(
        db, repo, page,
        [{"name": "", "provenance": ["a.py"]}, {"name": "real one", "provenance": ["b.py"]}],
    )
    assert written == 1


# --- Slice 4: matching ------------------------------------------------------


def test_capability_lexical_match_cites_capability_and_file(db: Session) -> None:
    _, repo, page = _seed_repo(
        db, project_name="AiGentOS", repo_name="agent-core", slug="agent-core",
        purpose="An engineering intelligence platform.",  # product-level, does NOT mention tools
    )
    _add_capabilities(
        db, repo, page,
        [{"name": "agent tool-calling loop", "description": "an agentic loop that calls tools",
          "provenance": ["agent/loop.py"]}],
    )
    recs = recommend_reuse(db, need="agent framework with tool calling", embedder=_NoneEmbedder())
    assert recs, "capability path should match even though the product purpose does not"
    top = recs[0]
    assert top["source_repository"] == "agent-core"
    assert top["capability"] == "agent tool-calling loop"
    assert top["capability_provenance"] == ["agent/loop.py"]
    assert "agent/loop.py" in top["reusable_asset"]
    assert any(e.get("type") == "capability" for e in top["evidence"])


def test_capability_path_beats_wrong_product_purpose(db: Session) -> None:
    """The granularity fix: the repo whose CAPABILITY matches wins over one whose PURPOSE
    happens to share a word."""
    # Repo A: purpose mentions "routing" (a lexical decoy) but has no LLM capability.
    _, repo_a, page_a = _seed_repo(
        db, project_name="WebApp", repo_name="http-service", slug="http-service",
        purpose="HTTP routing and middleware for a web API.",
    )
    _add_capabilities(db, repo_a, page_a,
                      [{"name": "request router", "description": "url routing", "provenance": ["web/router.py"]}])
    # Repo B: the real LLM provider abstraction, named as a capability.
    _, repo_b, page_b = _seed_repo(
        db, project_name="AiGentOS", repo_name="model-core", slug="model-core",
        purpose="An agent operating system.",
    )
    _add_capabilities(db, repo_b, page_b,
                      [{"name": "LLM provider routing abstraction",
                        "description": "routes prompts across model provider backends",
                        "provenance": ["core/llm_router.py"]}])
    recs = recommend_reuse(db, need="LLM provider abstraction and model routing", embedder=_NoneEmbedder())
    assert recs[0]["source_repository"] == "model-core"
    assert recs[0]["capability"] == "LLM provider routing abstraction"


def test_best_capability_per_repo_one_rec(db: Session) -> None:
    _, repo, page = _seed_repo(
        db, project_name="AiGentOS", repo_name="agent-core", slug="agent-core", purpose="x",
    )
    _add_capabilities(
        db, repo, page,
        [
            {"name": "agent tool-calling loop", "description": "calls tools", "provenance": ["a.py"]},
            {"name": "agent memory store", "description": "stores agent memory", "provenance": ["b.py"]},
        ],
    )
    recs = recommend_reuse(db, need="agent tool calling", embedder=_NoneEmbedder())
    assert len([r for r in recs if r["source_repository"] == "agent-core"]) == 1
    assert recs[0]["capability"] == "agent tool-calling loop"


def test_capability_path_respects_exclude_project(db: Session) -> None:
    project, repo, page = _seed_repo(
        db, project_name="AiGentOS", repo_name="agent-core", slug="agent-core", purpose="x",
    )
    _add_capabilities(db, repo, page,
                      [{"name": "agent tool-calling loop", "description": "calls tools", "provenance": ["a.py"]}])
    recs = recommend_reuse(
        db, need="agent tool calling", exclude_project_id=project.id, embedder=_NoneEmbedder()
    )
    assert recs == []


def test_no_capabilities_is_byte_for_byte_repo_level(db: Session) -> None:
    """Strict-superset guarantee: with zero capability rows, the result equals the
    pre-RFC-0013 repo-level lexical path exactly."""
    _seed_repo(
        db, project_name="AiGentOS", repo_name="provider-abstraction", slug="provider-abstraction",
        purpose="A unified LLM provider abstraction layer for routing prompts across model backends.",
    )
    assert db.query(RepositoryCapability.id).first() is None
    recs = recommend_reuse(db, need="LLM provider abstraction routing", embedder=_NoneEmbedder())
    assert recs and recs[0]["source_repository"] == "provider-abstraction"
    # repo-level recs carry no capability field
    assert "capability" not in recs[0]


def test_capabilities_exist_but_need_unmatched_falls_back_to_repo_level(db: Session) -> None:
    """Capabilities exist but the need matches none of them → fall back to the repo purpose."""
    _, repo, page = _seed_repo(
        db, project_name="Payments", repo_name="billing", slug="billing",
        purpose="A Stripe billing and invoicing gateway handling subscriptions and webhooks.",
    )
    _add_capabilities(db, repo, page,
                      [{"name": "webhook verifier", "description": "verifies stripe signatures", "provenance": ["b.py"]}])
    # "billing invoicing subscriptions" matches the PURPOSE, not the lone capability.
    recs = recommend_reuse(db, need="billing invoicing subscriptions", embedder=_NoneEmbedder())
    assert recs and recs[0]["source_repository"] == "billing"
    assert "capability" not in recs[0]  # came from the repo-level fallback


def test_empty_need_returns_empty(db: Session) -> None:
    _, repo, page = _seed_repo(
        db, project_name="AiGentOS", repo_name="agent-core", slug="agent-core", purpose="x",
    )
    _add_capabilities(db, repo, page, [{"name": "cap", "provenance": ["a.py"]}])
    assert recommend_reuse(db, need="   ", embedder=_NoneEmbedder()) == []
