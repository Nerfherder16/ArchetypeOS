"""Capability-aware node routing (AOS-NODE-AGENT-001, finding P1-2).

The node registry existed but nothing connected it to execution — the worker did
not claim by capability or enforce the sensitivity/write policy the models carry.
This is the enforcement brain: given a job's requirements, it computes the
eligible nodes and a deterministic routing explanation the Control Tower can show
(*"routed to teevee because it has scan/git-read, permits private data, is
healthy, and does not require write access"*).

Eligibility = required capability ∈ node capabilities ∧ job sensitivity ≤ node
ceiling ∧ write requirement ≤ node policy ∧ node health fresh.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..models import Node

# Ordered sensitivity ladder (index = rank). A node may run work at or below its
# declared ``max_sensitivity`` ceiling, never above it.
SENSITIVITY_ORDER: tuple[str, ...] = (
    "public",
    "private",
    "internal",
    "confidential",
    "restricted",
    "secret",
)
DEFAULT_HEARTBEAT_FRESHNESS_SECONDS = 120


def _rank(sensitivity: str) -> int:
    try:
        return SENSITIVITY_ORDER.index(sensitivity)
    except ValueError:
        return 0


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class RoutingDecision:
    node_id: str | None
    node_name: str | None
    eligible_node_ids: tuple[str, ...]
    explanation: str


def node_eligibility(
    node: Node,
    *,
    required_capability: str | None,
    sensitivity: str,
    requires_write: bool,
    now: datetime,
    freshness_seconds: int = DEFAULT_HEARTBEAT_FRESHNESS_SECONDS,
) -> tuple[bool, str]:
    """Return ``(eligible, reason)`` for one node against a job's requirements."""
    capabilities = {cap.capability for cap in node.capabilities}
    if required_capability and required_capability not in capabilities:
        return False, f"missing capability {required_capability!r}"
    if _rank(sensitivity) > _rank(node.max_sensitivity):
        return False, f"sensitivity {sensitivity!r} exceeds node ceiling {node.max_sensitivity!r}"
    if requires_write and not node.write_access:
        return False, "job requires write access; node is read-only"
    if node.node_status != "healthy":
        return False, f"node health is {node.node_status!r}, not healthy"
    if node.last_seen_at is None:
        return False, "node has never heartbeated"
    if _as_utc(now) - _as_utc(node.last_seen_at) > timedelta(seconds=freshness_seconds):
        return False, "node heartbeat is stale"
    return True, "eligible"


def route_job(
    db,
    *,
    required_capability: str | None,
    sensitivity: str = "public",
    requires_write: bool = False,
    now: datetime,
    freshness_seconds: int = DEFAULT_HEARTBEAT_FRESHNESS_SECONDS,
) -> RoutingDecision:
    """Choose an eligible node for a job's requirements, with an explanation.

    Deterministic: among eligible nodes, the lexicographically-first name is
    chosen so the routing is reproducible.
    """
    nodes = db.query(Node).all()
    eligible: list[Node] = []
    reasons: list[str] = []
    for node in nodes:
        ok, reason = node_eligibility(
            node,
            required_capability=required_capability,
            sensitivity=sensitivity,
            requires_write=requires_write,
            now=now,
            freshness_seconds=freshness_seconds,
        )
        if ok:
            eligible.append(node)
        else:
            reasons.append(f"{node.name}: {reason}")

    if not eligible:
        detail = "; ".join(reasons) if reasons else "no nodes registered"
        return RoutingDecision(
            node_id=None,
            node_name=None,
            eligible_node_ids=(),
            explanation=(
                f"no eligible node for capability={required_capability!r} "
                f"sensitivity={sensitivity!r} write={requires_write} ({detail})"
            ),
        )

    chosen = sorted(eligible, key=lambda n: n.name)[0]
    caps = sorted({cap.capability for cap in chosen.capabilities})
    write_clause = "allows write access" if chosen.write_access else "does not require write access"
    explanation = (
        f"routed to {chosen.name} because it has {caps}, permits {chosen.max_sensitivity} data, "
        f"is {chosen.node_status}, and {write_clause}"
    )
    return RoutingDecision(
        node_id=chosen.id,
        node_name=chosen.name,
        eligible_node_ids=tuple(sorted(n.id for n in eligible)),
        explanation=explanation,
    )


__all__ = ["RoutingDecision", "node_eligibility", "route_job", "SENSITIVITY_ORDER"]
