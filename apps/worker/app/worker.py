from __future__ import annotations
import logging
import os
import socket
import time
import redis
from aos_core.config import get_settings
from aos_core.database import SessionLocal
from aos_core.models import Job
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

# AOS-WORKER-HANDLERS-001 (finding P1-1): handlers live in app.handlers, one module
# per job type. The registry imports them and populates JOB_HANDLERS; adding a job
# type no longer edits this file. HandlerSpec/JOB_HANDLERS are re-exported so
# existing importers keep working.
from app.handlers.registry import HandlerSpec, JOB_HANDLERS, load_handlers, register_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("archetypeos.worker")
settings = get_settings()
MAX_ATTEMPTS = 3
# Identifies this worker process for lease ownership (finding P0-1 recovery).
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

load_handlers()  # populate JOB_HANDLERS from the per-type modules

__all__ = ["HandlerSpec", "JOB_HANDLERS", "register_handler", "run_job", "main", "QUEUE"]


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
