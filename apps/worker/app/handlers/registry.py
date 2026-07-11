"""Job-handler registry (AOS-WORKER-HANDLERS-001, finding P1-1).

Each job type lives in its own module under ``app.handlers`` and exports one
immutable :class:`HandlerSpec`. The registry imports a known module list and
registers each spec, so adding a job type adds a module — it never edits a shared
source block in ``worker.py`` (the recurring merge-conflict hotspot, PR #179;
union-merging Python source is unsafe, LES-026/LES-L03).

``HandlerSpec`` now also declares the metadata the durable-jobs runtime and the
future node router need: ``timeout_seconds``, ``max_attempts``,
``idempotency_strategy``, and the ``result_schema`` keys — not just capability
and sensitivity.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from aos_core.models import Job

# How a handler guarantees safety under at-least-once redelivery (RFC-0014):
#   * "origin_job_id"       — output carries a unique job_id; get-or-create for the job
#   * "naturally_idempotent" — re-running produces no duplicate side effect
#   * "atomic_completion"   — side effect + job completion share one transaction
IDEMPOTENCY_STRATEGIES = frozenset(
    {"origin_job_id", "naturally_idempotent", "atomic_completion"}
)


@dataclass(frozen=True)
class HandlerSpec:
    """A registered job handler plus the metadata routing and retries need.

    ``capability`` and ``sensitivity`` let a capability-aware node router match a
    job to an eligible node (AOS-NODE-AGENT-001); ``run`` returns the result dict.
    """

    job_type: str
    capability: str
    sensitivity: str  # "public" | "private"
    run: Callable[[Job, Session], dict]
    timeout_seconds: int = 300
    max_attempts: int = 3
    idempotency_strategy: str = "atomic_completion"
    result_schema: tuple[str, ...] = field(default=())


JOB_HANDLERS: dict[str, HandlerSpec] = {}


def register_handler(spec: HandlerSpec) -> None:
    JOB_HANDLERS[spec.job_type] = spec


# The known handler modules. Adding a job type = add a module + this one line.
_HANDLER_MODULES: tuple[str, ...] = (
    "repository_scan",
    "project_digest",
    "council_review",
    "research",
    "research_run",
    "test",
)


def load_handlers() -> dict[str, HandlerSpec]:
    """Import every handler module and register its ``SPEC``; return the registry."""
    for name in _HANDLER_MODULES:
        module = importlib.import_module(f"app.handlers.{name}")
        register_handler(module.SPEC)
    return JOB_HANDLERS


__all__ = [
    "HandlerSpec",
    "JOB_HANDLERS",
    "register_handler",
    "load_handlers",
    "IDEMPOTENCY_STRATEGIES",
]
