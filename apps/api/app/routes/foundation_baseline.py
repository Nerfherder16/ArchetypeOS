"""HTTP API over the Foundation Baseline engine (RFC-0022, Foundation
Intelligence Slice 5, AOS-FOUNDATION-BASELINE-API-001).

Thin wrappers only — every route builds a request DTO, calls the matching
``services/foundation_baseline.py`` function, and returns a response DTO. No
business logic lives here (mirrors ``routes/foundation_council.py`` over
``services/foundation_council.py``).

Error-mapping discipline (matches ``routes/foundation_council.py``):

- A missing parent entity this route itself looks up (project/baseline)
  -> 404, raised here via ``db.get``.
- ``mint_baseline`` already 404s a missing run and 409s a run that is not
  ``selected`` or has no selected candidate itself -> these propagate
  straight through, unwrapped. It can also raise ``IllegalTransition`` (the
  prior-baseline supersede transition) -> caught here, 409.
- ``compare_baselines`` already 404s either missing baseline itself -> let it
  propagate unwrapped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import FoundationBaseline, FoundationBaselineElement, Project
from aos_core.services.foundation import IllegalTransition
from aos_core.services.foundation_baseline import compare_baselines, mint_baseline

from ..schemas import (
    BaselineMintRequest,
    FoundationBaselineDetailRead,
    FoundationBaselineElementRead,
    FoundationBaselineRead,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Mint (the mandatory second human gate — design §12 Stage 14)
# ---------------------------------------------------------------------------


@router.post("/foundation-runs/{run_id}/baseline", response_model=FoundationBaselineRead)
def mint_baseline_endpoint(
    run_id: str, payload: BaselineMintRequest, db: Session = Depends(get_db)
) -> FoundationBaseline:
    # Service 404s a missing run and 409s a non-'selected' run / no selected
    # candidate itself — let both propagate unwrapped.
    try:
        return mint_baseline(
            db, selection_run_id=run_id, approver=payload.approver, review_triggers=payload.review_triggers
        )
    except IllegalTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# List / detail / compare
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/foundation-baselines", response_model=list[FoundationBaselineRead])
def list_project_baselines(project_id: str, db: Session = Depends(get_db)) -> list[FoundationBaseline]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(FoundationBaseline)
        .filter(FoundationBaseline.project_id == project_id)
        .order_by(FoundationBaseline.created_at.desc(), FoundationBaseline.id)
        .all()
    )


@router.get("/foundation-baselines/{baseline_id}", response_model=FoundationBaselineDetailRead)
def get_foundation_baseline(baseline_id: str, db: Session = Depends(get_db)) -> dict:
    baseline = db.get(FoundationBaseline, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")

    elements = (
        db.query(FoundationBaselineElement)
        .filter(FoundationBaselineElement.baseline_id == baseline_id)
        .order_by(FoundationBaselineElement.created_at, FoundationBaselineElement.id)
        .all()
    )

    data = FoundationBaselineRead.model_validate(baseline).model_dump()
    data["elements"] = [FoundationBaselineElementRead.model_validate(e).model_dump() for e in elements]
    return data


@router.get("/foundation-baselines/{base_id}/compare/{other_id}", response_model=dict)
def compare_foundation_baselines(base_id: str, other_id: str, db: Session = Depends(get_db)) -> dict:
    # Service 404s either missing baseline itself — let it propagate unwrapped.
    return compare_baselines(db, base_id=base_id, other_id=other_id)
