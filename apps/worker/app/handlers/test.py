"""test handler — a trivial no-op job used for smoke checks."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from aos_core.models import Job

from .registry import HandlerSpec


def run(job: Job, db: Session) -> dict:
    return {
        "message": "test job completed",
        "worker": "archetypeos-worker",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


SPEC = HandlerSpec(
    job_type="test",
    capability="noop",
    sensitivity="public",
    run=run,
    idempotency_strategy="naturally_idempotent",
    result_schema=("message", "worker", "completed_at"),
)
