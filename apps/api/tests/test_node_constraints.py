"""AOS-NODE-CONSTRAINTS-001 (finding P1-3) — concurrency-safe node/heartbeat rows.

The node registry and audit-heartbeat board now carry the uniqueness the
query-then-insert services relied on: unique node name, unique (node_id,
capability), and a partial unique index enforcing one global (routine, NULL)
heartbeat. These prove the constraints reject duplicates and the services stay
idempotent.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from aos_core.models import AuditHeartbeat, Node, NodeCapability
from aos_core.services.audit_heartbeat import record_heartbeat
from aos_core.services.nodes import register_node


def test_node_name_unique(db_session):
    db_session.add(Node(name="teevee"))
    db_session.commit()
    db_session.add(Node(name="teevee"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_node_capability_unique(db_session):
    node = Node(name="n1")
    db_session.add(node)
    db_session.commit()
    db_session.add(NodeCapability(node_id=node.id, capability="scan"))
    db_session.commit()
    db_session.add(NodeCapability(node_id=node.id, capability="scan"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def _hb(routine, project_id):
    return AuditHeartbeat(
        routine=routine, project_id=project_id, heartbeat_status="clean", day="2026-07-11"
    )


def test_global_heartbeat_unique(db_session):
    # The partial unique index closes the NULL-is-distinct gap.
    db_session.add(_hb("self-audit", None))
    db_session.commit()
    db_session.add(_hb("self-audit", None))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_per_project_and_global_heartbeats_coexist(db_session):
    db_session.add(_hb("r", None))
    db_session.add(_hb("r", "00000000-0000-0000-0000-000000000001"))
    db_session.add(_hb("r", "00000000-0000-0000-0000-000000000002"))
    db_session.commit()
    assert db_session.query(AuditHeartbeat).filter(AuditHeartbeat.routine == "r").count() == 3


def test_register_node_idempotent_and_replaces_capabilities(db_session):
    first = register_node(
        db_session, name="box", write_access=True, capabilities=[{"capability": "scan"}], allow_policy=True
    )
    second = register_node(
        db_session, name="box", capabilities=[{"capability": "git-read"}]
    )
    assert first.id == second.id
    assert db_session.query(Node).filter(Node.name == "box").count() == 1
    assert {c.capability for c in second.capabilities} == {"git-read"}
    # AOS-NODE-IDENTITY-001 (P0-5): a plain re-register (allow_policy=False) does not
    # touch operator policy, so the write_access the operator granted persists.
    assert second.write_access is True


def test_register_node_dedupes_repeated_capability(db_session):
    node = register_node(
        db_session,
        name="dup",
        capabilities=[{"capability": "scan"}, {"capability": "scan"}],
    )
    assert [c.capability for c in node.capabilities] == ["scan"]


def test_record_heartbeat_idempotent_global(db_session):
    record_heartbeat(db_session, routine="self-audit", status="clean", day="2026-07-11")
    record_heartbeat(db_session, routine="self-audit", status="findings", day="2026-07-11")
    rows = (
        db_session.query(AuditHeartbeat)
        .filter(AuditHeartbeat.routine == "self-audit", AuditHeartbeat.project_id.is_(None))
        .all()
    )
    assert len(rows) == 1
    assert rows[0].heartbeat_status == "findings"
