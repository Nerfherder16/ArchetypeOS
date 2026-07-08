"""Voice Command Center API tests (AOS-VOICE-001).

POST /voice/turns accepts a transcript, runs it through the voice spine, and
returns the persisted review-first inbox item (with the spoken reply). The
provider is patched to a fake so no Claude CLI / network is touched.
"""

from __future__ import annotations

import json

from aos_core.llm import ProviderResult


class _FakeProvider:
    name = "fake"

    def __init__(self, text: str) -> None:
        self._text = text

    def generate(self, *, system: str, prompt: str, max_tokens: int = 1024, response_format=None) -> ProviderResult:
        return ProviderResult(text=self._text, provider="fake", model="fake-1", finish_reason="stop")


def _patch_provider(monkeypatch, text: str) -> None:
    import app.routes.voice as voice_route

    monkeypatch.setattr(voice_route, "voice_provider", lambda settings, sink=None: _FakeProvider(text))


def test_post_voice_turn_returns_reply_and_persists(client, monkeypatch):
    _patch_provider(monkeypatch, json.dumps({
        "intent": "research_request",
        "confidence": 0.88,
        "summary": "Wants a survey of message queues.",
        "suggested_action": "Draft a research task on message queues.",
    }))
    resp = client.post(
        "/voice/turns",
        json={"transcript": "research the best message queue for us", "source_device": "pixel-8"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["detected_intent"] == "research_request"
    assert body["source_device"] == "pixel-8"
    assert body["reply_text"]
    assert body["review_state"] == "pending"
    item_id = body["id"]

    # Persisted and listable.
    listing = client.get("/voice/inbox")
    assert listing.status_code == 200
    assert any(row["id"] == item_id for row in listing.json())


def test_post_voice_turn_rejects_empty_transcript(client, monkeypatch):
    _patch_provider(monkeypatch, "not json")
    resp = client.post("/voice/turns", json={"transcript": "   "})
    assert resp.status_code == 422


def test_post_voice_turn_unknown_project_404(client, monkeypatch):
    _patch_provider(monkeypatch, "not json")
    resp = client.post(
        "/voice/turns",
        json={"transcript": "capture an idea", "project_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404


def _make_item(client, monkeypatch) -> str:
    _patch_provider(monkeypatch, "not json")
    resp = client.post("/voice/turns", json={"transcript": "capture an idea about caching"})
    assert resp.status_code == 200
    return resp.json()["id"]


def test_patch_voice_inbox_approves(client, monkeypatch):
    item_id = _make_item(client, monkeypatch)
    resp = client.patch(f"/voice/inbox/{item_id}", json={"review_state": "approved"})
    assert resp.status_code == 200
    assert resp.json()["review_state"] == "approved"
    # Persisted.
    listing = client.get("/voice/inbox").json()
    assert next(r for r in listing if r["id"] == item_id)["review_state"] == "approved"


def test_patch_voice_inbox_dismisses(client, monkeypatch):
    item_id = _make_item(client, monkeypatch)
    resp = client.patch(f"/voice/inbox/{item_id}", json={"review_state": "dismissed"})
    assert resp.status_code == 200
    assert resp.json()["review_state"] == "dismissed"


def test_patch_voice_inbox_unknown_404(client):
    resp = client.patch(
        "/voice/inbox/00000000-0000-0000-0000-000000000000",
        json={"review_state": "approved"},
    )
    assert resp.status_code == 404


def test_patch_voice_inbox_invalid_state_422(client, monkeypatch):
    item_id = _make_item(client, monkeypatch)
    resp = client.patch(f"/voice/inbox/{item_id}", json={"review_state": "banana"})
    assert resp.status_code == 422
