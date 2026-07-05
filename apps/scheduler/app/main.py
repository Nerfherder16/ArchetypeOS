from __future__ import annotations

import logging
import time

import redis

from aos_core.config import get_settings
from aos_core.database import SessionLocal
from aos_core.models import now_utc
from aos_core.services.scheduler import run_due_schedules

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("archetypeos.scheduler")
settings = get_settings()

TICK_SECONDS = 30


def main() -> None:
    logger.info("scheduler starting")
    client = redis.Redis.from_url(settings.redis_url)
    while True:
        try:
            with SessionLocal() as db:
                job_ids = run_due_schedules(db, client, now_utc())
            if job_ids:
                logger.info("enqueued %s job(s) from due schedules: %s", len(job_ids), job_ids)
        except Exception:
            logger.exception("scheduler tick failed")
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main()
