"""AOS-AUTHORITY-HARDEN-001 — the envelope is one-use, bound, expiring, resumable.

The authority envelope existed but was reusable, unbound, never expired, and
distillation minted a fresh pending request on every retry with a hardcoded-public
sensitivity. These tests prove the atomic one-use consume, target binding, expiry,
and the distillation approve-and-resume flow (incl. repo-sensitivity gating).
"""

from __future__ import annotations

from datetime import timedelta

from aos_core.models import now_utc
from aos_core.services.authority_envelope import (
    authorize_action,
    consume_action,
    is_authorized,
    matches,
    request_action,
)


# --- one-use CAS consume ------------------------------------------------------


def test_consume_action_is_one_use(db_session):
    ar = request_action(db_session, action_class="repo_write")
    authorize_action(db_session, ar.id)
    assert consume_action(db_session, ar) is True
    db_session.commit()
    # A second consume of the same envelope fails — it is one-use.
    assert consume_action(db_session, ar) is False


def test_rejected_envelope_cannot_be_consumed(db_session):
    from aos_core.services.authority_envelope import reject_action

    ar = request_action(db_session, action_class="repo_write")
    reject_action(db_session, ar.id)
    assert consume_action(db_session, ar) is False


# --- binding + expiry ---------------------------------------------------------


def test_matches_rejects_wrong_repository_class_payload(db_session):
    ar = request_action(
        db_session, action_class="external_network", repository_id="repo-1", payload_digest="d1"
    )
    assert matches(ar, action_class="external_network", repository_id="repo-1", payload_digest="d1")
    assert not matches(ar, action_class="external_network", repository_id="repo-2")
    assert not matches(ar, action_class="repo_write", repository_id="repo-1")
    assert not matches(ar, action_class="external_network", repository_id="repo-1", payload_digest="d2")


def test_is_authorized_respects_expiry(db_session):
    past = now_utc() - timedelta(seconds=1)
    ar = request_action(db_session, action_class="repo_write", expires_at=past)
    authorize_action(db_session, ar.id)
    # Authorized but already expired → not usable, and cannot be consumed.
    assert is_authorized(ar) is False
    assert consume_action(db_session, ar) is False


# --- distillation approve-and-resume + repo sensitivity -----------------------


def _project(client):
    return client.post("/projects", json={"name": "P", "slug": "p-harden"}).json()["id"]


def _repo(client, project_id, *, name, sensitivity="public"):
    import pathlib

    from app.main import settings

    root = pathlib.Path(settings.repository_root)
    (root / name).mkdir(parents=True, exist_ok=True)
    (root / name / "README.md").write_text("# hi\n\nhello world", encoding="utf-8")
    return client.post(
        f"/projects/{project_id}/repositories",
        json={"name": name, "local_path": name, "sensitivity": sensitivity},
    ).json()["id"]


def test_public_repo_distill_auto_authorizes(client, tmp_path):
    from app.main import settings

    settings.knowledge_root = tmp_path
    pid = _project(client)
    rid = _repo(client, pid, name="pub", sensitivity="public")
    r = client.post(f"/repositories/{rid}/distill")
    assert r.status_code == 200, r.text


def test_private_repo_distill_requires_approval_then_resumes(client, tmp_path):
    from app.main import settings

    settings.knowledge_root = tmp_path
    pid = _project(client)
    rid = _repo(client, pid, name="priv", sensitivity="private")

    # First attempt: private egress requires approval → 403 with the pending id.
    r1 = client.post(f"/repositories/{rid}/distill")
    assert r1.status_code == 403, r1.text
    action_id = r1.json()["detail"]["action_request_id"]

    # Approve it (operator), then RESUME with the same id — no new pending envelope.
    client.post(f"/authority/actions/{action_id}/authorize")
    r2 = client.post(f"/repositories/{rid}/distill", params={"action_request_id": action_id})
    assert r2.status_code == 200, r2.text

    # The approved envelope is now consumed (one-use): a replay is refused.
    r3 = client.post(f"/repositories/{rid}/distill", params={"action_request_id": action_id})
    assert r3.status_code in (403, 409), r3.text


def test_distill_rejects_envelope_bound_to_another_repository(client, tmp_path):
    from app.main import settings

    settings.knowledge_root = tmp_path
    pid = _project(client)
    rid_a = _repo(client, pid, name="a", sensitivity="private")
    rid_b = _repo(client, pid, name="b", sensitivity="private")

    # Get + approve an envelope for repo A.
    action_id = client.post(f"/repositories/{rid_a}/distill").json()["detail"]["action_request_id"]
    client.post(f"/authority/actions/{action_id}/authorize")
    # Try to use A's envelope to distill repo B → refused (binding).
    r = client.post(f"/repositories/{rid_b}/distill", params={"action_request_id": action_id})
    assert r.status_code == 403, r.text
