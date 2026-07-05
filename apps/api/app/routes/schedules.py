import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Job, Project, Schedule, now_utc
from aos_core.services.jobs import enqueue_job

from ..schemas import JobRead, ScheduleCreate, ScheduleRead, ScheduleUpdate

settings = get_settings()
router = APIRouter()


@router.post("/projects/{project_id}/schedules", response_model=ScheduleRead)
def create_schedule(project_id: str, payload: ScheduleCreate, db: Session = Depends(get_db)) -> Schedule:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    schedule = Schedule(
        project_id=project_id,
        name=payload.name,
        job_type=payload.job_type,
        interval_seconds=payload.interval_seconds,
        payload=payload.payload,
        enabled=payload.enabled,
        next_run_at=now_utc(),
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/projects/{project_id}/schedules", response_model=list[ScheduleRead])
def list_schedules(project_id: str, db: Session = Depends(get_db)) -> list[Schedule]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Schedule).filter(Schedule.project_id == project_id).order_by(Schedule.created_at.desc(), Schedule.id).all()


@router.get("/schedules/{schedule_id}", response_model=ScheduleRead)
def get_schedule(schedule_id: str, db: Session = Depends(get_db)) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.patch("/schedules/{schedule_id}", response_model=ScheduleRead)
def update_schedule(schedule_id: str, payload: ScheduleUpdate, db: Session = Depends(get_db)) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)) -> None:
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(schedule)
    db.commit()
    return None


@router.post("/schedules/{schedule_id}/run", response_model=JobRead)
def run_schedule_now(schedule_id: str, db: Session = Depends(get_db)) -> Job:
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    job = enqueue_job(
        db,
        redis.Redis.from_url(settings.redis_url),
        job_type=schedule.job_type,
        project_id=schedule.project_id,
        payload=schedule.payload,
    )
    schedule.last_run_at = now_utc()
    db.add(schedule)
    db.commit()
    return job
