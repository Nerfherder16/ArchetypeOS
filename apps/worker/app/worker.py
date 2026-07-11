from __future__ import annotations
import logging
import os
import signal
import socket
import threading
import time
import redis
from aos_core.config import get_settings
from aos_core.database import SessionLocal
from aos_core.models import Job, Node
from aos_core.services.jobs import (
    DEFAULT_LEASE_SECONDS,
    QUEUE,
    Claim,
    claim_job_for_node,
    complete_job,
    dead_letter_job,
    dispatch_outbox,
    fail_job,
    reap_expired_leases,
    rearm_outbox,
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


class _HandlerTimeout(Exception):
    """Raised inside a handler when its per-spec ``timeout_seconds`` elapses."""


def _raise_timeout(signum, frame):  # noqa: ARG001 — signal handler signature
    raise _HandlerTimeout()


class LeaseRenewer(threading.Thread):
    """Background thread that renews a job's lease while its handler runs.

    AOS-JOB-FENCING-001: a handler running longer than the lease window would
    otherwise have its lease expire and be reaped mid-flight. This renews on a
    fraction of the lease in its OWN session (never the handler's), and stops when
    the handler returns (the caller's ``finally``). If a renewal fails the CAS
    (the job was reclaimed — token no longer matches), it records ``lost_ownership``
    and stops trying; the completion CAS will then also fail, so no stale result is
    committed.
    """

    def __init__(self, claim: Claim, *, interval: float, session_factory=SessionLocal) -> None:
        super().__init__(daemon=True)
        self._claim = claim
        self._interval = max(0.05, interval)
        self._session_factory = session_factory
        # NB: not ``_stop`` — that shadows threading.Thread's internal _stop() method.
        self._stop_event = threading.Event()
        self.lost_ownership = False

    def run(self) -> None:
        from aos_core.services.jobs import renew_lease

        while not self._stop_event.wait(self._interval):
            try:
                with self._session_factory() as db:
                    if not renew_lease(db, self._claim):
                        self.lost_ownership = True
                        return
            except Exception:  # noqa: BLE001 — renewal errors must not crash the worker
                logger.exception("lease renewal failed: %s", self._claim.job_id)
                return

    def stop(self) -> None:
        self._stop_event.set()


def _renew_interval(lease_seconds: int = DEFAULT_LEASE_SECONDS) -> float:
    """Renew at a third of the lease so a slow renewal still beats expiry."""
    return max(1.0, lease_seconds / 3.0)


def _run_with_timeout(spec: HandlerSpec, job: Job, db) -> dict:
    """Run a handler under its per-spec timeout, interrupting it if it overruns.

    Uses SIGALRM (``setitimer`` for sub-second precision) on the worker's main
    thread — the worker processes one job at a time on the main thread, so the
    alarm interrupts the synchronous ``spec.run`` cleanly. Off the main thread or
    on a platform without ``setitimer`` (e.g. Windows), the timeout is skipped and
    a warning is logged rather than silently pretending it is enforced.
    """
    timeout = spec.timeout_seconds
    on_main = threading.current_thread() is threading.main_thread()
    can_alarm = on_main and hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")
    if not timeout or timeout <= 0 or not can_alarm:
        if timeout and timeout > 0 and not can_alarm:
            logger.warning("timeout not enforceable (no SIGALRM/off main thread): %s", job.id)
        return spec.run(job, db)
    previous = signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, float(timeout))
    try:
        return spec.run(job, db)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _validate_result(spec: HandlerSpec, result) -> None:
    """Enforce ``HandlerSpec.result_schema`` — required keys must be present."""
    if not spec.result_schema:
        return
    if not isinstance(result, dict):
        raise ValueError(f"handler result is not a dict: {type(result).__name__}")
    missing = [key for key in spec.result_schema if key not in result]
    if missing:
        raise ValueError(f"handler result missing required keys: {missing}")


def _retry_or_dead_letter(db, job_id: str, claim: Claim, spec: HandlerSpec, error: str) -> None:
    """Fenced failure handling driven by ``spec.max_attempts`` (AOS-JOB-FENCING-001).

    Under the per-handler retry budget, the job is reset to ``queued`` (fenced) and
    redelivered through the durable outbox; over budget it is dead-lettered (fenced).
    Both transitions compare-and-swap on the claim token, so a stale worker that
    lost ownership cannot requeue or dead-letter a job another worker now holds.
    """
    db.rollback()  # clear any aborted handler transaction before the fenced write
    job = db.get(Job, job_id)
    attempts = job.attempts if job is not None else spec.max_attempts
    if attempts < spec.max_attempts:
        if release_for_retry(db, job_id, claim=claim):
            rearm_outbox(db, job_id)
            logger.warning("job re-queued (attempt %s/%s): %s", attempts, spec.max_attempts, job_id)
        else:
            logger.warning("retry skipped — ownership lost: %s", job_id)
    else:
        if dead_letter_job(db, job_id, error, claim=claim):
            logger.error("job dead-lettered after %s attempts: %s", attempts, job_id)
        else:
            logger.warning("dead-letter skipped — ownership lost: %s", job_id)


def _self_node(db, worker_id: str = WORKER_ID) -> Node | None:
    """This worker's registered node (by name == worker id), or None if unregistered.

    The worker registers itself as a node named ``WORKER_ID`` on startup
    (:func:`register_self`); resolving it here lets the claim enforce capability /
    sensitivity / write / health eligibility for THIS node. None (not yet registered)
    means the claim can still take unassigned jobs to bootstrap.
    """
    return db.query(Node).filter(Node.name == worker_id).one_or_none()


def run_job(job_id: str, *, worker_id: str = WORKER_ID) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("job not found: %s", job_id)
            return

        # Node-aware fenced claim (AOS-NODE-EXECUTION-001): the claim only succeeds
        # if this worker's node is the one routing assigned AND the node is still
        # eligible (capability/sensitivity/write/health) — revalidated at claim time,
        # not trusted from origination. A job routed to another node cannot be claimed
        # here even if its id was delivered to this worker. Falls back to an
        # unassigned-only claim when this worker is not yet a registered node (bootstrap
        # / tests). All the WP1 fencing guarantees still hold (fresh claim_token).
        node = _self_node(db, worker_id)
        claim = claim_job_for_node(db, job_id, worker_id, node=node)
        if claim is None:
            logger.info("job not claimed (not assigned/eligible or already leased): %s", job_id)
            return
        db.refresh(job)

        spec = JOB_HANDLERS.get(job.job_type)
        if spec is None:
            # Unknown job type fails clearly (was silently treated as a test job).
            logger.error("no handler registered for job_type %r: %s", job.job_type, job_id)
            fail_job(db, job_id, f"no handler registered for job_type {job.job_type!r}", claim=claim)
            return

        logger.info("dispatching job %s (type=%s capability=%s)", job_id, job.job_type, spec.capability)
        # Pass SessionLocal explicitly (resolved now, so a test that monkeypatches
        # worker.SessionLocal is honored by the renewer thread too).
        renewer = LeaseRenewer(claim, interval=_renew_interval(), session_factory=SessionLocal)
        renewer.start()
        try:
            result = _run_with_timeout(spec, job, db)
            _validate_result(spec, result)
            if not complete_job(db, job_id, result, claim=claim):
                # Lost the lease while running (reaped/reclaimed): another worker owns
                # this job now — discard our result rather than overwrite theirs.
                logger.warning("ownership lost before completion; result discarded: %s", job_id)
        except _HandlerTimeout:
            logger.error("handler timed out after %ss: %s", spec.timeout_seconds, job_id)
            _retry_or_dead_letter(db, job_id, claim, spec, f"handler exceeded timeout {spec.timeout_seconds}s")
        except Exception as exc:  # noqa: BLE001 — any handler error is fenced-failed here
            logger.exception("handler failed: %s", job_id)
            _retry_or_dead_letter(db, job_id, claim, spec, str(exc))
        finally:
            renewer.stop()
            renewer.join(timeout=2)


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


def node_capabilities() -> list[dict]:
    """This worker's capabilities — the union of its registered handlers' capabilities."""
    return [{"capability": c} for c in sorted({spec.capability for spec in JOB_HANDLERS.values()})]


def register_self() -> str:
    """Register this worker as a node with its handler capabilities (AOS-NODE-AGENT-001).

    Connects the worker to the node registry so the control plane can route
    capability-declared work to it and the Operations dashboard sees it live.
    Returns the node id.
    """
    from aos_core.services.nodes import record_heartbeat as node_heartbeat
    from aos_core.services.nodes import register_node

    with SessionLocal() as db:
        node = register_node(db, name=WORKER_ID, node_type="worker", capabilities=node_capabilities())
        node_heartbeat(db, node_id=node.id, health="healthy")
        return node.id


def heartbeat_self(node_id: str) -> None:
    """Emit a node heartbeat so the worker's freshness stays visible for routing."""
    from aos_core.services.nodes import record_heartbeat as node_heartbeat

    with SessionLocal() as db:
        node_heartbeat(db, node_id=node_id, health="healthy")


# How often the heavier reconciliation sweep (which scans the broker list) runs,
# versus the light per-tick drain + reap.
RECONCILE_INTERVAL_SECONDS = 60


def main() -> None:
    logger.info("worker starting")
    client = redis.Redis.from_url(settings.redis_url)
    try:
        self_node_id = register_self()  # join the node registry (AOS-NODE-AGENT-001)
        logger.info("registered as node %s (%s)", WORKER_ID, self_node_id)
    except Exception:  # noqa: BLE001 — never let node registration stop the worker
        logger.exception("node self-registration failed")
        self_node_id = None
    last_reconcile = time.monotonic()
    while True:
        try:
            if self_node_id is not None:
                heartbeat_self(self_node_id)
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
