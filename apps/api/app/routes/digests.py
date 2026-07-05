from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import NightlyDigest, Project
from aos_core.services.digest import build_digest

from ..schemas import NightlyDigestRead

router = APIRouter()


@router.post("/projects/{project_id}/digests", response_model=NightlyDigestRead)
def run_digest(project_id: str, db: Session = Depends(get_db)) -> NightlyDigest:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    digest = build_digest(project_id, db)
    db.add(digest)
    db.commit()
    db.refresh(digest)
    return digest


@router.get("/projects/{project_id}/digests", response_model=list[NightlyDigestRead])
def list_digests(project_id: str, db: Session = Depends(get_db)) -> list[NightlyDigest]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(NightlyDigest)
        .filter(NightlyDigest.project_id == project_id)
        .order_by(NightlyDigest.created_at.desc(), NightlyDigest.id)
        .all()
    )


@router.get("/digests/{digest_id}", response_model=NightlyDigestRead)
def get_digest(digest_id: str, db: Session = Depends(get_db)) -> NightlyDigest:
    digest = db.get(NightlyDigest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest
