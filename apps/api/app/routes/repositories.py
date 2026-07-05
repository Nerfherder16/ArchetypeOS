from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Project, Repository, RepositoryDNA
from aos_core.repository_scanner import safe_repo_path

from ..schemas import RepositoryCreate, RepositoryDnaRead, RepositoryRead

settings = get_settings()
router = APIRouter()


@router.post("/projects/{project_id}/repositories", response_model=RepositoryRead)
def register_repository(project_id: str, payload: RepositoryCreate, db: Session = Depends(get_db)) -> Repository:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        safe_repo_path(settings.repository_root, payload.local_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repository = Repository(
        project_id=project_id,
        name=payload.name,
        local_path=payload.local_path,
        default_branch=payload.default_branch,
        remote_url=payload.remote_url,
        is_read_only=True,
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)
    return repository


@router.get("/projects/{project_id}/repositories", response_model=list[RepositoryRead])
def list_repositories(project_id: str, db: Session = Depends(get_db)) -> list[Repository]:
    return db.query(Repository).filter(Repository.project_id == project_id).order_by(Repository.created_at.desc()).all()


@router.get("/repositories/{repository_id}/dna", response_model=RepositoryDnaRead)
def get_repository_dna(repository_id: str, db: Session = Depends(get_db)) -> RepositoryDNA:
    repository = db.get(Repository, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repository.dna is None:
        raise HTTPException(status_code=404, detail="Repository has not been scanned")
    return repository.dna
