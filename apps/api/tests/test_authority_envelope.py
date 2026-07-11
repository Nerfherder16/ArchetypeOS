"""AOS-AUTHORITY-ENVELOPE-001 (finding P0-6) — mandatory execution envelope.

The advisory authority evaluator becomes a structural gate: a high-impact action
must carry an authorized ActionRequest to run, low-impact actions auto-authorize,
and the job-origination chokepoint refuses an ungated high-impact action.
"""

from __future__ import annotations

import pytest

from aos_core.models import Job
from aos_core.services.authority_envelope import (
    authorize_action,
    reject_action,
    request_action,
)
from aos_core.services.jobs import enqueue_job


class FakeRedis:
    def __init__(self):
        self.queue = []

    def lpush(self, name, value):
        self.queue.append(value)


# --- envelope service ----------------------------------------------------------


def test_low_impact_action_auto_authorizes(db_session):
    ar = request_action(db_session, action_class="read_only")
    assert ar.policy_decision == "allow"
    assert ar.approval_state == "auto_approved"
    assert ar.execution_state == "authorized"


def test_high_impact_action_requires_approval(db_session):
    ar = request_action(db_session, action_class="repo_write", target="repo:x")
    assert ar.policy_decision == "needs_approval"
    assert ar.approval_state == "pending"
    assert ar.execution_state == "requested"

    authorized = authorize_action(db_session, ar.id, approver="op")
    assert authorized.approval_state == "approved"
    assert authorized.execution_state == "authorized"


def test_rejected_action_cannot_execute(db_session):
    ar = request_action(db_session, action_class="deploy")
    rejected = reject_action(db_session, ar.id)
    assert rejected.approval_state == "rejected"
    assert rejected.execution_state == "rejected"


def test_sensitive_egress_needs_approval_public_does_not(db_session):
    assert request_action(
        db_session, action_class="external_network", sensitivity="public"
    ).execution_state == "authorized"
    assert request_action(
        db_session, action_class="external_network", sensitivity="private"
    ).execution_state == "requested"


# --- the enqueue_job gate ------------------------------------------------------


def test_enqueue_low_impact_passes_through(db_session):
    # The default (read_only) — every current job type — is ungated.
    job = enqueue_job(db_session, FakeRedis(), job_type="repository_scan")
    assert db_session.get(Job, job.id) is not None


def test_enqueue_high_impact_without_envelope_is_rejected(db_session):
    with pytest.raises(PermissionError):
        enqueue_job(db_session, FakeRedis(), job_type="deploy_service", action_class="deploy")
    # No job was created.
    assert db_session.query(Job).count() == 0


def test_enqueue_high_impact_with_authorized_envelope_runs_and_consumes_it(db_session):
    ar = request_action(db_session, action_class="repo_write")
    authorize_action(db_session, ar.id)
    job = enqueue_job(
        db_session,
        FakeRedis(),
        job_type="apply_patch",
        action_class="repo_write",
        action_request=ar,
    )
    assert db_session.get(Job, job.id) is not None
    db_session.refresh(ar)
    assert ar.execution_state == "executed"  # the envelope is consumed by the job


def test_enqueue_high_impact_with_unauthorized_envelope_is_rejected(db_session):
    ar = request_action(db_session, action_class="repo_write")  # still pending
    with pytest.raises(PermissionError):
        enqueue_job(
            db_session, FakeRedis(), job_type="apply_patch", action_class="repo_write", action_request=ar
        )


def test_enqueue_envelope_class_mismatch_is_rejected(db_session):
    ar = request_action(db_session, action_class="deploy")
    authorize_action(db_session, ar.id)
    # An envelope authorized for 'deploy' cannot authorize a 'repo_write' job.
    with pytest.raises(PermissionError):
        enqueue_job(
            db_session, FakeRedis(), job_type="apply_patch", action_class="repo_write", action_request=ar
        )


# --- API surface ---------------------------------------------------------------


def test_action_request_api_flow(client):
    created = client.post("/authority/actions", json={"action_class": "repo_write", "target": "repo:y"})
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["approval_state"] == "pending"
    action_id = body["id"]

    authorized = client.post(f"/authority/actions/{action_id}/authorize")
    assert authorized.status_code == 200
    assert authorized.json()["execution_state"] == "authorized"

    fetched = client.get(f"/authority/actions/{action_id}")
    assert fetched.status_code == 200
    assert fetched.json()["approval_state"] == "approved"


def test_action_request_unknown_class_422(client):
    assert client.post("/authority/actions", json={"action_class": "bogus"}).status_code == 422
