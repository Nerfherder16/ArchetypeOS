"""Node registry API tests (AOS-NODE-001).

Register nodes + capabilities, receive heartbeats, list/inspect. Hermetic via the
`client` fixture (sqlite). Nodes are read-only by default; capabilities are
declared for future capability-aware routing.
"""

from __future__ import annotations


def _register(client, **over):
    body = {
        "name": "teevee-worker",
        "node_type": "worker",
        "endpoint": "http://100.123.29.114:8000",
        "capabilities": [
            {"capability": "scan", "version": "1"},
            {"capability": "council", "limits": {"max_tokens": 4000}},
        ],
    }
    body.update(over)
    return client.post("/nodes/register", json=body)


def test_register_node_defaults_read_only_and_records_capabilities(client):
    resp = _register(client)
    assert resp.status_code == 200, resp.text
    node = resp.json()
    assert node["name"] == "teevee-worker"
    assert node["write_access"] is False, "nodes are read-only by default"
    assert node["max_sensitivity"] == "public"
    assert node["node_status"] == "healthy"
    assert node["last_seen_at"]
    caps = {c["capability"] for c in node["capabilities"]}
    assert caps == {"scan", "council"}


def test_register_is_idempotent_by_name_and_replaces_capabilities(client):
    first = _register(client).json()
    # Re-register the same node with a different capability set + write access.
    second = _register(
        client, write_access=True, capabilities=[{"capability": "research"}]
    ).json()
    assert second["id"] == first["id"], "re-register by name updates the same node"
    # AOS-NODE-IDENTITY-001 (P0-5): self-register CANNOT self-grant write access;
    # the payload's write_access is ignored (only enrollment sets policy).
    assert second["write_access"] is False
    assert {c["capability"] for c in second["capabilities"]} == {"research"}
    # Listing shows exactly one node.
    listing = client.get("/nodes").json()
    assert len([n for n in listing if n["name"] == "teevee-worker"]) == 1


def _enroll(client, **over):
    body = {"name": "teevee-worker", "node_type": "worker", "capabilities": []}
    body.update(over)
    return client.post("/nodes/enroll", json=body)


def test_heartbeat_updates_node_status_and_last_seen(client):
    enrolled = _enroll(client).json()
    node_id, token = enrolled["id"], enrolled["token"]
    resp = client.post(
        f"/nodes/{node_id}/heartbeat",
        json={"health": "degraded", "metrics": {"vram_mb": 1800}},
        headers={"X-Node-Token": token},
    )
    assert resp.status_code == 200, resp.text
    hb = resp.json()
    assert hb["node_id"] == node_id
    assert hb["health"] == "degraded"
    assert hb["metrics"]["vram_mb"] == 1800
    # Rolled up onto the node.
    node = client.get(f"/nodes/{node_id}").json()
    assert node["node_status"] == "degraded"


def test_heartbeat_unknown_node_401(client):
    # No credential for the node → the token gate rejects (does not leak existence).
    resp = client.post("/nodes/00000000-0000-0000-0000-000000000000/heartbeat", json={"health": "healthy"})
    assert resp.status_code == 401


def test_get_unknown_node_404(client):
    assert client.get("/nodes/00000000-0000-0000-0000-000000000000").status_code == 404


def test_register_rejects_empty_name(client):
    assert _register(client, name="   ").status_code == 422
