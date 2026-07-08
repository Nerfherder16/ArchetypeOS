from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
import logging
import time
import redis
from sqlalchemy.orm import Session
from aos_core.config import get_settings
from aos_core.database import SessionLocal
from aos_core.models import Job
from aos_core.services.jobs import QUEUE
from aos_core.services.scan import run_scan
from aos_core.services.digest import build_digest
from aos_core.services.council import council_provider, run_council
from aos_core.services.llm_router import Sensitivity
from aos_core.services.research import research
from aos_core.services.usage import make_ledger_sink

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("archetypeos.worker")
settings = get_settings()
MAX_ATTEMPTS = 3


def mark_job(job_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = status
        job.updated_at = now
        if status == "running":
            job.started_at = now
            job.attempts = (job.attempts or 0) + 1
        elif status in {"completed", "failed"}:
            job.result = result
            job.error = error
            job.finished_at = now
        db.commit()


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
    digest = build_digest(job.project_id, db)
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
    provider = council_provider(settings, sink=make_ledger_sink(SessionLocal, settings, context="council"))
    review = run_council(db, project_id=job.project_id, question=question, provider=provider)
    review.job_id = job.id
    db.add(review)
    db.commit()
    return {"review_id": review.id, "verdict": review.verdict}


def _run_research(job: Job, db: Session) -> dict:
    payload = job.payload or {}
    sensitivity = Sensitivity(payload.get("sensitivity", "public"))
    note = research(db, project_id=job.project_id, question=payload.get("question", ""), sensitivity=sensitivity)
    return {"note_id": note.id}


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
register_handler(HandlerSpec("test", "noop", "public", _run_test))


def run_job(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("job not found: %s", job_id)
            return

        mark_job(job_id, "running")

        spec = JOB_HANDLERS.get(job.job_type)
        if spec is None:
            # Unknown job type fails clearly (was silently treated as a test job).
            logger.error("no handler registered for job_type %r: %s", job.job_type, job_id)
            mark_job(job_id, "failed", error=f"no handler registered for job_type {job.job_type!r}")
            return

        logger.info("dispatching job %s (type=%s capability=%s)", job_id, job.job_type, spec.capability)
        result = spec.run(job, db)
        mark_job(job_id, "completed", result=result)


def handle_failure(job_id: str, client: "redis.Redis", error: str) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        attempts = job.attempts if job is not None else MAX_ATTEMPTS
    if attempts < MAX_ATTEMPTS:
        client.lpush(QUEUE, job_id)
        mark_job(job_id, "queued")
        logger.warning("job re-enqueued (attempt %s of %s): %s", attempts, MAX_ATTEMPTS, job_id)
    else:
        mark_job(job_id, "failed", error=error)
        logger.error("job failed after %s attempts: %s", attempts, job_id)


def main() -> None:
    logger.info("worker starting")
    client = redis.Redis.from_url(settings.redis_url)
    while True:
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
