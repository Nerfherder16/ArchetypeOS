from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import ImplementationPlan, Project
from aos_core.services.build_plan import approve_plan, plan_from_decision

from ..schemas import ImplementationPlanApprove, ImplementationPlanRead

router = APIRouter()


@router.post("/decisions/{decision_id}/plan", response_model=ImplementationPlanRead)
def draft_plan(decision_id: str, db: Session = Depends(get_db)) -> ImplementationPlan:
    # Service 404s a missing decision and 409s a decision that is not approved;
    # idempotent (one plan per decision).
    return plan_from_decision(db, decision_id=decision_id)


@router.get("/plans/{plan_id}", response_model=ImplementationPlanRead)
def get_plan(plan_id: str, db: Session = Depends(get_db)) -> ImplementationPlan:
    plan = db.get(ImplementationPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Implementation plan not found")
    return plan


@router.get("/projects/{project_id}/plans", response_model=list[ImplementationPlanRead])
def list_plans(project_id: str, db: Session = Depends(get_db)) -> list[ImplementationPlan]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(ImplementationPlan)
        .filter(ImplementationPlan.project_id == project_id)
        .order_by(ImplementationPlan.created_at.desc())
        .all()
    )


@router.post("/plans/{plan_id}/approve", response_model=ImplementationPlanRead)
def approve_plan_endpoint(
    plan_id: str, payload: ImplementationPlanApprove, db: Session = Depends(get_db)
) -> ImplementationPlan:
    # Service 404s a missing plan and 409s a plan that is not in 'draft'.
    return approve_plan(db, plan_id=plan_id, approver=payload.approver, rationale=payload.rationale)
