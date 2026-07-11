"""AOS-NODE-AGENT-001 (finding P1-2) — capability-aware node routing.

The node registry now drives execution: a job is routed to a node only if it has
the capability, permits the sensitivity, satisfies the write requirement, and is
freshly healthy — with a deterministic explanation.
"""

from __future__ import annotations

from datetime import timedelta

from aos_core.models import Node, NodeCapability, now_utc
from aos_core.services.routing import node_eligibility, route_job


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


def test_eligible_when_capability_sensitivity_write_and_health_match(db_session):
    node = _node(db_session, "teevee", caps=["scan", "git-read"], max_sensitivity="private", write=True)
    ok, reason = node_eligibility(
        node, required_capability="scan", sensitivity="private", requires_write=True, now=now_utc()
    )
    assert ok is True and reason == "eligible"


def test_missing_capability_is_ineligible(db_session):
    node = _node(db_session, "n", caps=["digest"])
    ok, reason = node_eligibility(
        node, required_capability="scan", sensitivity="public", requires_write=False, now=now_utc()
    )
    assert ok is False and "missing capability" in reason


def test_sensitivity_ceiling_enforced(db_session):
    node = _node(db_session, "n", caps=["scan"], max_sensitivity="public")
    ok, reason = node_eligibility(
        node, required_capability="scan", sensitivity="private", requires_write=False, now=now_utc()
    )
    assert ok is False and "exceeds node ceiling" in reason


def test_write_policy_enforced(db_session):
    node = _node(db_session, "n", caps=["scan"], write=False)
    ok, reason = node_eligibility(
        node, required_capability="scan", sensitivity="public", requires_write=True, now=now_utc()
    )
    assert ok is False and "read-only" in reason


def test_stale_or_unhealthy_node_is_ineligible(db_session):
    stale = _node(db_session, "stale", caps=["scan"], seen_delta=timedelta(minutes=10))
    ok, reason = node_eligibility(
        stale, required_capability="scan", sensitivity="public", requires_write=False, now=now_utc()
    )
    assert ok is False and "stale" in reason

    sick = _node(db_session, "sick", caps=["scan"], status="degraded")
    ok, reason = node_eligibility(
        sick, required_capability="scan", sensitivity="public", requires_write=False, now=now_utc()
    )
    assert ok is False and "not healthy" in reason


def test_route_job_picks_an_eligible_node_with_explanation(db_session):
    _node(db_session, "teevee", caps=["scan", "git-read"], max_sensitivity="private", write=False)
    _node(db_session, "laptop", caps=["digest"])  # ineligible: no scan

    decision = route_job(db_session, required_capability="scan", sensitivity="private", now=now_utc())
    assert decision.node_name == "teevee"
    assert decision.node_id is not None
    assert "routed to teevee because it has" in decision.explanation
    assert "permits private data" in decision.explanation


def test_route_job_explains_why_no_node_is_eligible(db_session):
    _node(db_session, "laptop", caps=["digest"], max_sensitivity="public")
    decision = route_job(db_session, required_capability="scan", sensitivity="private", now=now_utc())
    assert decision.node_id is None
    assert "no eligible node" in decision.explanation
    assert "laptop" in decision.explanation  # the per-node reason is surfaced


def test_route_endpoint(client):
    # Enroll a capable node, heartbeat it, then ask the router.
    enrolled = client.post(
        "/nodes/enroll",
        json={"name": "teevee", "max_sensitivity": "private", "capabilities": [{"capability": "scan"}]},
    ).json()
    client.post(
        f"/nodes/{enrolled['id']}/heartbeat",
        json={"health": "healthy"},
        headers={"X-Node-Token": enrolled["token"]},
    )
    resp = client.get("/nodes/route", params={"capability": "scan", "sensitivity": "private"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["node_name"] == "teevee"
    assert "routed to teevee" in body["explanation"]
