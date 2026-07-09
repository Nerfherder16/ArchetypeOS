from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import Project, ResearchPlan
from aos_core.services.llm_router import Sensitivity
from aos_core.services.research_plan import create_research_plan

from ..schemas import ResearchPlanCreate, ResearchPlanRead

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
