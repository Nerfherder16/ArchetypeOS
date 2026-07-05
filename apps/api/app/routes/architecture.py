from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import ArchitectureEdge, ArchitectureNode, Project

from ..schemas import (
    ArchitectureCorrectionUpdate,
    ArchitectureEdgeRead,
    ArchitectureGraphRead,
    ArchitectureNodeRead,
)

router = APIRouter()


@router.get("/projects/{project_id}/architecture", response_model=ArchitectureGraphRead)
def get_project_architecture(project_id: str, repository_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    node_query = db.query(ArchitectureNode).filter(ArchitectureNode.project_id == project_id)
    edge_query = db.query(ArchitectureEdge).filter(ArchitectureEdge.project_id == project_id)
    if repository_id is not None:
        node_query = node_query.filter(ArchitectureNode.repository_id == repository_id)
        edge_query = edge_query.filter(ArchitectureEdge.repository_id == repository_id)
    nodes = node_query.order_by(ArchitectureNode.label, ArchitectureNode.id).all()
    edges = edge_query.order_by(ArchitectureEdge.type, ArchitectureEdge.id).all()
    return {"nodes": nodes, "edges": edges}


@router.patch("/architecture/nodes/{node_id}", response_model=ArchitectureNodeRead)
def correct_architecture_node(node_id: str, payload: ArchitectureCorrectionUpdate, db: Session = Depends(get_db)) -> ArchitectureNode:
    node = db.get(ArchitectureNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Architecture node not found")
    node.manual_correction = payload.manual_correction
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@router.patch("/architecture/edges/{edge_id}", response_model=ArchitectureEdgeRead)
def correct_architecture_edge(edge_id: str, payload: ArchitectureCorrectionUpdate, db: Session = Depends(get_db)) -> ArchitectureEdge:
    edge = db.get(ArchitectureEdge, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Architecture edge not found")
    edge.manual_correction = payload.manual_correction
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge
