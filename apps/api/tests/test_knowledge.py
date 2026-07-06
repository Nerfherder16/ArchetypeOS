"""Knowledge read path tests (AOS-KNOW-002 / RFC-0002 / RFC-0004).

Counts are derived from the live lessons index, not hardcoded: lessons are
append-only (a new lesson is recorded on every CI failure / guardian BLOCK),
so pinning a magic count makes the suite brittle (see LES-012). The invariants
that matter are self-consistency (synced == created on first sync, == updated
on re-sync, row count stable) and the specific known facts (LES-001..011 are
present and contiguous from LES-001). Open lessons are derived live from the
index (OPEN_IDS), never pinned to a specific ID — a lesson's status flips when a
loop consumes it (e.g. AOS-20 closed LES-007), which must not break this suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.models import KnowledgePage
from aos_core.services.knowledge import parse_lessons_index, sync_knowledge

from app.main import settings

# Repo root resolved from this file so the vault path is cwd-independent.
REPO_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_ROOT = REPO_ROOT / "knowledge"
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"

# Expected values derived from the live index — robust to lesson growth.
_INDEX_TEXT = (KNOWLEDGE_ROOT / "wiki" / "lessons" / "index.md").read_text(encoding="utf-8")
_LESSONS = parse_lessons_index(_INDEX_TEXT)
N_LESSONS = len(_LESSONS)
OPEN_IDS = [row["lesson_id"] for row in _LESSONS if row["status"] == "open"]
N_OPEN = len(OPEN_IDS)
# Known lessons that must always be present (grows over time; never shrinks).
KNOWN_MIN = 11


@pytest.fixture()
def db():
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


def test_parse_lessons_index() -> None:
    rows = parse_lessons_index(_INDEX_TEXT)

    assert len(rows) >= KNOWN_MIN
    ids = [row["lesson_id"] for row in rows]
    # Contiguous from LES-001, and the original 11 are all present.
    assert ids == [f"LES-{n:03d}" for n in range(1, len(rows) + 1)]
    assert {f"LES-{n:03d}" for n in range(1, KNOWN_MIN + 1)} <= set(ids)

    # Open lessons are derived live, not pinned to a specific ID (AOS-20 closed LES-007).
    assert OPEN_IDS, "the live index should have at least one open lesson"
    assert [row["lesson_id"] for row in rows if row["status"] == "open"] == OPEN_IDS
    assert all(row["status"] in {"open", "closed"} for row in rows)

    # LES-001 field spot-check
    les1 = rows[0]
    assert les1["date"] == "2026-07-05"
    assert les1["category"] == "guardian-catch"
    assert "Credential-shaped strings" in les1["short"]

    # Tolerant: empty / malformed input never raises, yields []
    assert parse_lessons_index("") == []
    assert parse_lessons_index("# heading\n\nno table here\n") == []
    assert parse_lessons_index("| not a lesson | row |\n| --- | --- |\n") == []


def test_sync_knowledge(db) -> None:
    result = sync_knowledge(db, KNOWLEDGE_ROOT)

    assert result["synced"] == N_LESSONS
    assert result["created"] == N_LESSONS
    assert result["updated"] == 0
    assert result["open_lessons"] == N_OPEN

    pages = db.query(KnowledgePage).all()
    assert len(pages) == N_LESSONS
    assert all(page.page_type == "lesson" for page in pages)
    assert all(page.project_id is None for page in pages)
    assert all(page.vault_path.startswith("wiki/lessons/LES-") for page in pages)

    open_pages = db.query(KnowledgePage).filter(KnowledgePage.validation_state == "open").all()
    assert len(open_pages) == N_OPEN
    assert {page.vault_path for page in open_pages} == {f"wiki/lessons/{lid}.md" for lid in OPEN_IDS}

    # Idempotent re-sync: update in place, no dupes
    rerun = sync_knowledge(db, KNOWLEDGE_ROOT)
    assert rerun["synced"] == N_LESSONS
    assert rerun["created"] == 0
    assert rerun["updated"] == N_LESSONS
    assert rerun["open_lessons"] == N_OPEN
    assert db.query(KnowledgePage).count() == N_LESSONS


def test_sync_knowledge_missing_dir(db, tmp_path) -> None:
    result = sync_knowledge(db, tmp_path / "does-not-exist")
    assert result == {"synced": 0, "created": 0, "updated": 0, "open_lessons": 0}
    assert db.query(KnowledgePage).count() == 0


def test_sync_knowledge_derives_decision_pages(db, tmp_path) -> None:
    """Approved-decision ADRs in the vault are re-derived as `decision` pages.

    Count-agnostic (LES-012): a temp vault with no lessons index is used, so the
    invariants asserted are about the decision page itself, not any pinned total.
    """
    decisions_dir = tmp_path / "wiki" / "decisions"
    decisions_dir.mkdir(parents=True)
    (decisions_dir / "ADR-sample-decision-abcd1234.md").write_text(
        "# ADR — Sample decision\n\n## Status\n\nAccepted\n\n## Context\n\nBecause reasons.\n",
        encoding="utf-8",
    )
    # Tolerant: a heading-less / empty file and .gitkeep are skipped, never raise.
    (decisions_dir / "empty.md").write_text("", encoding="utf-8")
    (decisions_dir / ".gitkeep").write_text("", encoding="utf-8")

    result = sync_knowledge(db, tmp_path)
    assert result["synced"] >= 1

    decision_pages = db.query(KnowledgePage).filter(KnowledgePage.page_type == "decision").all()
    assert len(decision_pages) == 1
    page = decision_pages[0]
    assert page.vault_path == "wiki/decisions/ADR-sample-decision-abcd1234.md"
    assert page.validation_state == "approved"
    assert page.title == "ADR — Sample decision"
    assert page.checksum

    # Idempotent re-sync: update in place, no duplicate decision page.
    sync_knowledge(db, tmp_path)
    assert db.query(KnowledgePage).filter(KnowledgePage.page_type == "decision").count() == 1


def test_sync_knowledge_derives_repository_pages(db, tmp_path) -> None:
    """Repository distillations in the vault are re-derived as `repository` pages.

    Count-agnostic (LES-012): a temp vault (no lessons index) is used, so the
    invariants asserted are about the repository page itself (RFC-0008 /
    AOS-DISTILL-001), not any pinned total.
    """
    repos_dir = tmp_path / "wiki" / "repositories"
    repos_dir.mkdir(parents=True)
    (repos_dir / "free-llm-api-resources.md").write_text(
        "# Free LLM API resources\n\n## Summary\n\nA curated catalog of free LLM API providers.\n",
        encoding="utf-8",
    )
    # Tolerant: a heading-less / empty file and .gitkeep are skipped, never raise.
    (repos_dir / "empty.md").write_text("", encoding="utf-8")
    (repos_dir / ".gitkeep").write_text("", encoding="utf-8")

    result = sync_knowledge(db, tmp_path)
    assert result["synced"] >= 1

    repo_pages = db.query(KnowledgePage).filter(KnowledgePage.page_type == "repository").all()
    assert len(repo_pages) == 1
    page = repo_pages[0]
    assert page.vault_path == "wiki/repositories/free-llm-api-resources.md"
    assert page.validation_state == "derived"
    assert page.title == "Free LLM API resources"
    assert page.checksum

    # Idempotent re-sync: update in place, no duplicate repository page.
    sync_knowledge(db, tmp_path)
    assert db.query(KnowledgePage).filter(KnowledgePage.page_type == "repository").count() == 1


def test_knowledge_api(client: TestClient) -> None:
    settings.knowledge_root = KNOWLEDGE_ROOT

    synced = client.post("/knowledge/sync")
    assert synced.status_code == 200, synced.text
    counts = synced.json()
    assert counts == {"synced": N_LESSONS, "created": N_LESSONS, "updated": 0, "open_lessons": N_OPEN}

    listing = client.get("/knowledge/pages", params={"page_type": "lesson"})
    assert listing.status_code == 200, listing.text
    pages = listing.json()
    assert len(pages) == N_LESSONS
    assert all(page["page_type"] == "lesson" for page in pages)
    assert all(page["project_id"] is None for page in pages)

    open_listing = client.get("/knowledge/pages", params={"validation_state": "open"})
    assert open_listing.status_code == 200, open_listing.text
    open_pages = open_listing.json()
    assert len(open_pages) == N_OPEN
    assert {page["vault_path"] for page in open_pages} == {f"wiki/lessons/{lid}.md" for lid in OPEN_IDS}

    page_id = open_pages[0]["id"]
    one = client.get(f"/knowledge/pages/{page_id}")
    assert one.status_code == 200, one.text
    assert one.json()["id"] == page_id

    missing = client.get(f"/knowledge/pages/{UNKNOWN_ID}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Knowledge page not found"
