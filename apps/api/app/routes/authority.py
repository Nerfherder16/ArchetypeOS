"""Authority action policy routes (AOS-AUTHORITY-001, eval Finding 10).

Exposes the central authority engine so review-first is enforceable infrastructure:
``GET /authority/action-classes`` lists the ordered action-class catalog,
``POST /authority/evaluate`` answers whether a given action needs approval (this is
how a route or client "asks the Authority Engine"), and ``GET /authority/pending``
surfaces the queue of actions awaiting a human decision for the dashboard. See
``docs/AUTHORITY_POLICY.md``.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import ApprovalRecord
from aos_core.services.authority import action_class_catalog, evaluate, list_pending_actions

from ..schemas import (
    ActionClassRead,
    ApprovalRecordRead,
    AuthorityDecisionRead,
    AuthorityEvaluateRequest,
)

router = APIRouter()


@router.get("/authority/action-classes", response_model=list[ActionClassRead])
def get_action_classes() -> list:
    return action_class_catalog()


@router.post("/authority/evaluate", response_model=AuthorityDecisionRead)
def evaluate_action(payload: AuthorityEvaluateRequest) -> dict:
    try:
        return evaluate(
            payload.action_type,
            target=payload.target,
            sensitivity=payload.sensitivity,
            capability=payload.capability,
        )
    except ValueError as exc:
        # Unknown action class — reject rather than silently allowing it through.
        raise HTTPException(status_code=422, detail=f"Unknown action_type: {payload.action_type}") from exc


@router.get("/authority/pending", response_model=list[ApprovalRecordRead])
def get_pending_actions(db: Session = Depends(get_db)) -> list[ApprovalRecord]:
    return list_pending_actions(db)
