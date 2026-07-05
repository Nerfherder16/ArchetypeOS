from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import Artifact

from ..schemas import ArtifactCreate, ArtifactRead

router = APIRouter()


@router.post("/artifacts", response_model=ArtifactRead)
def create_artifact(payload: ArtifactCreate, db: Session = Depends(get_db)) -> Artifact:
    artifact = Artifact(**payload.model_dump())
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@router.get("/projects/{project_id}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(project_id: str, db: Session = Depends(get_db)) -> list[Artifact]:
    return db.query(Artifact).filter(Artifact.project_id == project_id).order_by(Artifact.created_at.desc()).all()
