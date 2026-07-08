"""Groq Orpheus TTS service + route tests (AOS-VOICE-004).

The TTS proxy keeps the Groq key server-side: the browser POSTs reply text to
/voice/speak and gets WAV bytes back (or 204 → fall back to browser speech).
Everything here is hermetic — the Groq HTTP call is monkeypatched.
"""

from __future__ import annotations

from types import SimpleNamespace

from aos_core.services import tts as tts_service


def _settings(**over):
    base = dict(
        tts_base_url="https://api.groq.com/openai/v1",
        tts_model="canopylabs/orpheus-v1-english",
        tts_voice="austin",
        tts_api_key="",
        tts_max_chars=200,
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_tts_not_configured_without_key():
    assert tts_service.tts_configured(_settings()) is False
    assert tts_service.tts_configured(_settings(tts_api_key="gsk_x")) is True


def test_synthesize_returns_none_when_unconfigured():
    # No key → no network attempt, returns None (caller falls back to browser TTS).
    assert tts_service.synthesize_speech("hello", _settings()) is None


def test_synthesize_posts_and_returns_audio(monkeypatch):
    captured = {}

    def fake_post(*, url, headers, body, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        return b"RIFF....WAVEfake"

    monkeypatch.setattr(tts_service, "_post_audio", fake_post)
    audio = tts_service.synthesize_speech("Say this please", _settings(tts_api_key="gsk_x"))
    assert audio == b"RIFF....WAVEfake"
    assert captured["url"].endswith("/audio/speech")
    assert captured["body"]["model"] == "canopylabs/orpheus-v1-english"
    assert captured["body"]["voice"] == "austin"
    assert captured["body"]["input"] == "Say this please"
    assert captured["body"]["response_format"] == "wav"
    # Never log the key; but it must be sent as a bearer.
    assert captured["headers"]["Authorization"] == "Bearer gsk_x"
    assert "User-Agent" in captured["headers"]  # Cloudflare 1010 guard


def test_synthesize_truncates_to_max_chars(monkeypatch):
    captured = {}
    monkeypatch.setattr(tts_service, "_post_audio", lambda **kw: captured.update(kw) or b"wav")
    long_text = "x" * 500
    tts_service.synthesize_speech(long_text, _settings(tts_api_key="k", tts_max_chars=200))
    assert len(captured["body"]["input"]) == 200


def test_synthesize_fail_open_on_error(monkeypatch):
    def boom(**kw):
        raise RuntimeError("groq down")

    monkeypatch.setattr(tts_service, "_post_audio", boom)
    # A provider error must never raise to the caller — returns None.
    assert tts_service.synthesize_speech("hi", _settings(tts_api_key="k")) is None


# --- Route -------------------------------------------------------------------

def test_voice_speak_204_when_unconfigured(client):
    # Default test settings have no TTS key → 204, browser TTS takes over.
    resp = client.post("/voice/speak", json={"text": "read this aloud"})
    assert resp.status_code == 204


def test_voice_speak_returns_wav_when_configured(client, monkeypatch):
    import app.routes.voice as voice_route

    monkeypatch.setattr(voice_route, "synthesize_speech", lambda text, settings: b"RIFFfakewav")
    resp = client.post("/voice/speak", json={"text": "hello there"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/wav")
    assert resp.content == b"RIFFfakewav"


def test_voice_speak_rejects_empty_text(client):
    resp = client.post("/voice/speak", json={"text": "   "})
    assert resp.status_code == 422
