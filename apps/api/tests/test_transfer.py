"""Service + API tests for the Knowledge Transfer Engine (AOS-TRANSFER-001 / RFC-0009).

Given a portfolio of distilled repositories (each a ``KnowledgePage``
``page_type="repository"`` + a ``RepositoryDNA`` carrying the distilled ``purpose``
and technologies), ``recommend_reuse`` scores a free-text **need** by deterministic
lexical **need coverage** (the fraction of the need's terms the candidate covers via
text or technologies) and returns ranked, provenance-tagged reuse recommendations —
excluding the target project's own repos.

Hermetic: an in-memory sqlite DB is seeded directly; no model, no network, no vault
I/O. The API test seeds the same file DB the app reads (mirroring test_distillation).
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aos_core.database import Base
from aos_core.models import KnowledgePage, Project, Repository, RepositoryDNA
from aos_core.services.transfer import recommend_reuse, score_relevance

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


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
    package_managers: list | None = None,
    frameworks: list | None = None,
) -> tuple[str, str]:
    """Seed a project + repo + DNA + a distilled repository KnowledgePage. Returns (project_id, repo_id)."""
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
            package_managers=package_managers or [],
            frameworks=frameworks or [],
        )
    )
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


def _seed_portfolio(session: Session) -> dict:
    """Three distilled repos across three projects with distinct tech/purpose."""
    llm_pid, llm_rid = _seed_repo(
        session,
        project_name="AiGentOS",
        repo_name="provider-abstraction",
        slug="provider-abstraction",
        purpose="A unified LLM provider abstraction layer for routing prompts across multiple model backends.",
        language_mix={"Python": 900},
        package_managers=["pip"],
        frameworks=["pydantic"],
    )
    pay_pid, pay_rid = _seed_repo(
        session,
        project_name="Ledger",
        repo_name="payments-gateway",
        slug="payments-gateway",
        purpose="A Stripe billing and invoicing gateway handling subscriptions and webhooks.",
        language_mix={"TypeScript": 800},
        package_managers=["npm"],
        frameworks=["express"],
    )
    css_pid, css_rid = _seed_repo(
        session,
        project_name="Marketing",
        repo_name="landing-styles",
        slug="landing-styles",
        purpose="A collection of Tailwind CSS styles and layout components for marketing pages.",
        language_mix={"CSS": 500},
        package_managers=["npm"],
        frameworks=["tailwind"],
    )
    return {
        "llm": (llm_pid, llm_rid),
        "pay": (pay_pid, pay_rid),
        "css": (css_pid, css_rid),
    }


# --- score_relevance (pure) -------------------------------------------------


def test_score_relevance_empty_need_is_zero() -> None:
    assert score_relevance(set(), {"provider", "llm"}, {"python"}) == (0.0, [])


def test_score_relevance_is_need_coverage() -> None:
    need = {"llm", "provider", "routing"}
    cand = {"llm", "provider", "backends"}
    tech = {"python", "llm"}
    score, matched = score_relevance(need, cand, tech)
    # Need coverage = |covered| / |need|. covered = (need ∩ cand = {llm, provider})
    # ∪ (need ∩ tech = {llm}) = {llm, provider}; |{llm, provider}| / 3 = 0.6667.
    assert score == pytest.approx(2 / 3, abs=1e-4)
    assert matched == ["llm", "provider"]


def test_score_relevance_counts_a_tech_only_match() -> None:
    # A need term the candidate text misses but a technology covers still counts.
    need = {"fastapi", "service"}
    score, matched = score_relevance(need, {"service"}, {"fastapi"})
    # Both need terms are covered (service via text, fastapi via tech) → 2/2 = 1.0.
    assert score == pytest.approx(1.0)
    assert matched == ["fastapi", "service"]


def test_score_relevance_caps_at_one() -> None:
    need = {"a1", "b2", "c3", "d4", "e5", "f6", "g7"}
    score, _ = score_relevance(need, need, need)
    assert score == pytest.approx(1.0)


# --- recommend_reuse (retrieval) --------------------------------------------


def test_ranks_relevant_repo_first_with_provenance(db: Session) -> None:
    ids = _seed_portfolio(db)
    llm_pid, llm_rid = ids["llm"]

    results = recommend_reuse(db, need="Need an LLM provider abstraction to route prompts across model backends")

    assert results, "expected at least one recommendation"
    top = results[0]
    assert top["source_repository"] == "provider-abstraction"
    assert top["source_project_id"] == llm_pid
    # Matched-term provenance names the shared terms; reason echoes them.
    assert "provider" in top["matched_terms"]
    assert "abstraction" in top["matched_terms"]
    assert top["reason"]
    # Evidence cites the source distillation's vault_path + the repo id.
    refs = {(e.get("type"), e.get("ref") or e.get("id")) for e in top["evidence"]}
    assert ("distillation", "wiki/repositories/provider-abstraction.md") in refs
    assert ("repository", llm_rid) in refs
    # Confidence is the relevance score; the top repo outranks the others.
    assert 0.0 < top["confidence"] <= 1.0
    assert results == sorted(results, key=lambda r: -r["confidence"])
    # The heuristic required-changes / risks fields are present.
    assert top["required_changes"] and top["risks"]


def test_excludes_target_projects_own_repo(db: Session) -> None:
    ids = _seed_portfolio(db)
    llm_pid, _ = ids["llm"]

    # Query the LLM need but from the LLM project — its own repo must be excluded.
    results = recommend_reuse(
        db,
        need="LLM provider abstraction routing across model backends",
        exclude_project_id=llm_pid,
    )
    repos = {r["source_repository"] for r in results}
    assert "provider-abstraction" not in repos


def test_technology_match_boosts_score(db: Session) -> None:
    _seed_portfolio(db)
    # "tailwind" is a framework of landing-styles → tech boost even beyond text overlap.
    results = recommend_reuse(db, need="tailwind styling for marketing landing components")
    assert results
    assert results[0]["source_repository"] == "landing-styles"
    assert "tailwind" in results[0]["matched_terms"]


def test_empty_portfolio_returns_empty(db: Session) -> None:
    assert recommend_reuse(db, need="anything at all here") == []


def test_empty_need_returns_empty(db: Session) -> None:
    _seed_portfolio(db)
    assert recommend_reuse(db, need="") == []
    assert recommend_reuse(db, need="   ") == []


def test_zero_overlap_need_returns_empty(db: Session) -> None:
    _seed_portfolio(db)
    # No shared meaningful tokens with any distilled repo.
    assert recommend_reuse(db, need="quantum origami waterfall zeppelin") == []


def test_limit_is_honoured(db: Session) -> None:
    _seed_portfolio(db)
    # A need touching all three (each purpose mentions "components" or shared terms).
    results = recommend_reuse(db, need="provider gateway styles components layer", limit=1)
    assert len(results) <= 1


# --- API: POST /projects/{project_id}/transfer ------------------------------


def _seed_via_client(client) -> dict:
    """Seed the portfolio into the app's own (file) DB via a same-file session."""
    from app.main import settings  # noqa: F401  (kept parallel to test_distillation)
    from aos_core.database import get_db
    from app.main import app

    # Reuse the app's overridden session factory to seed the same DB the route reads.
    gen = app.dependency_overrides[get_db]()
    session: Session = next(gen)
    try:
        ids = _seed_portfolio(session)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return ids


def test_api_transfer_returns_ranked_list(client) -> None:
    ids = _seed_via_client(client)
    llm_pid, _ = ids["llm"]
    # Query from a different project (payments) so the LLM repo is eligible.
    pay_pid, _ = ids["pay"]

    resp = client.post(
        f"/projects/{pay_pid}/transfer",
        json={"need": "LLM provider abstraction to route prompts across model backends"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body, "expected recommendations"
    assert body[0]["source_repository"] == "provider-abstraction"
    assert body[0]["source_project_id"] == llm_pid
    assert any(e["type"] == "distillation" for e in body[0]["evidence"])


def test_api_transfer_excludes_own_project(client) -> None:
    ids = _seed_via_client(client)
    llm_pid, _ = ids["llm"]

    resp = client.post(
        f"/projects/{llm_pid}/transfer",
        json={"need": "LLM provider abstraction routing across model backends"},
    )
    assert resp.status_code == 200, resp.text
    repos = {r["source_repository"] for r in resp.json()}
    assert "provider-abstraction" not in repos


def test_api_transfer_missing_project_is_404(client) -> None:
    resp = client.post(f"/projects/{UNKNOWN_ID}/transfer", json={"need": "anything"})
    assert resp.status_code == 404
