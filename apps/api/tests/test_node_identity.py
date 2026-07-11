"""AOS-NODE-IDENTITY-001 (finding P0-5) — per-node service identity.

Enrollment issues a credential and sets operator policy; heartbeat requires the
token; a self-registering node cannot escalate; credentials rotate and revoke.
"""

from __future__ import annotations


def _enroll(client, **over):
    body = {"name": "node-a", "node_type": "worker", "capabilities": []}
    body.update(over)
    return client.post("/nodes/enroll", json=body)


def test_enroll_issues_token_and_sets_operator_policy(client):
    resp = _enroll(client, write_access=True, max_sensitivity="private")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token"], "enrollment returns a one-time token"
    assert body["write_access"] is True, "enrollment (operator) sets policy"
    assert body["max_sensitivity"] == "private"


def test_heartbeat_requires_valid_token(client):
    enrolled = _enroll(client).json()
    node_id, token = enrolled["id"], enrolled["token"]

    # No token → 401.
    assert client.post(f"/nodes/{node_id}/heartbeat", json={"health": "healthy"}).status_code == 401
    # Wrong token → 401.
    bad = client.post(
        f"/nodes/{node_id}/heartbeat", json={"health": "healthy"}, headers={"X-Node-Token": "nope"}
    )
    assert bad.status_code == 401
    # Correct token → 200.
    ok = client.post(
        f"/nodes/{node_id}/heartbeat", json={"health": "healthy"}, headers={"X-Node-Token": token}
    )
    assert ok.status_code == 200


def test_self_register_cannot_escalate_policy(client):
    resp = client.post(
        "/nodes/register",
        json={"name": "node-b", "write_access": True, "max_sensitivity": "private", "capabilities": []},
    )
    assert resp.status_code == 200
    node = resp.json()
    assert node["write_access"] is False, "self-register cannot self-grant write access"
    assert node["max_sensitivity"] == "public", "self-register cannot raise the sensitivity ceiling"


def test_reenroll_rotates_token_and_rejects_the_old_one(client):
    enrolled = _enroll(client, name="node-c").json()
    node_id, token = enrolled["id"], enrolled["token"]
    assert client.post(
        f"/nodes/{node_id}/heartbeat", json={"health": "healthy"}, headers={"X-Node-Token": token}
    ).status_code == 200

    # Re-enroll rotates the credential (same node by name) → the old token dies.
    rotated = _enroll(client, name="node-c").json()["token"]
    assert rotated != token
    assert client.post(
        f"/nodes/{node_id}/heartbeat", json={"health": "healthy"}, headers={"X-Node-Token": token}
    ).status_code == 401, "the rotated-out (old) token is rejected"
    assert client.post(
        f"/nodes/{node_id}/heartbeat", json={"health": "healthy"}, headers={"X-Node-Token": rotated}
    ).status_code == 200


def test_verify_and_revoke_at_service_level(db_session):
    from aos_core.services.node_identity import (
        enroll_node,
        issue_credential,
        revoke_credential,
        verify_node_token,
    )

    node, token = enroll_node(db_session, name="svc-node")
    assert verify_node_token(db_session, node.id, token) is True
    assert verify_node_token(db_session, node.id, "wrong") is False

    # Rotation invalidates the old token.
    new_token = issue_credential(db_session, node.id)
    assert verify_node_token(db_session, node.id, token) is False
    assert verify_node_token(db_session, node.id, new_token) is True

    # Revocation blocks everything.
    assert revoke_credential(db_session, node.id) is True
    assert verify_node_token(db_session, node.id, new_token) is False
