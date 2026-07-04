from __future__ import annotations
from datetime import datetime, timezone
import json
import logging
import time
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("archetypeos.worker")
settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
QUEUE = "archetypeos:jobs"


def mark_job(job_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        if status == "running":
            db.execute(text("update jobs set status=:status, started_at=:now, attempts=attempts + 1, updated_at=:now where id=:id"), {"status": status, "now": now, "id": job_id})
        elif status in {"completed", "failed"}:
            db.execute(
                text("update jobs set status=:status, result=:result, error=:error, finished_at=:now, updated_at=:now where id=:id"),
                {"status": status, "result": json.dumps(result) if result is not None else None, "error": error, "now": now, "id": job_id},
            )
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
