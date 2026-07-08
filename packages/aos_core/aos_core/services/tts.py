"""Groq Orpheus text-to-speech proxy (AOS-VOICE-004).

Synthesizes a short spoken reply server-side so the Groq key never reaches the
browser. Uses the OpenAI-compatible ``/audio/speech`` endpoint (Canopy Labs
Orpheus on GroqCloud): lowest round-trip in the free pool, no local GPU
contention. Fail-open: any missing key / network / non-audio response returns
``None`` so the CommandDeck falls back to the browser's speechSynthesis and a
spoken reply is never blocked. Orpheus caps input at 200 characters.

stdlib urllib only (matches OpenAICompatibleProvider), including the explicit
User-Agent that dodges Cloudflare error 1010 on the default ``Python-urllib`` UA.
"""

from __future__ import annotations

import json
import urllib.request

# Reuse the provider's UA so Cloudflare does not 403 the default urllib agent.
_USER_AGENT = "ArchetypeOS/1.0 (+voice-tts)"


def tts_configured(settings) -> bool:
    """True when a TTS key is set; otherwise callers use browser speech."""
    return bool(getattr(settings, "tts_api_key", ""))


def _post_audio(*, url: str, headers: dict[str, str], body: dict, timeout: float) -> bytes:
    """POST the speech request and return the raw audio bytes. Raises on failure."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def synthesize_speech(text: str, settings) -> bytes | None:
    """Return WAV bytes for ``text`` via Groq Orpheus, or None (fail-open).

    None is returned when TTS is unconfigured, the text is empty, or the provider
    errors — never raises, so a reply is never blocked on TTS.
    """
    if not tts_configured(settings):
        return None
    clean = " ".join((text or "").split())
    if not clean:
        return None
    max_chars = int(getattr(settings, "tts_max_chars", 200) or 200)
    clean = clean[:max_chars]
    body = {
        "model": getattr(settings, "tts_model", "canopylabs/orpheus-v1-english"),
        "voice": getattr(settings, "tts_voice", "austin"),
        "input": clean,
        "response_format": "wav",
    }
    headers = {
        "Authorization": f"Bearer {settings.tts_api_key}",
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
    }
    base = getattr(settings, "tts_base_url", "https://api.groq.com/openai/v1").rstrip("/")
    try:
        audio = _post_audio(url=f"{base}/audio/speech", headers=headers, body=body, timeout=20.0)
    except Exception:
        # Best-effort: any failure (network, HTTP, decode) → None so the caller
        # falls back to browser speech. TTS must never block or break a reply.
        return None
    return audio or None
