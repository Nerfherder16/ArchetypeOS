"""Authority action policy tests (AOS-AUTHORITY-001, eval Finding 10).

Review-first must be enforced infrastructure, not convention. A central evaluator
answers requires_approval(action_type, target, sensitivity, capability) over an
ordered set of action classes, so no write/destructive action can bypass policy.
Hermetic: the policy is a pure function (service-level tests) and the API surface
exposes the catalog, the evaluator, and the pending-actions queue.
"""

from __future__ import annotations

import pytest


# --- service-level: the policy is a pure, total function -------------------


def test_write_and_destructive_classes_always_require_approval():
    from aos_core.services.authority import ActionClass, requires_approval

    for action in (
        ActionClass.REPO_WRITE,
        ActionClass.GIT_COMMIT,
        ActionClass.DEPLOY,
        ActionClass.DELETE_DESTRUCTIVE,
    ):
        # No sensitivity or capability may waive approval for a write/destructive act.
        assert requires_approval(action.value, sensitivity="public") is True
        assert requires_approval(action.value, sensitivity="secret", capability="god") is True


def test_safe_classes_never_require_approval():
    from aos_core.services.authority import ActionClass, requires_approval

    for action in (ActionClass.CAPTURE_ONLY, ActionClass.READ_ONLY, ActionClass.DRAFT_ARTIFACT):
        assert requires_approval(action.value, sensitivity="secret") is False


def test_external_network_requires_approval_only_for_sensitive_data():
    from aos_core.services.authority import requires_approval

    assert requires_approval("external_network", sensitivity="public") is False
    assert requires_approval("external_network", sensitivity="private") is True
    assert requires_approval("external_network", sensitivity="restricted") is True


def test_evaluate_returns_a_reasoned_decision():
    from aos_core.services.authority import evaluate

    decision = evaluate("git_commit", target="main", sensitivity="public")
    assert decision["requires_approval"] is True
    assert decision["action_type"] == "git_commit"
    assert isinstance(decision["action_level"], int)
    assert decision["reason"]


def test_unknown_action_type_is_rejected():
    from aos_core.services.authority import requires_approval

    with pytest.raises(ValueError):
        requires_approval("teleport")


# --- API surface -----------------------------------------------------------


def test_action_classes_catalog_lists_every_class(client):
    resp = client.get("/authority/action-classes")
    assert resp.status_code == 200, resp.text
    names = {c["name"] for c in resp.json()}
    assert {
        "capture_only",
        "read_only",
        "draft_artifact",
        "external_network",
        "repo_write",
        "git_commit",
        "deploy",
        "delete_destructive",
    } <= names
    # Ordered by escalating risk level, and each declares whether it always gates.
    levels = [c["level"] for c in resp.json()]
    assert levels == sorted(levels)


def test_evaluate_endpoint_answers_whether_approval_is_required(client):
    resp = client.post(
        "/authority/evaluate",
        json={"action_type": "deploy", "target": "teevee", "sensitivity": "public"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["requires_approval"] is True

    safe = client.post("/authority/evaluate", json={"action_type": "read_only"})
    assert safe.status_code == 200, safe.text
    assert safe.json()["requires_approval"] is False


def test_evaluate_endpoint_rejects_unknown_action_type(client):
    resp = client.post("/authority/evaluate", json={"action_type": "teleport"})
    assert resp.status_code == 422


def test_pending_authority_actions_are_listed(client):
    # Seed a pending ApprovalRecord directly, then confirm the queue surfaces it.
    from aos_core.database import get_db
    from aos_core.models import ApprovalRecord

    db = next(client.app.dependency_overrides[get_db]())
    record = ApprovalRecord(
        actor="worker",
        tool="git",
        action_level=5,
        requested_capability="git_commit",
        target="main",
        approval_status="pending",
    )
    db.add(record)
    db.commit()

    resp = client.get("/authority/pending")
    assert resp.status_code == 200, resp.text
    pending = resp.json()
    assert any(item["requested_capability"] == "git_commit" for item in pending)
    assert all(item["approval_status"] == "pending" for item in pending)
