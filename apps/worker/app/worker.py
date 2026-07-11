from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
import logging
import os
import socket
import time
import redis
from sqlalchemy.orm import Session
from aos_core.config import get_settings
from aos_core.database import SessionLocal
from aos_core.models import CouncilReview, Job, NightlyDigest, ResearchNote, ResearchRun
from aos_core.services.jobs import (
    QUEUE,
    claim_job,
    complete_job,
    dead_letter_job,
    dispatch_outbox,
    fail_job,
    reap_expired_leases,
    reconcile,
    release_for_retry,
)
from aos_core.services.scan import run_scan
from aos_core.services.digest import build_digest
from aos_core.services.council import council_provider, run_council
from aos_core.services.llm_router import Sensitivity
from aos_core.services.research import research
from aos_core.services.research_run import execute_research_run
from aos_core.models import ResearchPlan
from aos_core.services.usage import make_ledger_sink

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("archetypeos.worker")
settings = get_settings()
MAX_ATTEMPTS = 3
# Identifies this worker process for lease ownership (finding P0-1 recovery).
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"


@dataclass
class HandlerSpec:
    """A registered job handler plus the metadata a future node router needs.

    AOS-WORKER-ROUTER-001: replaces the hardcoded if/elif dispatch. ``capability``
    and ``sensitivity`` are declared so a capability-aware Node router (AOS-NODE-001)
    can match a job to an eligible node; ``run`` returns the job's result dict.
    """

    job_type: str
    capability: str
    sensitivity: str  # "public" | "private"
    run: Callable[[Job, Session], dict]


JOB_HANDLERS: dict[str, HandlerSpec] = {}


def register_handler(spec: HandlerSpec) -> None:
    JOB_HANDLERS[spec.job_type] = spec


def _run_repository_scan(job: Job, db: Session) -> dict:
    result = run_scan(job.repository_id, db)
    artifacts = result.get("artifacts") or []
    return {"scanned": job.repository_id, "artifact": artifacts[0]["name"] if artifacts else None}


def _run_project_digest(job: Job, db: Session) -> dict:
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


def _run_council_review(job: Job, db: Session) -> dict:
    question = (job.payload or {}).get("question", "")
    # Multi-model when enabled + pool ready (AOS-LLM-EVAL-001), instrumented so each
    # non-deterministic agent call records a usage event (AOS-USAGE-001; the
    # deterministic CI provider is skipped by the wrapper → hermetic path unchanged).
    # council_provider is resolved at call time so tests can monkeypatch it.
    # Idempotent on redelivery (finding P0-3): return the review this job already
    # produced rather than run the (expensive) council again.
    existing = db.query(CouncilReview).filter(CouncilReview.job_id == job.id).first()
    if existing is not None:
        return {"review_id": existing.id, "verdict": existing.verdict}
    provider = council_provider(settings, sink=make_ledger_sink(SessionLocal, settings, context="council"))
    review = run_council(db, project_id=job.project_id, question=question, provider=provider)
    review.job_id = job.id  # stamped before commit — atomic with the review row
    db.add(review)
    db.commit()
    return {"review_id": review.id, "verdict": review.verdict}


def _run_research(job: Job, db: Session) -> dict:
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


def _run_research_run(job: Job, db: Session) -> dict:
    # Execute a persisted research plan through its phases (AOS-RESEARCH-003).
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
    run = execute_research_run(db, plan, job_id=job.id)
    return {"run_id": run.id, "confidence": run.confidence, "open_questions": len(run.open_questions)}


def _run_test(job: Job, db: Session) -> dict:
    return {
        "message": "test job completed",
        "worker": "archetypeos-worker",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


register_handler(HandlerSpec("repository_scan", "scan", "public", _run_repository_scan))
register_handler(HandlerSpec("project_digest", "digest", "public", _run_project_digest))
register_handler(HandlerSpec("council_review", "council", "public", _run_council_review))
register_handler(HandlerSpec("research", "research", "public", _run_research))
register_handler(HandlerSpec("research_run", "research", "public", _run_research_run))
register_handler(HandlerSpec("test", "noop", "public", _run_test))


def run_job(job_id: str, *, worker_id: str = WORKER_ID) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("job not found: %s", job_id)
            return

        # Take a lease via compare-and-swap. If another worker already holds a live
        # lease (or the reaper is mid-recovery), the claim loses and we drop the id
        # rather than run it twice (finding P0-1).
        if not claim_job(db, job_id, worker_id):
            logger.info("job not claimed (already leased): %s", job_id)
            return
        db.refresh(job)

        spec = JOB_HANDLERS.get(job.job_type)
        if spec is None:
            # Unknown job type fails clearly (was silently treated as a test job).
            logger.error("no handler registered for job_type %r: %s", job.job_type, job_id)
            fail_job(db, job_id, f"no handler registered for job_type {job.job_type!r}")
            return

        logger.info("dispatching job %s (type=%s capability=%s)", job_id, job.job_type, spec.capability)
        result = spec.run(job, db)
        complete_job(db, job_id, result)


def handle_failure(job_id: str, client: "redis.Redis", error: str) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        attempts = job.attempts if job is not None else MAX_ATTEMPTS
        if attempts < MAX_ATTEMPTS:
            # Release the lease so the retry can re-claim, then re-enqueue.
            release_for_retry(db, job_id)
            client.lpush(QUEUE, job_id)
            logger.warning("job re-enqueued (attempt %s of %s): %s", attempts, MAX_ATTEMPTS, job_id)
        else:
            dead_letter_job(db, job_id, error)
            logger.error("job dead-lettered after %s attempts: %s", attempts, job_id)


def drain_outbox(client: "redis.Redis") -> int:
    """Deliver any undelivered job-outbox rows to the queue (AOS-JOBS-RELIABILITY-001).

    Runs each worker tick so jobs whose immediate delivery was deferred (Redis was
    down when they were originated) are picked up once the broker is reachable
    again. Returns the number delivered.
    """
    with SessionLocal() as db:
        return dispatch_outbox(db, client)


def reap(client: "redis.Redis") -> int:
    """Recover jobs whose worker died mid-execution (expired lease); return count.

    Runs each worker tick so a crashed worker's in-flight jobs are re-queued once
    their lease lapses — the crash-recovery half of finding P0-1.
    """
    with SessionLocal() as db:
        return reap_expired_leases(db, client, max_attempts=MAX_ATTEMPTS)


def reconcile_now(client: "redis.Redis") -> dict:
    """Full reconciliation sweep (Slice 4): deliver, reap, and restore stranded jobs."""
    with SessionLocal() as db:
        return reconcile(db, client, max_attempts=MAX_ATTEMPTS)


# How often the heavier reconciliation sweep (which scans the broker list) runs,
# versus the light per-tick drain + reap.
RECONCILE_INTERVAL_SECONDS = 60


def main() -> None:
    logger.info("worker starting")
    client = redis.Redis.from_url(settings.redis_url)
    last_reconcile = time.monotonic()
    while True:
        try:
            drain_outbox(client)
            reap(client)
            if time.monotonic() - last_reconcile >= RECONCILE_INTERVAL_SECONDS:
                reconcile_now(client)
                last_reconcile = time.monotonic()
        except Exception:  # noqa: BLE001 — recovery sweeps must never crash the loop
            logger.exception("outbox drain / lease reap / reconcile failed")
        item = client.brpop(QUEUE, timeout=5)
        if not item:
            continue
        _, raw_job_id = item
        job_id = raw_job_id.decode("utf-8")
        try:
            run_job(job_id)
            logger.info("job completed: %s", job_id)
        except Exception as exc:
            logger.exception("job failed: %s", job_id)
            handle_failure(job_id, client, str(exc))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
