"""AOS-AUTH-BOUNDARY-001 — operator + node authentication on the control plane.

Before this package, node enrollment and authority approve/reject had NO auth
dependency, and a node could re-register (replace) an enrolled node's capabilities
anonymously. These tests prove the operator gate (token / fail-closed / dev-mode),
actor recording, credential rotation/revocation, and node-credential binding.
"""

from __future__ import annotations

import pytest

from app import security as sec

OP = {"X-Operator-Token": "op-secret"}


@pytest.fixture()
def operator_token(monkeypatch):
    """Configure an operator token (locks the operator plane)."""
    monkeypatch.setattr(sec.settings, "operator_token", "op-secret")
    monkeypatch.setattr(sec.settings, "auth_dev_mode", False)
    return "op-secret"


def _enroll_body(name="n1"):
    return {"name": name, "node_type": "worker", "write_access": True,
            "max_sensitivity": "private", "capabilities": []}


# --- enrollment (operator-owned) ---------------------------------------------


def test_anonymous_enroll_rejected_when_token_set(client, operator_token):
    assert client.post("/nodes/enroll", json=_enroll_body()).status_code == 401
    assert client.post("/nodes/enroll", json=_enroll_body(), headers={"X-Operator-Token": "wrong"}).status_code == 401


def test_enroll_succeeds_with_operator_token_and_records_actor(client, operator_token):
    resp = client.post("/nodes/enroll", json=_enroll_body(),
                       headers={**OP, "X-Operator-Id": "alice"})
    assert resp.status_code == 200
    node = resp.json()
    assert node["updated_by"] == "alice"  # operator identity recorded
    assert node["write_access"] is True   # enrollment DOES grant policy


def test_enroll_fails_closed_when_no_token_and_dev_mode_off(client, monkeypatch):
    monkeypatch.setattr(sec.settings, "operator_token", "")
    monkeypatch.setattr(sec.settings, "auth_dev_mode", False)
    # No token configured + dev-mode disabled → deployed profile refuses (503).
    assert client.post("/nodes/enroll", json=_enroll_body()).status_code == 503


def test_enroll_open_in_dev_mode(client, monkeypatch):
    monkeypatch.setattr(sec.settings, "operator_token", "")
    monkeypatch.setattr(sec.settings, "auth_dev_mode", True)
    assert client.post("/nodes/enroll", json=_enroll_body()).status_code == 200


# --- authority approve / reject (operator-owned, actor recorded) --------------


def _pending_action(client):
    # A repo_write action always requires approval → stays pending.
    resp = client.post("/authority/actions", json={
        "action_class": "repo_write", "actor": "agent", "target": "repo:x", "sensitivity": "public"})
    assert resp.status_code == 200
    return resp.json()["id"]


def test_anonymous_authorize_rejected(client, operator_token):
    action_id = _pending_action(client)
    assert client.post(f"/authority/actions/{action_id}/authorize").status_code == 401


def test_authorize_records_operator_identity(client, operator_token):
    action_id = _pending_action(client)
    resp = client.post(f"/authority/actions/{action_id}/authorize",
                       headers={**OP, "X-Operator-Id": "bob"})
    assert resp.status_code == 200
    ar = resp.json()
    assert ar["execution_state"] == "authorized"
    assert ar["updated_by"] == "bob"  # the approver is recorded, not a literal "operator"


def test_anonymous_reject_rejected(client, operator_token):
    action_id = _pending_action(client)
    assert client.post(f"/authority/actions/{action_id}/reject").status_code == 401


# --- credential rotation / revocation -----------------------------------------


def test_rotate_credential_invalidates_prior_token(client, operator_token):
    enrolled = client.post("/nodes/enroll", json=_enroll_body("rot"), headers=OP).json()
    node_id, old = enrolled["id"], enrolled["token"]
    assert client.post(f"/nodes/{node_id}/heartbeat", json={"health": "healthy"},
                       headers={"X-Node-Token": old}).status_code == 200

    rotated = client.post(f"/nodes/{node_id}/rotate-credential", headers=OP)
    assert rotated.status_code == 200
    new = rotated.json()["token"]
    assert new != old
    # Old token no longer heartbeats; new one does.
    assert client.post(f"/nodes/{node_id}/heartbeat", json={"health": "healthy"},
                       headers={"X-Node-Token": old}).status_code == 401
    assert client.post(f"/nodes/{node_id}/heartbeat", json={"health": "healthy"},
                       headers={"X-Node-Token": new}).status_code == 200


def test_rotate_requires_operator(client, operator_token):
    enrolled = client.post("/nodes/enroll", json=_enroll_body("rot2"), headers=OP).json()
    assert client.post(f"/nodes/{enrolled['id']}/rotate-credential").status_code == 401


def test_revoke_credential_blocks_heartbeat(client, operator_token):
    enrolled = client.post("/nodes/enroll", json=_enroll_body("rev"), headers=OP).json()
    node_id, token = enrolled["id"], enrolled["token"]
    assert client.post(f"/nodes/{node_id}/revoke-credential", headers=OP).status_code == 200
    # A revoked credential can no longer heartbeat.
    assert client.post(f"/nodes/{node_id}/heartbeat", json={"health": "healthy"},
                       headers={"X-Node-Token": token}).status_code == 401


def test_revoke_requires_operator(client, operator_token):
    enrolled = client.post("/nodes/enroll", json=_enroll_body("rev2"), headers=OP).json()
    assert client.post(f"/nodes/{enrolled['id']}/revoke-credential").status_code == 401


# --- node-credential binding on re-registration -------------------------------


def test_enrolled_node_cannot_be_reregistered_without_its_token(client, operator_token):
    # An enrolled node (holds a credential) cannot have its capabilities/endpoint
    # replaced by an anonymous re-register — cross-node impersonation is blocked.
    enrolled = client.post("/nodes/enroll", json=_enroll_body("bound"), headers=OP).json()
    token = enrolled["token"]

    hijack = client.post("/nodes/register", json={
        "name": "bound", "node_type": "worker", "endpoint": "http://evil", "capabilities": []})
    assert hijack.status_code == 401

    # With the node's own token, re-registration is allowed.
    ok = client.post("/nodes/register", json={
        "name": "bound", "node_type": "worker", "endpoint": "http://ok", "capabilities": []},
        headers={"X-Node-Token": token})
    assert ok.status_code == 200


def test_new_node_can_still_self_register(client, operator_token):
    # Bootstrapping: a brand-new node (no credential yet) may self-register.
    resp = client.post("/nodes/register", json={
        "name": "fresh", "node_type": "worker", "capabilities": []})
    assert resp.status_code == 200
    assert resp.json()["write_access"] is False  # still non-escalating
