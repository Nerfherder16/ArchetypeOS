import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import Artifact, Repository
from aos_core.services.scan import run_scan

from ..schemas import ArtifactRead, RepositoryScanRead

router = APIRouter()


@router.post("/repositories/{repository_id}/scan", response_model=RepositoryScanRead)
def scan_registered_repository(repository_id: str, db: Session = Depends(get_db)) -> dict:
    return run_scan(repository_id, db)


@router.get("/repositories/{repository_id}/scans", response_model=list[ArtifactRead])
def list_repository_scans(repository_id: str, db: Session = Depends(get_db)) -> list[Artifact]:
    if not db.get(Repository, repository_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    return (
        db.query(Artifact)
        .filter(Artifact.repository_id == repository_id, Artifact.artifact_type == "repository_scan")
        .order_by(Artifact.created_at.desc(), Artifact.id)
        .all()
    )


@router.get("/repositories/{repository_id}/scans/{artifact_id}", response_model=dict)
def get_repository_scan(repository_id: str, artifact_id: str, db: Session = Depends(get_db)) -> dict:
    if not db.get(Repository, repository_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    artifact = db.get(Artifact, artifact_id)
    if not artifact or artifact.repository_id != repository_id or artifact.artifact_type != "repository_scan":
        raise HTTPException(status_code=404, detail="Scan artifact not found")
    artifact_path = Path(artifact.path)
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Scan artifact file missing")
    return json.loads(artifact_path.read_text(encoding="utf-8"))
