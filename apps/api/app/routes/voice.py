"""Voice Command Center routes (AOS-VOICE-001).

``POST /voice/turns`` runs a transcript through the voice spine and returns the
persisted review-first inbox draft (including the spoken reply). ``GET /voice/inbox``
lists recent drafts for the dashboard. The provider is built per-request via
``voice_provider`` (imported into this module so tests can patch it) and defaults
to Claude; classification/reply are fail-open so a turn is never lost.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Project, VoiceInboxItem
from aos_core.services.tts import synthesize_speech
from aos_core.services.voice import process_voice_turn, promote_inbox_item, voice_provider

from ..schemas import VoiceInboxItemRead, VoiceInboxUpdate, VoiceSpeakRequest, VoiceTurnCreate

settings = get_settings()
router = APIRouter()


@router.post("/voice/turns", response_model=VoiceInboxItemRead)
def create_voice_turn(payload: VoiceTurnCreate, db: Session = Depends(get_db)) -> VoiceInboxItem:
    if payload.project_id and not db.get(Project, payload.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return process_voice_turn(
        db,
        transcript=payload.transcript,
        source_device=payload.source_device,
        provider=voice_provider(settings),
        project_id=payload.project_id,
    )


@router.get("/voice/inbox", response_model=list[VoiceInboxItemRead])
def list_voice_inbox(db: Session = Depends(get_db)) -> list[VoiceInboxItem]:
    return (
        db.query(VoiceInboxItem)
        .order_by(VoiceInboxItem.created_at.desc(), VoiceInboxItem.id)
        .limit(50)
        .all()
    )


@router.patch("/voice/inbox/{item_id}", response_model=VoiceInboxItemRead)
def update_voice_inbox(
    item_id: str, payload: VoiceInboxUpdate, db: Session = Depends(get_db)
) -> VoiceInboxItem:
    """Approve / dismiss / re-open a review-first Voice Inbox draft.

    Review-first: this only transitions the item's ``review_state``. Promoting an
    approved draft into its concrete action (research task, decision, etc.) is
    AOS-VOICE-005 — approving here never executes anything on its own.
    """
    item = db.get(VoiceInboxItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Voice inbox item not found")
    item.review_state = payload.review_state
    # Approving a mapped intent promotes it into a concrete draft (idempotent,
    # no-op without a project/mapping) — AOS-VOICE-005.
    if payload.review_state == "approved":
        promote_inbox_item(db, item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/voice/speak")
def speak(payload: VoiceSpeakRequest) -> Response:
    """Synthesize a spoken reply server-side (Groq Orpheus) and return WAV.

    Returns 204 when TTS is unconfigured or synthesis fails (fail-open) so the
    CommandDeck falls back to the browser's speechSynthesis. The Groq key never
    leaves the server.
    """
    audio = synthesize_speech(payload.text, settings)
    if not audio:
        return Response(status_code=204)
    return Response(content=audio, media_type="audio/wav")
