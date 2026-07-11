"""council_review handler — run the Agent Council over a project question."""

from __future__ import annotations

from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import SessionLocal
from aos_core.models import CouncilReview, Job
from aos_core.services.council import council_provider, run_council
from aos_core.services.usage import make_ledger_sink

from .registry import HandlerSpec

settings = get_settings()


def run(job: Job, db: Session) -> dict:
    question = (job.payload or {}).get("question", "")
    # Idempotent on redelivery (finding P0-3): return the review this job already
    # produced rather than run the (expensive) council again.
    existing = db.query(CouncilReview).filter(CouncilReview.job_id == job.id).first()
    if existing is not None:
        return {"review_id": existing.id, "verdict": existing.verdict}
    # Multi-model when enabled + pool ready (AOS-LLM-EVAL-001), instrumented so each
    # non-deterministic agent call records a usage event (AOS-USAGE-001; the
    # deterministic CI provider is skipped by the wrapper → hermetic path unchanged).
    # council_provider is resolved at call time so tests can monkeypatch it.
    provider = council_provider(settings, sink=make_ledger_sink(SessionLocal, settings, context="council"))
    review = run_council(db, project_id=job.project_id, question=question, provider=provider)
    review.job_id = job.id  # stamped before commit — atomic with the review row
    db.add(review)
    db.commit()
    return {"review_id": review.id, "verdict": review.verdict}


SPEC = HandlerSpec(
    job_type="council_review",
    capability="council",
    sensitivity="public",
    run=run,
    idempotency_strategy="origin_job_id",
    result_schema=("review_id", "verdict"),
)
