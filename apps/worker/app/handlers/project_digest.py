"""project_digest handler — build a project's nightly digest."""

from __future__ import annotations

from sqlalchemy.orm import Session

from aos_core.models import Job, NightlyDigest
from aos_core.services.digest import build_digest

from .registry import HandlerSpec


def run(job: Job, db: Session) -> dict:
    # Idempotent on redelivery (finding P0-3): a prior attempt that committed the
    # digest but crashed before completing the job returns the same digest here,
    # and the unique job_id constraint is the hard backstop.
    existing = db.query(NightlyDigest).filter(NightlyDigest.job_id == job.id).first()
    if existing is not None:
        return {"digest_id": existing.id, "summary": existing.summary}
    digest = build_digest(job.project_id, db)
    digest.job_id = job.id  # stamped before commit — atomic with the digest row
    db.add(digest)
    db.commit()
    db.refresh(digest)
    return {"digest_id": digest.id, "summary": digest.summary}


SPEC = HandlerSpec(
    job_type="project_digest",
    capability="digest",
    sensitivity="public",
    run=run,
    idempotency_strategy="origin_job_id",
    result_schema=("digest_id", "summary"),
)
