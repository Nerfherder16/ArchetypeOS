import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Job, Project
from aos_core.services.jobs import enqueue_job

from ..schemas import JobRead, ResearchRequest

settings = get_settings()
router = APIRouter()


@router.post("/projects/{project_id}/research", response_model=JobRead)
def create_research(project_id: str, payload: ResearchRequest, db: Session = Depends(get_db)) -> Job:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return enqueue_job(
        db,
        redis.Redis.from_url(settings.redis_url),
        job_type="research",
        project_id=project_id,
        payload={"question": payload.question, "sensitivity": payload.sensitivity},
    )
