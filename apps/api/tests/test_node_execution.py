"""AOS-NODE-EXECUTION-001 — capability-aware routing wired to actual execution.

Routing was advisory (a GET /nodes/route calculation); a job ran on any worker off
one global queue. These tests prove the claim now enforces node assignment +
eligibility on top of the WP1 fencing, that origination persists the routing
decision, that a waiting job is re-routed when a node becomes eligible, and that an
unknown sensitivity fails CLOSED.
"""

from __future__ import annotations

from datetime import timedelta

from aos_core.models import Job, Node, NodeCapability, now_utc
from aos_core.services.jobs import (
    claim_job_for_node,
    enqueue_job,
    reroute_waiting_jobs,
)
from aos_core.sensitivity import sensitivity_rank, validate_sensitivity


class FakeRedis:
    def __init__(self):
        self.queue = []

    def lpush(self, name, value):
        self.queue.append((name, value))


def _node(db, name, *, caps, max_sensitivity="public", write=False, status="healthy", seen_delta=timedelta(0)):
    node = Node(
        name=name,
        node_type="worker",
        node_status=status,
        max_sensitivity=max_sensitivity,
        write_access=write,
        last_seen_at=now_utc() - seen_delta,
    )
    db.add(node)
    db.flush()
    for c in caps:
        db.add(NodeCapability(node_id=node.id, capability=c))
    db.commit()
    return node


def _job(db, *, capability=None, sensitivity="public", requires_write=False, assigned_node_id=None):
    job = Job(
        job_type="test",
        status="queued",
        required_capability=capability,
        sensitivity=sensitivity,
        requires_write=requires_write,
        assigned_node_id=assigned_node_id,
    )
    db.add(job)
    db.commit()
    return job


# --- fail-closed sensitivity (shared enum) ------------------------------------


def test_unknown_sensitivity_ranks_above_every_ceiling():
    # The old _rank returned 0 (=public) for an unknown value — fail OPEN. Now an
    # unknown value ranks above the top class, so it exceeds every node ceiling.
    assert sensitivity_rank("secret") == 5
    assert sensitivity_rank("typo-secret") == 6  # > any real ceiling → fails closed


def test_validate_sensitivity_rejects_unknown():
    validate_sensitivity("private")
    try:
        validate_sensitivity("secrett")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


# --- node-aware claim enforcement ---------------------------------------------


def test_node_without_capability_cannot_claim(db_session):
    node = _node(db_session, "n", caps=["digest"])
    job = _job(db_session, capability="scan")
    assert claim_job_for_node(db_session, job.id, "w1", node=node) is None


def test_private_work_rejected_by_public_only_node(db_session):
    node = _node(db_session, "n", caps=["scan"], max_sensitivity="public")
    job = _job(db_session, capability="scan", sensitivity="private")
    assert claim_job_for_node(db_session, job.id, "w1", node=node) is None


def test_write_work_rejected_by_read_only_node(db_session):
    node = _node(db_session, "n", caps=["scan"], write=False)
    job = _job(db_session, capability="scan", requires_write=True)
    assert claim_job_for_node(db_session, job.id, "w1", node=node) is None


def test_stale_node_cannot_claim(db_session):
    node = _node(db_session, "n", caps=["scan"], seen_delta=timedelta(minutes=10))
    job = _job(db_session, capability="scan")
    assert claim_job_for_node(db_session, job.id, "w1", node=node) is None


def test_unhealthy_node_cannot_claim(db_session):
    node = _node(db_session, "n", caps=["scan"], status="degraded")
    job = _job(db_session, capability="scan")
    assert claim_job_for_node(db_session, job.id, "w1", node=node) is None


def test_eligible_node_claims_its_assigned_job(db_session):
    node = _node(db_session, "n", caps=["scan"], max_sensitivity="private", write=True)
    job = _job(db_session, capability="scan", sensitivity="private", requires_write=True, assigned_node_id=None)
    claim = claim_job_for_node(db_session, job.id, "w1", node=node)
    assert claim is not None and claim.claim_token
    db_session.expire_all()  # the CAS updates via Core; refresh the ORM view (worker does db.refresh)
    row = db_session.get(Job, job.id)
    assert row.status == "running" and row.claimed_by == "w1"


def test_worker_cannot_claim_job_assigned_to_another_node(db_session):
    node_a = _node(db_session, "a", caps=["scan"])
    node_b = _node(db_session, "b", caps=["scan"])
    job = _job(db_session, capability="scan", assigned_node_id=node_a.id)
    # B is fully capable but the job is routed to A — B must not win it.
    assert claim_job_for_node(db_session, job.id, "wB", node=node_b) is None
    # A claims its own assigned job.
    assert claim_job_for_node(db_session, job.id, "wA", node=node_a) is not None


def test_nodeless_worker_cannot_claim_assigned_job(db_session):
    node_a = _node(db_session, "a", caps=["scan"])
    job = _job(db_session, capability="scan", assigned_node_id=node_a.id)
    # A worker with no node identity can only take unassigned jobs.
    assert claim_job_for_node(db_session, job.id, "generic", node=None) is None


# --- routing at origination + reroute -----------------------------------------


def test_origination_routes_to_eligible_node(db_session):
    node = _node(db_session, "n", caps=["noop"])  # 'test' job → capability 'noop'
    job = enqueue_job(db_session, FakeRedis(), job_type="test")
    row = db_session.get(Job, job.id)
    assert row.required_capability == "noop"       # derived server-side
    assert row.routing_status == "routed"
    assert row.assigned_node_id == node.id
    assert row.routing_explanation and "routed to n" in row.routing_explanation


def test_origination_with_no_eligible_node_waits(db_session):
    job = enqueue_job(db_session, FakeRedis(), job_type="test")  # no nodes registered
    row = db_session.get(Job, job.id)
    assert row.routing_status == "no_eligible_node"
    assert row.assigned_node_id is None
    assert row.status == "queued"  # visibly waiting, not lost


def test_reroute_assigns_waiting_job_when_node_appears(db_session):
    job = enqueue_job(db_session, FakeRedis(), job_type="test")  # waits (no node)
    assert db_session.get(Job, job.id).routing_status == "no_eligible_node"
    _node(db_session, "n", caps=["noop"])  # a capable node now registers
    assert reroute_waiting_jobs(db_session) == 1
    row = db_session.get(Job, job.id)
    assert row.routing_status == "routed" and row.assigned_node_id is not None


def test_reroute_reassigns_when_assigned_node_goes_stale(db_session):
    node = _node(db_session, "n", caps=["noop"])
    job = enqueue_job(db_session, FakeRedis(), job_type="test")
    assert db_session.get(Job, job.id).assigned_node_id == node.id
    # The node goes stale; a fresh capable node appears → re-routed to the fresh one.
    node.last_seen_at = now_utc() - timedelta(minutes=10)
    db_session.commit()
    fresh = _node(db_session, "fresh", caps=["noop"])
    reroute_waiting_jobs(db_session)
    assert db_session.get(Job, job.id).assigned_node_id == fresh.id


# --- API surface: sensitivity validation + routing exposure -------------------


def test_route_endpoint_rejects_unknown_sensitivity(client):
    assert client.get("/nodes/route", params={"sensitivity": "public"}).status_code == 200
    r = client.get("/nodes/route", params={"sensitivity": "not-a-class"})
    assert r.status_code == 422
    assert "unknown sensitivity" in r.json()["detail"]


def test_job_read_exposes_routing_fields(client):
    proj = client.post("/projects", json={"name": "P", "slug": "p-routing"}).json()
    created = client.post("/jobs", json={"project_id": proj["id"], "job_type": "test"})
    assert created.status_code in (200, 201), created.text
    job = client.get(f"/jobs/{created.json()['id']}").json()
    # Routing was derived + persisted at origination (no worker node in the test →
    # waiting), and is surfaced for the Control Tower.
    assert job["required_capability"] == "noop"
    assert job["routing_status"] in {"routed", "no_eligible_node"}
    assert "routing_explanation" in job
