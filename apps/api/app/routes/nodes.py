"""Node registry routes (AOS-NODE-001).

Register execution nodes + capabilities, receive heartbeats, and list/inspect
nodes for the Operations -> Nodes dashboard. The control plane (worker router,
AOS-WORKER-ROUTER-001) will match capability-declared jobs to eligible nodes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import Node
from aos_core.services.nodes import record_heartbeat, register_node

from ..schemas import NodeHeartbeatCreate, NodeHeartbeatRead, NodeRead, NodeRegister

router = APIRouter()


@router.post("/nodes/register", response_model=NodeRead)
def register(payload: NodeRegister, db: Session = Depends(get_db)) -> Node:
    return register_node(
        db,
        name=payload.name,
        node_type=payload.node_type,
        endpoint=payload.endpoint,
        max_sensitivity=payload.max_sensitivity,
        write_access=payload.write_access,
        capabilities=[cap.model_dump() for cap in payload.capabilities],
    )


@router.post("/nodes/{node_id}/heartbeat", response_model=NodeHeartbeatRead)
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
