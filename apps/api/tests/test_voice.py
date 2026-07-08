"""Voice Command Center service tests (AOS-VOICE-001).

The voice spine is text-in: a transcript is classified into an intent, persisted
as a review-first Voice Inbox item, and answered with a short spoken reply. All
hermetic — a fake provider stands in for Claude, and the keyword fallback path is
exercised directly so CI (deterministic provider) is covered too.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.llm import ProviderResult
from aos_core.models import Project, VoiceInboxItem
from aos_core.services.voice import (
    INTENT_TYPES,
    classify_intent,
    generate_reply,
    process_voice_turn,
)


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'voice.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
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


class _FakeProvider:
    """Returns a fixed text for every generate() — stands in for Claude."""

    name = "fake"

    def __init__(self, text: str) -> None:
        self._text = text

    def generate(self, *, system: str, prompt: str, max_tokens: int = 1024, response_format=None) -> ProviderResult:
        return ProviderResult(text=self._text, provider="fake", model="fake-1", finish_reason="stop")


def test_classify_intent_uses_valid_llm_json():
    payload = json.dumps({
        "intent": "research_request",
        "confidence": 0.9,
        "summary": "Wants a survey of vector databases.",
        "detected_project": "Recall",
        "suggested_action": "Draft a research task comparing vector DBs.",
    })
    result = classify_intent("look into the best vector database for us", _FakeProvider(payload))
    assert result.intent == "research_request"
    assert result.confidence == pytest.approx(0.9)
    assert result.detected_project == "Recall"
    assert "vector" in result.summary.lower()


def test_classify_intent_falls_back_to_keywords_when_llm_junk():
    # Provider returns non-JSON garbage → deterministic keyword classifier picks
    # the intent from the transcript, never raising.
    result = classify_intent(
        "research the tradeoffs between qdrant and pgvector",
        _FakeProvider("I am not JSON at all, sorry."),
    )
    assert result.intent == "research_request"
    assert result.intent in INTENT_TYPES
    assert 0.0 <= result.confidence <= 1.0


def test_classify_intent_invalid_intent_name_falls_back():
    # LLM returns well-formed JSON but an intent not in the taxonomy → fallback.
    payload = json.dumps({"intent": "make_coffee", "confidence": 0.99})
    result = classify_intent("capture an idea about a caching layer", _FakeProvider(payload))
    assert result.intent in INTENT_TYPES
    assert result.intent != "make_coffee"


def test_generate_reply_returns_prose_and_ignores_jsonish():
    ir = classify_intent("todo: email the vendor", _FakeProvider("not json"))
    prose = generate_reply("todo: email the vendor", ir, _FakeProvider("Got it — queued that to-do for review."))
    assert prose == "Got it — queued that to-do for review."
    # A JSON-looking model reply is rejected in favour of the template.
    templated = generate_reply("todo: email the vendor", ir, _FakeProvider('{"summary": "x"}'))
    assert not templated.startswith("{")
    assert templated


def test_process_voice_turn_persists_review_first_item(db):
    provider = _FakeProvider(json.dumps({
        "intent": "repo_review_request",
        "confidence": 0.95,
        "summary": "Asks for a Guardian review of the api service.",
        "suggested_action": "Queue a PR Guardian review of apps/api.",
    }))
    item = process_voice_turn(
        db,
        transcript="run a guardian review on the api service",
        source_device="pixel-8",
        provider=provider,
    )
    assert isinstance(item, VoiceInboxItem)
    assert item.id
    assert item.detected_intent == "repo_review_request"
    assert item.source_device == "pixel-8"
    assert item.review_state == "pending"
    # High-stakes intent stays a review-first draft even at high confidence.
    assert item.required_review is True
    assert item.reply_text  # a spoken reply was produced
    # Actually persisted.
    assert db.get(VoiceInboxItem, item.id) is not None


def test_process_voice_turn_links_known_project(db):
    project = Project(name="Recall", slug="recall")
    db.add(project)
    db.commit()
    item = process_voice_turn(
        db,
        transcript="capture an idea for the memory system",
        source_device="web",
        provider=_FakeProvider("not json"),
        project_id=project.id,
    )
    assert item.project_id == project.id
