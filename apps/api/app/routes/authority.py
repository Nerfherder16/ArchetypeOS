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
from aos_core.models import ActionRequest, ApprovalRecord
from aos_core.services.authority import action_class_catalog, evaluate, list_pending_actions
from aos_core.services.authority_envelope import authorize_action, reject_action, request_action

from ..schemas import (
    ActionClassRead,
    ActionRequestCreate,
    ActionRequestRead,
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


# --- AOS-AUTHORITY-ENVELOPE-001 (P0-6): the mandatory execution envelope --------


@router.post("/authority/actions", response_model=ActionRequestRead)
def create_action_request(payload: ActionRequestCreate, db: Session = Depends(get_db)) -> ActionRequest:
    try:
        return request_action(
            db,
            action_class=payload.action_class,
            actor=payload.actor,
            agent=payload.agent,
            project_id=payload.project_id,
            target=payload.target,
            sensitivity=payload.sensitivity,
            requested_capability=payload.requested_capability,
            payload_digest=payload.payload_digest,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown action_class: {payload.action_class}") from exc


@router.post("/authority/actions/{action_id}/authorize", response_model=ActionRequestRead)
def authorize_action_request(action_id: str, db: Session = Depends(get_db)) -> ActionRequest:
    ar = authorize_action(db, action_id)
    if ar is None:
        raise HTTPException(status_code=404, detail="ActionRequest not found")
    return ar


@router.post("/authority/actions/{action_id}/reject", response_model=ActionRequestRead)
def reject_action_request(action_id: str, db: Session = Depends(get_db)) -> ActionRequest:
    ar = reject_action(db, action_id)
    if ar is None:
        raise HTTPException(status_code=404, detail="ActionRequest not found")
    return ar


@router.get("/authority/actions/{action_id}", response_model=ActionRequestRead)
def get_action_request(action_id: str, db: Session = Depends(get_db)) -> ActionRequest:
    ar = db.get(ActionRequest, action_id)
    if ar is None:
        raise HTTPException(status_code=404, detail="ActionRequest not found")
    return ar
