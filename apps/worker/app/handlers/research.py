"""research handler — gather a ranked research note over the project corpus."""

from __future__ import annotations

from sqlalchemy.orm import Session

from aos_core.models import Job, ResearchNote
from aos_core.services.llm_router import Sensitivity
from aos_core.services.research import research

from .registry import HandlerSpec


def run(job: Job, db: Session) -> dict:
    existing = db.query(ResearchNote).filter(ResearchNote.job_id == job.id).first()
    if existing is not None:
        return {"note_id": existing.id}
    payload = job.payload or {}
    sensitivity = Sensitivity(payload.get("sensitivity", "public"))
    note = research(
        db,
        project_id=job.project_id,
        question=payload.get("question", ""),
        sensitivity=sensitivity,
        job_id=job.id,
    )
    return {"note_id": note.id}


SPEC = HandlerSpec(
    job_type="research",
    capability="research",
    sensitivity="public",
    run=run,
    idempotency_strategy="origin_job_id",
    result_schema=("note_id",),
)
