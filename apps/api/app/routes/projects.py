import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import Project

from ..schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "project"


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    slug = payload.slug or slugify(payload.name)
    project = Project(name=payload.name, slug=slug, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)
) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # Partial update: only apply fields the caller actually sent (an empty body is
    # a no-op). MVP surface is the per-project nightly-audit toggle.
    fields = payload.model_dump(exclude_unset=True)
    if "audits_enabled" in fields:
        project.audits_enabled = fields["audits_enabled"]
    db.commit()
    db.refresh(project)
    return project
