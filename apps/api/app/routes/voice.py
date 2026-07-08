"""Voice Command Center routes (AOS-VOICE-001).

``POST /voice/turns`` runs a transcript through the voice spine and returns the
persisted review-first inbox draft (including the spoken reply). ``GET /voice/inbox``
lists recent drafts for the dashboard. The provider is built per-request via
``voice_provider`` (imported into this module so tests can patch it) and defaults
to Claude; classification/reply are fail-open so a turn is never lost.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Project, VoiceInboxItem
from aos_core.services.voice import process_voice_turn, voice_provider

from ..schemas import VoiceInboxItemRead, VoiceTurnCreate

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
