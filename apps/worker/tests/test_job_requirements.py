"""AOS-NODE-EXECUTION-001 — the server-owned job registry agrees with the handlers.

``enqueue_job`` derives a job's routing requirements from
``aos_core.services.job_requirements.JOB_REQUIREMENTS`` (server-side, never the
client). That registry must stay in agreement with what each worker ``HandlerSpec``
declares, so routing sends a job to a node that can actually run it.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./archetypeos_worker_dev.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:9999/0")

import app.worker as worker  # noqa: E402
from aos_core.services.job_requirements import JOB_REQUIREMENTS  # noqa: E402


def test_job_requirements_match_handlers():
    for job_type, spec in worker.JOB_HANDLERS.items():
        req = JOB_REQUIREMENTS.get(job_type)
        assert req is not None, f"job registry is missing handler job_type {job_type!r}"
        assert req.capability == spec.capability, (
            f"{job_type}: registry capability {req.capability!r} != handler {spec.capability!r}"
        )
        assert req.sensitivity == spec.sensitivity, (
            f"{job_type}: registry sensitivity {req.sensitivity!r} != handler {spec.sensitivity!r}"
        )


def test_every_registry_entry_has_a_handler():
    # No orphan registry rows — every declared requirement maps to a real handler.
    for job_type in JOB_REQUIREMENTS:
        assert job_type in worker.JOB_HANDLERS, f"registry has {job_type!r} with no handler"
