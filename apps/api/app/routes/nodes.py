"""Node registry routes (AOS-NODE-001; AOS-NODE-IDENTITY-001).

Enroll execution nodes (operator-approved, issues a credential), receive
authenticated heartbeats, self-register capabilities (non-escalating), and
list/inspect nodes. A node presents its token (``X-Node-Token``) on heartbeat so
an unauthenticated client can no longer report false health (finding P0-5); only
enrollment grants ``write_access`` / a higher ``max_sensitivity``.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import Node
from aos_core.services.node_identity import enroll_node, verify_node_token
from aos_core.services.nodes import record_heartbeat, register_node

from ..schemas import (
    NodeEnrollRead,
    NodeHeartbeatCreate,
    NodeHeartbeatRead,
    NodeRead,
    NodeRegister,
)

router = APIRouter()


def require_node_token(
    node_id: str,
    x_node_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    """Reject a request that does not present the node's live credential (P0-5)."""
    if not verify_node_token(db, node_id, x_node_token):
        raise HTTPException(status_code=401, detail="Invalid or missing node token")
    return node_id


@router.post("/nodes/enroll", response_model=NodeEnrollRead)
def enroll(payload: NodeRegister, db: Session = Depends(get_db)) -> NodeEnrollRead:
    # Operator-approved: sets the operator policy (write_access / max_sensitivity)
    # and issues the credential. The token is returned ONCE.
    node, token = enroll_node(
        db,
        name=payload.name,
        node_type=payload.node_type,
        endpoint=payload.endpoint,
        max_sensitivity=payload.max_sensitivity,
        write_access=payload.write_access,
        capabilities=[cap.model_dump() for cap in payload.capabilities],
    )
    return NodeEnrollRead(**NodeRead.model_validate(node).model_dump(), token=token)


@router.post("/nodes/register", response_model=NodeRead)
def register(payload: NodeRegister, db: Session = Depends(get_db)) -> Node:
    # Self-register: capabilities/endpoint only. write_access / max_sensitivity in
    # the payload are IGNORED — a node cannot self-grant them (allow_policy=False).
    return register_node(
        db,
        name=payload.name,
        node_type=payload.node_type,
        endpoint=payload.endpoint,
        capabilities=[cap.model_dump() for cap in payload.capabilities],
    )


@router.post(
    "/nodes/{node_id}/heartbeat",
    response_model=NodeHeartbeatRead,
    dependencies=[Depends(require_node_token)],
)
def heartbeat(node_id: str, payload: NodeHeartbeatCreate, db: Session = Depends(get_db)):
    hb = record_heartbeat(db, node_id=node_id, health=payload.health, metrics=payload.metrics)
    if hb is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return hb


@router.get("/nodes", response_model=list[NodeRead])
def list_nodes(db: Session = Depends(get_db)) -> list[Node]:
    return db.query(Node).order_by(Node.created_at.desc(), Node.id).all()


@router.get("/nodes/{node_id}", response_model=NodeRead)
def get_node(node_id: str, db: Session = Depends(get_db)) -> Node:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node
