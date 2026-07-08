from __future__ import annotations
from datetime import datetime, timezone
import logging
import time
import redis
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


def run_job(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("job not found: %s", job_id)
            return
        job_type = job.job_type
        repository_id = job.repository_id
        project_id = job.project_id

        mark_job(job_id, "running")

        if job_type == "repository_scan":
            result = run_scan(repository_id, db)
            artifacts = result.get("artifacts") or []
            mark_job(
                job_id,
                "completed",
                result={"scanned": repository_id, "artifact": artifacts[0]["name"] if artifacts else None},
            )
        elif job_type == "project_digest":
            digest = build_digest(project_id, db)
            db.add(digest)
            db.commit()
            db.refresh(digest)
            mark_job(job_id, "completed", result={"digest_id": digest.id, "summary": digest.summary})
        elif job_type == "council_review":
            question = (job.payload or {}).get("question", "")
            # Multi-model when enabled + pool ready (AOS-LLM-EVAL-001), AND
            # instrumented so each non-deterministic agent call records a usage
            # event (AOS-USAGE-001; deterministic CI provider skipped by the
            # wrapper → hermetic path unchanged). Ledger writes use a fresh session.
            provider = council_provider(
                settings, sink=make_ledger_sink(SessionLocal, settings, context="council")
            )
            review = run_council(db, project_id=project_id, question=question, provider=provider)
            review.job_id = job_id
            db.add(review)
            db.commit()
            mark_job(job_id, "completed", result={"review_id": review.id, "verdict": review.verdict})
        elif job_type == "research":
            payload = job.payload or {}
            question = payload.get("question", "")
            sensitivity = Sensitivity(payload.get("sensitivity", "public"))
            note = research(db, project_id=project_id, question=question, sensitivity=sensitivity)
            mark_job(job_id, "completed", result={"note_id": note.id})
        else:
            result = {
                "message": "test job completed",
                "worker": "archetypeos-worker",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
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
