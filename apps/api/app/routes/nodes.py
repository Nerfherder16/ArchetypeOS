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
from aos_core.models import Node, NodeCredential, now_utc
from aos_core.services.node_identity import (
    enroll_node,
    issue_credential,
    revoke_credential,
    verify_node_token,
)
from aos_core.services.nodes import record_heartbeat, register_node
from aos_core.services.routing import route_job

from ..security import require_operator

from ..schemas import (
    NodeEnrollRead,
    NodeHeartbeatCreate,
    NodeHeartbeatRead,
    NodeRead,
    NodeRegister,
    RoutingDecisionRead,
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
def enroll(
    payload: NodeRegister,
    db: Session = Depends(get_db),
    operator: str = Depends(require_operator),
) -> NodeEnrollRead:
    # Operator-approved (AOS-AUTH-BOUNDARY-001): only an authenticated operator may
    # grant policy (write_access / max_sensitivity) and issue the credential. The
    # token is returned ONCE.
    node, token = enroll_node(
        db,
        name=payload.name,
        node_type=payload.node_type,
        endpoint=payload.endpoint,
        max_sensitivity=payload.max_sensitivity,
        write_access=payload.write_access,
        capabilities=[cap.model_dump() for cap in payload.capabilities],
    )
    node.updated_by = operator
    db.commit()
    return NodeEnrollRead(**NodeRead.model_validate(node).model_dump(), token=token)


@router.post("/nodes/register", response_model=NodeRead)
def register(
    payload: NodeRegister,
    db: Session = Depends(get_db),
    x_node_token: str | None = Header(default=None),
) -> Node:
    # Self-register: capabilities/endpoint only. write_access / max_sensitivity in
    # the payload are IGNORED — a node cannot self-grant them (allow_policy=False).
    # AOS-AUTH-BOUNDARY-001: a node that has ALREADY been enrolled (holds a live
    # credential) can only be re-registered by presenting its node token, so an
    # anonymous client cannot replace an enrolled node's capabilities/endpoint by
    # name. A brand-new node (no credential yet) may still self-register to bootstrap.
    existing = db.query(Node).filter(Node.name == payload.name).one_or_none()
    if existing is not None:
        cred = (
            db.query(NodeCredential)
            .filter(NodeCredential.node_id == existing.id, NodeCredential.revoked_at.is_(None))
            .one_or_none()
        )
        if cred is not None and not verify_node_token(db, existing.id, x_node_token):
            raise HTTPException(
                status_code=401,
                detail="node is enrolled; re-registration requires its node token",
            )
    return register_node(
        db,
        name=payload.name,
        node_type=payload.node_type,
        endpoint=payload.endpoint,
        capabilities=[cap.model_dump() for cap in payload.capabilities],
    )


@router.post("/nodes/{node_id}/rotate-credential", response_model=NodeEnrollRead)
def rotate_credential(
    node_id: str,
    db: Session = Depends(get_db),
    operator: str = Depends(require_operator),
) -> NodeEnrollRead:
    # Operator-only: mint a fresh credential (invalidates the prior token — its hash
    # is replaced). The new token is returned ONCE.
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    token = issue_credential(db, node_id)
    node.updated_by = operator
    db.commit()
    db.refresh(node)
    return NodeEnrollRead(**NodeRead.model_validate(node).model_dump(), token=token)


@router.post("/nodes/{node_id}/revoke-credential", response_model=NodeRead)
def revoke_node_credential(
    node_id: str,
    db: Session = Depends(get_db),
    operator: str = Depends(require_operator),
) -> Node:
    # Operator-only: revoke a node's credential so it can no longer heartbeat/claim.
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    if not revoke_credential(db, node_id):
        raise HTTPException(status_code=404, detail="Node has no credential to revoke")
    node.updated_by = operator
    db.commit()
    db.refresh(node)
    return node


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


@router.get("/nodes/route", response_model=RoutingDecisionRead)
def route(
    capability: str | None = None,
    sensitivity: str = "public",
    write: bool = False,
    db: Session = Depends(get_db),
) -> RoutingDecisionRead:
    # Capability/sensitivity/write/health-aware routing with a deterministic
    # explanation the Control Tower can show (AOS-NODE-AGENT-001, finding P1-2).
    decision = route_job(
        db,
        required_capability=capability,
        sensitivity=sensitivity,
        requires_write=write,
        now=now_utc(),
    )
    return RoutingDecisionRead(
        node_id=decision.node_id,
        node_name=decision.node_name,
        eligible_node_ids=list(decision.eligible_node_ids),
        explanation=decision.explanation,
    )


@router.get("/nodes/{node_id}", response_model=NodeRead)
def get_node(node_id: str, db: Session = Depends(get_db)) -> Node:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node
