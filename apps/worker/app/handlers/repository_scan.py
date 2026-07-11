"""repository_scan handler — scan a registered repository into artifacts + DNA."""

from __future__ import annotations

from sqlalchemy.orm import Session

from aos_core.models import Job
from aos_core.services.scan import run_scan

from .registry import HandlerSpec


def run(job: Job, db: Session) -> dict:
    result = run_scan(job.repository_id, db)
    artifacts = result.get("artifacts") or []
    return {"scanned": job.repository_id, "artifact": artifacts[0]["name"] if artifacts else None}


SPEC = HandlerSpec(
    job_type="repository_scan",
    capability="scan",
    sensitivity="public",
    run=run,
    idempotency_strategy="naturally_idempotent",  # run_scan upserts by repository
    result_schema=("scanned", "artifact"),
)
