from __future__ import annotations
from datetime import datetime, timezone
import logging
import time
import redis
from aos_core.config import get_settings
from aos_core.database import SessionLocal
from aos_core.models import Job
from aos_core.services.scan import run_scan
from aos_core.services.digest import build_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("archetypeos.worker")
settings = get_settings()
QUEUE = "archetypeos:jobs"
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
