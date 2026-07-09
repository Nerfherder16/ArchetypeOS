"""Per-project nightly-audit toggle (AOS-SELFHEAL, per-project MVP).

A project opts into the nightly audit loop with a single ``audits_enabled`` flag.
The dispatcher runs the repo-state (coherence) probe against every opted-in
project's repo and posts a heartbeat keyed to that project. These tests cover the
persistence + toggle route; the ProjectRead surface exposes the flag so the panel
can group heartbeats by project.
"""

from __future__ import annotations


def test_project_read_defaults_audits_disabled(client):
    created = client.post("/projects", json={"name": "Recall"})
    assert created.status_code == 200
    assert created.json()["audits_enabled"] is False


def test_patch_project_enables_audits(client):
    pid = client.post("/projects", json={"name": "Recall"}).json()["id"]

    resp = client.patch(f"/projects/{pid}", json={"audits_enabled": True})
    assert resp.status_code == 200
    assert resp.json()["audits_enabled"] is True

    # Persisted across a fresh read.
    assert client.get(f"/projects/{pid}").json()["audits_enabled"] is True

    # And back off again — the toggle is idempotent and reversible.
    off = client.patch(f"/projects/{pid}", json={"audits_enabled": False})
    assert off.json()["audits_enabled"] is False


def test_patch_project_unknown_is_404(client):
    resp = client.patch("/projects/does-not-exist", json={"audits_enabled": True})
    assert resp.status_code == 404


def test_patch_project_empty_body_is_noop(client):
    pid = client.post("/projects", json={"name": "Recall"}).json()["id"]
    client.patch(f"/projects/{pid}", json={"audits_enabled": True})

    # A patch that sets nothing leaves the flag untouched (partial update).
    resp = client.patch(f"/projects/{pid}", json={})
    assert resp.status_code == 200
    assert resp.json()["audits_enabled"] is True
