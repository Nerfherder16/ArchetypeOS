import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Job, Project, ResearchPlan, ResearchRun
from aos_core.services.jobs import enqueue_job
from aos_core.services.llm_router import Sensitivity
from aos_core.services.research_plan import create_research_plan

from ..schemas import (
    JobRead,
    ResearchPlanCreate,
    ResearchPlanRead,
    ResearchRunRead,
    SourceDecisionRequest,
)

settings = get_settings()
router = APIRouter()


# AOS-RESEARCH-003 (Finding 15): a research plan is recorded before any source is
# fetched. POST builds the plan deterministically and persists it; GET lists /
# reads plans for auditability.
@router.post(
    "/projects/{project_id}/research-plans",
    response_model=ResearchPlanRead,
    status_code=201,
)
def create_plan(
    project_id: str, payload: ResearchPlanCreate, db: Session = Depends(get_db)
) -> ResearchPlan:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        sensitivity = Sensitivity(payload.sensitivity)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"unknown sensitivity {payload.sensitivity!r}")
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")
    return create_research_plan(db, project_id=project_id, question=question, sensitivity=sensitivity)


@router.get("/projects/{project_id}/research-plans", response_model=list[ResearchPlanRead])
def list_plans(project_id: str, db: Session = Depends(get_db)) -> list[ResearchPlan]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(ResearchPlan)
        .filter(ResearchPlan.project_id == project_id)
        .order_by(ResearchPlan.created_at.desc(), ResearchPlan.id)
        .all()
    )


@router.get("/research-plans/{plan_id}", response_model=ResearchPlanRead)
def get_plan(plan_id: str, db: Session = Depends(get_db)) -> ResearchPlan:
    plan = db.get(ResearchPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Research plan not found")
    return plan


# --- research runs (AOS-RESEARCH-003 executor, criteria 2-5) ----------------


@router.post("/research-plans/{plan_id}/run", response_model=JobRead)
def run_plan(plan_id: str, db: Session = Depends(get_db)) -> Job:
    plan = db.get(ResearchPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Research plan not found")
    # Executed asynchronously by the worker (mirrors council); the run appears
    # under GET /research-plans/{id}/runs once produced.
    return enqueue_job(
        db,
        redis.Redis.from_url(settings.redis_url),
        job_type="research_run",
        project_id=plan.project_id,
        payload={"plan_id": plan.id},
    )


@router.get("/research-plans/{plan_id}/runs", response_model=list[ResearchRunRead])
def list_runs(plan_id: str, db: Session = Depends(get_db)) -> list[ResearchRun]:
    if db.get(ResearchPlan, plan_id) is None:
        raise HTTPException(status_code=404, detail="Research plan not found")
    return (
        db.query(ResearchRun)
        .filter(ResearchRun.plan_id == plan_id)
        .order_by(ResearchRun.created_at.desc(), ResearchRun.id)
        .all()
    )


@router.get("/research-runs/{run_id}", response_model=ResearchRunRead)
def get_run(run_id: str, db: Session = Depends(get_db)) -> ResearchRun:
    run = db.get(ResearchRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found")
    return run


@router.post("/research-runs/{run_id}/sources/{source_ref:path}/decision", response_model=ResearchRunRead)
def decide_source(
    run_id: str, source_ref: str, payload: SourceDecisionRequest, db: Session = Depends(get_db)
) -> ResearchRun:
    """Operator override: accept/reject a considered source WITH a reason (criterion 2)."""
    run = db.get(ResearchRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found")
    if not payload.reason.strip():
        raise HTTPException(status_code=422, detail="a source decision must carry a reason")
    sources = list(run.sources)
    matched = False
    for source in sources:
        if source.get("ref") == source_ref:
            source["accepted"] = payload.accepted
            source["reason"] = payload.reason
            matched = True
    if not matched:
        raise HTTPException(status_code=404, detail="Source not found in this run")
    run.sources = sources
    db.commit()
    db.refresh(run)
    return run
