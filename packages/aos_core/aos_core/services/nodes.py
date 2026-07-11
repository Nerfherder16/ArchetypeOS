"""Node registry service (AOS-NODE-001).

Register execution nodes + their declared capabilities, and record heartbeats.
The control plane uses this to route capability-declared work to eligible nodes;
nodes are read-only by default and carry a sensitivity ceiling. Hermetic (pure
DB ops), so the API tests exercise it without any real node.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from ..models import Node, NodeCapability, NodeHeartbeat, now_utc

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


def _get_or_create_node(db: "Session", name: str) -> Node:
    """Fetch a node by name, creating it if absent — safe under a concurrent race.

    The unique ``nodes.name`` constraint (AOS-NODE-CONSTRAINTS-001) means a racing
    insert loses with an ``IntegrityError`` instead of creating a duplicate; we
    catch it, roll back, and re-fetch the row the winner created.
    """
    node = db.query(Node).filter(Node.name == name).first()
    if node is not None:
        return node
    node = Node(name=name)
    db.add(node)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        node = db.query(Node).filter(Node.name == name).one()
    return node


def register_node(
    db: "Session",
    *,
    name: str,
    node_type: str = "worker",
    endpoint: str | None = None,
    max_sensitivity: str = "public",
    write_access: bool = False,
    capabilities: list[dict] | None = None,
    allow_policy: bool = False,
) -> Node:
    """Register (or re-register, by name) a node and replace its declared capabilities.

    ``allow_policy`` gates the operator-owned fields (``write_access``,
    ``max_sensitivity``): only enrollment sets them (AOS-NODE-IDENTITY-001, finding
    P0-5). A self-registering node cannot self-grant write access or raise its
    sensitivity ceiling — a new node stays read-only/public, and an existing node
    keeps the policy the operator enrolled it with.
    """
    node = _get_or_create_node(db, name)
    node.node_type = node_type
    node.endpoint = endpoint
    if allow_policy:
        node.max_sensitivity = max_sensitivity
        node.write_access = write_access
    node.node_status = "healthy"
    node.last_seen_at = now_utc()
    db.flush()

    if capabilities is not None:
        for existing in list(node.capabilities):
            db.delete(existing)
        db.flush()  # apply the deletes before re-inserting so the unique (node_id,
        # capability) index never sees the old + new rows at once
        # Dedupe by capability (last wins) — the unique constraint forbids repeats.
        by_capability = {cap["capability"]: cap for cap in capabilities}
        for cap in by_capability.values():
            db.add(
                NodeCapability(
                    node_id=node.id,
                    capability=cap["capability"],
                    capability_version=cap.get("version"),
                    limits=cap.get("limits") or {},
                )
            )
    db.commit()
    db.refresh(node)
    return node


def record_heartbeat(
    db: "Session", *, node_id: str, health: str = "healthy", metrics: dict | None = None
) -> NodeHeartbeat | None:
    """Record a heartbeat and roll it up onto the node (status + last_seen). None if the node is unknown."""
    node = db.get(Node, node_id)
    if node is None:
        return None
    heartbeat = NodeHeartbeat(node_id=node_id, health=health, observed_at=now_utc(), metrics=metrics or {})
    db.add(heartbeat)
    node.node_status = health
    node.last_seen_at = heartbeat.observed_at
    db.commit()
    db.refresh(heartbeat)
    return heartbeat
