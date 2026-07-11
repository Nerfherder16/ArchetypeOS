"""Per-node service identity (AOS-NODE-IDENTITY-001, finding P0-5).

Nodes are enrolled by an operator, which issues a bearer token whose SHA-256 hash
is stored (never the token itself). A node presents its token on heartbeat/claim,
so an unauthenticated client can no longer report false health or impersonate a
node. Operator policy (``write_access`` / ``max_sensitivity``) is set only at
enrollment — a self-registering node cannot escalate it.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING

from ..models import Node, NodeCredential, now_utc
from .nodes import register_node

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_credential(db: "Session", node_id: str) -> str:
    """Issue (or rotate) a node's credential; return the PLAINTEXT token once."""
    token = secrets.token_urlsafe(32)
    cred = db.query(NodeCredential).filter(NodeCredential.node_id == node_id).one_or_none()
    now = now_utc()
    if cred is None:
        cred = NodeCredential(node_id=node_id, token_hash=_hash(token), issued_at=now)
        db.add(cred)
    else:
        cred.token_hash = _hash(token)
        cred.rotated_at = now
        cred.revoked_at = None
    db.commit()
    return token


def enroll_node(
    db: "Session",
    *,
    name: str,
    node_type: str = "worker",
    endpoint: str | None = None,
    max_sensitivity: str = "public",
    write_access: bool = False,
    capabilities: list[dict] | None = None,
) -> tuple[Node, str]:
    """Operator-approved enrollment: set operator policy AND issue a credential.

    Returns the node and its plaintext token (shown once). This is the only path
    that grants ``write_access`` / a higher ``max_sensitivity``.
    """
    node = register_node(
        db,
        name=name,
        node_type=node_type,
        endpoint=endpoint,
        max_sensitivity=max_sensitivity,
        write_access=write_access,
        capabilities=capabilities,
        allow_policy=True,
    )
    token = issue_credential(db, node.id)
    return node, token


def verify_node_token(db: "Session", node_id: str, token: str | None) -> bool:
    """True iff ``token`` matches the node's live (non-revoked) credential."""
    if not token:
        return False
    cred = db.query(NodeCredential).filter(NodeCredential.node_id == node_id).one_or_none()
    if cred is None or cred.revoked_at is not None:
        return False
    return secrets.compare_digest(cred.token_hash, _hash(token))


def revoke_credential(db: "Session", node_id: str) -> bool:
    """Revoke a node's credential. Returns True if one was revoked."""
    cred = db.query(NodeCredential).filter(NodeCredential.node_id == node_id).one_or_none()
    if cred is None:
        return False
    cred.revoked_at = now_utc()
    db.commit()
    return True


__all__ = ["issue_credential", "enroll_node", "verify_node_token", "revoke_credential"]
