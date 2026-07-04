from __future__ import annotations
from datetime import datetime, timezone
import logging
import time
import redis
from sqlalchemy import MetaData, Table, create_engine, update
from sqlalchemy.orm import sessionmaker
from .config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("archetypeos.worker")
settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
metadata = MetaData()
QUEUE = "archetypeos:jobs"


def jobs_table() -> Table:
    return Table("jobs", metadata, autoload_with=engine)


def mark_job(job_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    jobs = jobs_table()
    values: dict = {"status": status, "updated_at": now}
    if status == "running":
        values["started_at"] = now
        values["attempts"] = jobs.c.attempts + 1
    elif status in {"completed", "failed"}:
        values["result"] = result
        values["error"] = error
        values["finished_at"] = now
    with SessionLocal() as db:
        db.execute(update(jobs).where(jobs.c.id == job_id).values(**values))
        db.commit()


def run_job(job_id: str) -> None:
    mark_job(job_id, "running")
    result = {"message": "test job completed", "worker": "archetypeos-worker", "completed_at": datetime.now(timezone.utc).isoformat()}
    mark_job(job_id, "completed", result=result)


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
            mark_job(job_id, "failed", error=str(exc))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
