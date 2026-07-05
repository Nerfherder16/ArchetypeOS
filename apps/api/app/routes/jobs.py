import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Job, Project
from aos_core.services.jobs import enqueue_job

from ..schemas import JobCreate, JobRead

settings = get_settings()
router = APIRouter()


@router.post("/jobs", response_model=JobRead)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> Job:
    return enqueue_job(
        db,
        redis.Redis.from_url(settings.redis_url),
        job_type=payload.job_type,
        project_id=payload.project_id,
        repository_id=payload.repository_id,
        payload=payload.payload,
        priority=payload.priority,
    )


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/projects/{project_id}/jobs", response_model=list[JobRead])
def list_project_jobs(project_id: str, db: Session = Depends(get_db)) -> list[Job]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(Job)
        .filter(Job.project_id == project_id)
        .order_by(Job.queued_at.desc(), Job.id)
        .limit(50)
        .all()
    )
