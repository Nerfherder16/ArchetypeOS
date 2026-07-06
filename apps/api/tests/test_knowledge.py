"""Knowledge read path tests (AOS-KNOW-002 / RFC-0002 / RFC-0004)."""

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
    text = (KNOWLEDGE_ROOT / "wiki" / "lessons" / "index.md").read_text(encoding="utf-8")
    rows = parse_lessons_index(text)

    assert len(rows) == 11
    ids = [row["lesson_id"] for row in rows]
    assert ids == [f"LES-{n:03d}" for n in range(1, 12)]

    open_ids = [row["lesson_id"] for row in rows if row["status"] == "open"]
    assert open_ids == ["LES-007"]
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

    assert result["synced"] == 11
    assert result["created"] == 11
    assert result["updated"] == 0
    assert result["open_lessons"] == 1

    pages = db.query(KnowledgePage).all()
    assert len(pages) == 11
    assert all(page.page_type == "lesson" for page in pages)
    assert all(page.project_id is None for page in pages)
    assert all(page.vault_path.startswith("wiki/lessons/LES-") for page in pages)

    open_pages = db.query(KnowledgePage).filter(KnowledgePage.validation_state == "open").all()
    assert len(open_pages) == 1
    assert open_pages[0].vault_path == "wiki/lessons/LES-007.md"

    # Idempotent re-sync: update in place, no dupes
    rerun = sync_knowledge(db, KNOWLEDGE_ROOT)
    assert rerun["synced"] == 11
    assert rerun["created"] == 0
    assert rerun["updated"] == 11
    assert rerun["open_lessons"] == 1
    assert db.query(KnowledgePage).count() == 11


def test_sync_knowledge_missing_dir(db, tmp_path) -> None:
    result = sync_knowledge(db, tmp_path / "does-not-exist")
    assert result == {"synced": 0, "created": 0, "updated": 0, "open_lessons": 0}
    assert db.query(KnowledgePage).count() == 0


def test_knowledge_api(client: TestClient) -> None:
    settings.knowledge_root = KNOWLEDGE_ROOT

    synced = client.post("/knowledge/sync")
    assert synced.status_code == 200, synced.text
    counts = synced.json()
    assert counts == {"synced": 11, "created": 11, "updated": 0, "open_lessons": 1}

    listing = client.get("/knowledge/pages", params={"page_type": "lesson"})
    assert listing.status_code == 200, listing.text
    pages = listing.json()
    assert len(pages) == 11
    assert all(page["page_type"] == "lesson" for page in pages)
    assert all(page["project_id"] is None for page in pages)

    open_listing = client.get("/knowledge/pages", params={"validation_state": "open"})
    assert open_listing.status_code == 200, open_listing.text
    open_pages = open_listing.json()
    assert len(open_pages) == 1
    assert open_pages[0]["vault_path"] == "wiki/lessons/LES-007.md"

    page_id = open_pages[0]["id"]
    one = client.get(f"/knowledge/pages/{page_id}")
    assert one.status_code == 200, one.text
    assert one.json()["id"] == page_id

    missing = client.get(f"/knowledge/pages/{UNKNOWN_ID}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Knowledge page not found"
