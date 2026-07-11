"""research_run handler — execute a persisted research plan through its phases."""

from __future__ import annotations

from sqlalchemy.orm import Session

from aos_core.models import Job, ResearchPlan, ResearchRun
from aos_core.services.research_run import execute_research_run

from .registry import HandlerSpec


def run(job: Job, db: Session) -> dict:
    existing = db.query(ResearchRun).filter(ResearchRun.job_id == job.id).first()
    if existing is not None:
        return {
            "run_id": existing.id,
            "confidence": existing.confidence,
            "open_questions": len(existing.open_questions),
        }
    plan_id = (job.payload or {}).get("plan_id", "")
    plan = db.get(ResearchPlan, plan_id)
    if plan is None:
        raise ValueError(f"research plan {plan_id!r} not found")
    run_row = execute_research_run(db, plan, job_id=job.id)
    return {
        "run_id": run_row.id,
        "confidence": run_row.confidence,
        "open_questions": len(run_row.open_questions),
    }


SPEC = HandlerSpec(
    job_type="research_run",
    capability="research",
    sensitivity="public",
    run=run,
    idempotency_strategy="origin_job_id",
    result_schema=("run_id", "confidence", "open_questions"),
)
