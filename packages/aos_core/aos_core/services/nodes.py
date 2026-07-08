"""Node registry service (AOS-NODE-001).

Register execution nodes + their declared capabilities, and record heartbeats.
The control plane uses this to route capability-declared work to eligible nodes;
nodes are read-only by default and carry a sensitivity ceiling. Hermetic (pure
DB ops), so the API tests exercise it without any real node.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import Node, NodeCapability, NodeHeartbeat, now_utc

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


def register_node(
    db: "Session",
    *,
    name: str,
    node_type: str = "worker",
    endpoint: str | None = None,
    max_sensitivity: str = "public",
    write_access: bool = False,
    capabilities: list[dict] | None = None,
) -> Node:
    """Register (or re-register, by name) a node and replace its declared capabilities."""
    node = db.query(Node).filter(Node.name == name).first()
    if node is None:
        node = Node(name=name)
        db.add(node)
    node.node_type = node_type
    node.endpoint = endpoint
    node.max_sensitivity = max_sensitivity
    node.write_access = write_access
    node.node_status = "healthy"
    node.last_seen_at = now_utc()
    db.flush()

    if capabilities is not None:
        for existing in list(node.capabilities):
            db.delete(existing)
        for cap in capabilities:
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
