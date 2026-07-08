"""Voice Command Center spine (AOS-VOICE-001).

A voice turn is text-in: a transcript (from Sotto STT) is classified into an
intent, persisted as a **review-first** Voice Inbox draft, and answered with a
short spoken reply. Per VOICE_COMMAND_CENTER.md, voice mode captures and prepares
work; it never performs destructive actions directly — every turn is a draft for
later approval in the dashboard.

The reply brain is Claude (the operator's choice), reached through the provider
abstraction. Both classification and reply are **fail-open**: if the provider
errors or returns junk, a deterministic keyword classifier and a templated reply
take over, so a turn is never lost and CI (deterministic provider) stays hermetic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING

from ..llm import Provider, get_provider
from ..models import Project, VoiceInboxItem

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session

# The intent taxonomy (VOICE_COMMAND_CENTER.md). Order matters for the keyword
# fallback: earlier, more specific intents win over later generic ones.
INTENT_TYPES: list[str] = [
    "pr_guardian_request",
    "repo_review_request",
    "research_request",
    "decision_draft",
    "architecture_note",
    "design_note",
    "risk_note",
    "experiment_request",
    "todo",
    "idea_capture",
]

# Intents whose action touches code, infrastructure, decisions, or repository
# state — always a review-first draft regardless of confidence.
_HIGH_STAKES_INTENTS = frozenset({
    "pr_guardian_request",
    "repo_review_request",
    "decision_draft",
    "architecture_note",
    "risk_note",
    "experiment_request",
})

# Below this confidence a turn is held for review even for low-stakes intents.
_AUTO_REVIEW_CONFIDENCE = 0.75

# Deterministic keyword classifier (fallback). First matching intent wins.
_INTENT_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("pr_guardian_request", ("guardian", "pr guardian", "review the pr", "review pr")),
    ("repo_review_request", ("review the repo", "repo review", "review the code", "code review", "review on the", "review of the", "scan the repo")),
    ("research_request", ("research", "look into", "investigate", "compare", "survey", "find out")),
    ("decision_draft", ("decide", "decision", "should we", "choose between", "pick between")),
    ("architecture_note", ("architecture", "system design", "diagram the", "how should the system")),
    ("design_note", ("design", "ui", "ux", "layout", "mockup")),
    ("risk_note", ("risk", "concern", "worried", "danger", "security issue")),
    ("experiment_request", ("experiment", "spike", "prototype", "try out", "proof of concept")),
    ("todo", ("todo", "to do", "remind me", "task:", "don't forget", "remember to")),
    ("idea_capture", ("idea", "capture", "thought", "what if", "note that")),
]

_SUGGESTED_ACTION: dict[str, str] = {
    "pr_guardian_request": "Queue a PR Guardian review request for later approval.",
    "repo_review_request": "Draft a repository review request for later approval.",
    "research_request": "Draft a research task for the Research Librarian.",
    "decision_draft": "Draft a decision record for review.",
    "architecture_note": "Draft an architecture note for the Architecture Cartographer.",
    "design_note": "Draft a design note for the Design Intelligence agent.",
    "risk_note": "Capture a risk note for review.",
    "experiment_request": "Draft an experiment request for review.",
    "todo": "Capture a to-do for later triage.",
    "idea_capture": "Capture the idea in the project inbox.",
}

_CLASSIFY_SYSTEM = (
    "You are the Voice Command Center intent router for an engineering platform. "
    "Classify one spoken transcript into exactly one intent and reply with a single "
    "JSON object and nothing else."
)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class IntentResult:
    intent: str
    confidence: float
    summary: str
    detected_project: str | None
    suggested_action: str


def _classify_prompt(transcript: str) -> str:
    return (
        "Transcript:\n"
        f"{transcript}\n\n"
        f"Allowed intents: {', '.join(INTENT_TYPES)}.\n"
        "Return JSON with keys: intent (one of the allowed intents), confidence "
        "(0..1), summary (one sentence), detected_project (project name or null), "
        "suggested_action (one sentence, a DRAFT — never a completed action)."
    )


def _clamp_confidence(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.5


def _summarize(transcript: str) -> str:
    text = " ".join(transcript.split())
    return text if len(text) <= 140 else text[:137].rstrip() + "..."


def _parse_intent_json(text: str, transcript: str) -> IntentResult | None:
    """Parse a model reply into an IntentResult, or None to trigger fallback."""
    match = _JSON_BLOCK.search(text or "")
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    intent = str(obj.get("intent", "")).strip()
    if intent not in INTENT_TYPES:
        return None
    detected_project = obj.get("detected_project")
    detected_project = str(detected_project).strip() if detected_project else None
    summary = str(obj.get("summary") or "").strip() or _summarize(transcript)
    suggested_action = str(obj.get("suggested_action") or "").strip() or _SUGGESTED_ACTION[intent]
    return IntentResult(
        intent=intent,
        confidence=_clamp_confidence(obj.get("confidence", 0.7)),
        summary=summary,
        detected_project=detected_project,
        suggested_action=suggested_action,
    )


def _keyword_fallback(transcript: str) -> IntentResult:
    lowered = transcript.lower()
    for intent, keywords in _INTENT_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return IntentResult(
                intent=intent,
                confidence=0.4,
                summary=_summarize(transcript),
                detected_project=None,
                suggested_action=_SUGGESTED_ACTION[intent],
            )
    return IntentResult(
        intent="idea_capture",
        confidence=0.3,
        summary=_summarize(transcript),
        detected_project=None,
        suggested_action=_SUGGESTED_ACTION["idea_capture"],
    )


def classify_intent(transcript: str, provider: Provider) -> IntentResult:
    """Classify a transcript, LLM-first with a deterministic keyword fallback."""
    try:
        result = provider.generate(system=_CLASSIFY_SYSTEM, prompt=_classify_prompt(transcript), max_tokens=300)
        parsed = _parse_intent_json(getattr(result, "text", ""), transcript)
        if parsed is not None:
            return parsed
    except Exception:
        pass
    return _keyword_fallback(transcript)


def generate_reply(transcript: str, intent: IntentResult, provider: Provider) -> str:
    """A short spoken confirmation. Fail-open to a template on error / junk."""
    template = f"Captured a {intent.intent.replace('_', ' ')} for review. {intent.suggested_action}".strip()
    try:
        prompt = (
            f"The user said: {transcript}\n"
            f"You classified this as {intent.intent}. Reply in one short spoken sentence "
            "confirming you captured it as a draft for their review. Plain text only."
        )
        result = provider.generate(
            system="You are a concise voice assistant confirming a captured request.",
            prompt=prompt,
            max_tokens=120,
        )
        text = (getattr(result, "text", "") or "").strip()
    except Exception:
        return template
    if not text or text[0] in "{[":
        return template
    return text if len(text) <= 400 else text[:397].rstrip() + "..."


def _resolve_project_id(db: "Session", project_id: str | None, detected_project: str | None) -> str | None:
    if project_id:
        return project_id
    if detected_project:
        match = (
            db.query(Project)
            .filter(Project.name.ilike(detected_project))
            .first()
        )
        if match is not None:
            return match.id
    return None


def process_voice_turn(
    db: "Session",
    *,
    transcript: str,
    source_device: str,
    provider: Provider,
    project_id: str | None = None,
) -> VoiceInboxItem:
    """Run one voice turn end to end and persist a review-first inbox draft."""
    intent = classify_intent(transcript, provider)
    reply = generate_reply(transcript, intent, provider)
    resolved_project_id = _resolve_project_id(db, project_id, intent.detected_project)
    required_review = intent.intent in _HIGH_STAKES_INTENTS or intent.confidence < _AUTO_REVIEW_CONFIDENCE

    item = VoiceInboxItem(
        project_id=resolved_project_id,
        transcript=transcript,
        summary=intent.summary,
        detected_intent=intent.intent,
        detected_project=intent.detected_project,
        suggested_action=intent.suggested_action,
        confidence=intent.confidence,
        required_review=required_review,
        review_state="pending",
        source_device=source_device or "unknown",
        reply_text=reply,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def voice_provider(settings, sink=None) -> Provider:
    """Build the voice reply/classify provider from ``settings.voice_llm_provider``.

    Reuses :func:`get_provider` via a shim so the same construction (claude_code /
    openai_compatible / deterministic) applies, without disturbing the reviewer's
    ``llm_provider``.
    """
    name = getattr(settings, "voice_llm_provider", "claude_code")
    shim = SimpleNamespace(
        llm_provider=name,
        llm_base_url=getattr(settings, "llm_base_url", "http://localhost:11434/v1"),
        llm_model=getattr(settings, "llm_model", "qwen2.5-coder:7b"),
        llm_api_key=getattr(settings, "llm_api_key", ""),
    )
    return get_provider(shim, sink=sink)
