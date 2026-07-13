"""foundation_council_review handler — run the Council over a Foundation
candidate (RFC-0021, Foundation Intelligence Slice 4, AOS-COUNCIL-VALIDATION-API-001).

Mirrors ``council_review.py`` exactly, delegating to
``services/foundation_council.review_candidate`` (which itself reuses
``services/council.py``'s ``run_council`` — RFC-0016 C2: a candidate review
*is* a council review with a subject, no parallel evidence pipeline).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import SessionLocal
from aos_core.models import CouncilReview, Job
from aos_core.services.council import council_provider
from aos_core.services.foundation_council import review_candidate
from aos_core.services.usage import make_ledger_sink

from .registry import HandlerSpec

settings = get_settings()


def run(job: Job, db: Session) -> dict:
    candidate_id = (job.payload or {}).get("candidate_id", "")
    # Idempotent on redelivery (mirrors council_review.py's P0-3 fix): return the
    # review this job already produced rather than run the (expensive) council again.
    existing = db.query(CouncilReview).filter(CouncilReview.job_id == job.id).first()
    if existing is not None:
        return {"review_id": existing.id, "verdict": existing.verdict}
    # council_provider is resolved at call time so tests can monkeypatch it.
    provider = council_provider(settings, sink=make_ledger_sink(SessionLocal, settings, context="council"))
    review = review_candidate(db, candidate_id=candidate_id, provider=provider)
    review.job_id = job.id  # stamped before commit — atomic with the review row
    db.add(review)
    db.commit()
    return {"review_id": review.id, "verdict": review.verdict}


SPEC = HandlerSpec(
    job_type="foundation_council_review",
    capability="council",
    sensitivity="public",
    run=run,
    idempotency_strategy="origin_job_id",
    result_schema=("review_id", "verdict"),
)
