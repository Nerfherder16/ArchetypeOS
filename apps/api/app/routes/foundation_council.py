"""HTTP API over the Council & Validation engine (RFC-0021, Foundation
Intelligence Slice 4, AOS-COUNCIL-VALIDATION-API-001).

Thin wrappers only — every route builds a request DTO, calls the matching
``services/foundation_council.py`` function, and returns a response DTO. No
business logic lives here (mirrors ``routes/foundation.py`` over
``services/foundation.py``).

Error-mapping discipline (matches ``routes/foundation.py``):

- A missing parent entity this route itself looks up (candidate/run/objection/
  task) -> 404, raised here via ``db.get``.
- ``resolve_objection``/``record_validation_result`` can raise
  ``IllegalTransition`` (an illegal target status/outcome) -> caught here, 409;
  any other ``ValueError`` -> caught here, 422. The services' own
  404s/409s (missing objection/task/run/candidate; a non-open objection; the
  ``select_candidate`` gate) propagate straight through, unwrapped.
- ``review_candidate`` runs asynchronously (a worker job, mirrors
  ``routes/council.py``'s ``create_council_review``) — this route only enqueues
  it and returns the ``Job``.
"""

from __future__ import annotations

import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import (
    FoundationCandidate,
    FoundationDossier,
    FoundationObjection,
    FoundationSelectionRun,
    Job,
    ValidationResult,
    ValidationTask,
)
from aos_core.services.foundation import IllegalTransition
from aos_core.services.foundation_council import (
    record_validation_result,
    resolve_objection,
    select_candidate,
    synthesize_dossier,
)
from aos_core.services.jobs import enqueue_job

from ..schemas import (
    CandidateSelectRequest,
    CouncilReviewSubjectRequest,
    FoundationCandidateRead,
    FoundationDossierRead,
    FoundationObjectionRead,
    JobRead,
    ObjectionResolveRequest,
    ValidationResultCreate,
    ValidationResultRead,
    ValidationTaskDetailRead,
    ValidationTaskRead,
)

settings = get_settings()
router = APIRouter()


# ---------------------------------------------------------------------------
# Council review (async — enqueues a worker job, mirrors routes/council.py)
# ---------------------------------------------------------------------------


@router.post("/candidates/{candidate_id}/council-review", response_model=JobRead)
def create_candidate_council_review(
    candidate_id: str, payload: CouncilReviewSubjectRequest, db: Session = Depends(get_db)
) -> Job:
    candidate = db.get(FoundationCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    run = db.get(FoundationSelectionRun, candidate.selection_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Selection run not found")
    return enqueue_job(
        db,
        redis.Redis.from_url(settings.redis_url),
        job_type="foundation_council_review",
        project_id=run.project_id,
        payload={"candidate_id": candidate_id},
    )


# ---------------------------------------------------------------------------
# Objection / validation / dossier / selection (design §§11-13)
# ---------------------------------------------------------------------------


@router.post("/foundation-objections/{objection_id}/resolve", response_model=FoundationObjectionRead)
def resolve_objection_endpoint(
    objection_id: str, payload: ObjectionResolveRequest, db: Session = Depends(get_db)
) -> FoundationObjection:
    # Service 404s a missing objection and 409s a non-'open' one itself — let
    # both propagate unwrapped.
    try:
        return resolve_objection(
            db,
            objection_id=objection_id,
            status=payload.status,
            resolution=payload.resolution,
            validation_task_id=payload.validation_task_id,
            decision_id=payload.decision_id,
        )
    except IllegalTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/validation-tasks/{task_id}/result", response_model=ValidationResultRead)
def record_validation_result_endpoint(
    task_id: str, payload: ValidationResultCreate, db: Session = Depends(get_db)
) -> ValidationResult:
    # Service 404s a missing task itself — let it propagate unwrapped.
    try:
        return record_validation_result(
            db,
            validation_task_id=task_id,
            outcome=payload.outcome,
            summary=payload.summary,
            evidence=payload.evidence,
            benchmark_ref=payload.benchmark_ref,
            experiment_ref=payload.experiment_ref,
        )
    except IllegalTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/foundation-runs/{run_id}/synthesize-dossier", response_model=FoundationDossierRead)
def synthesize_dossier_endpoint(run_id: str, db: Session = Depends(get_db)) -> FoundationDossier:
    # Service 404s a missing run itself — let it propagate unwrapped.
    return synthesize_dossier(db, selection_run_id=run_id)


@router.post("/foundation-runs/{run_id}/select", response_model=FoundationCandidateRead)
def select_candidate_endpoint(
    run_id: str, payload: CandidateSelectRequest, db: Session = Depends(get_db)
) -> FoundationCandidate:
    # Service 404s a missing run/candidate and 409s the selection gate itself —
    # let both propagate unwrapped.
    return select_candidate(db, selection_run_id=run_id, candidate_id=payload.candidate_id, approver=payload.approver)


# ---------------------------------------------------------------------------
# List / detail
# ---------------------------------------------------------------------------


@router.get("/candidates/{candidate_id}/objections", response_model=list[FoundationObjectionRead])
def list_candidate_objections(candidate_id: str, db: Session = Depends(get_db)) -> list[FoundationObjection]:
    if not db.get(FoundationCandidate, candidate_id):
        raise HTTPException(status_code=404, detail="Candidate not found")
    return (
        db.query(FoundationObjection)
        .filter(FoundationObjection.candidate_id == candidate_id)
        .order_by(FoundationObjection.created_at.desc(), FoundationObjection.id)
        .all()
    )


@router.get("/foundation-objections/{objection_id}", response_model=FoundationObjectionRead)
def get_objection(objection_id: str, db: Session = Depends(get_db)) -> FoundationObjection:
    objection = db.get(FoundationObjection, objection_id)
    if not objection:
        raise HTTPException(status_code=404, detail="Objection not found")
    return objection


@router.get("/foundation-runs/{run_id}/validation-tasks", response_model=list[ValidationTaskRead])
def list_run_validation_tasks(run_id: str, db: Session = Depends(get_db)) -> list[ValidationTask]:
    if not db.get(FoundationSelectionRun, run_id):
        raise HTTPException(status_code=404, detail="Selection run not found")
    return (
        db.query(ValidationTask)
        .filter(ValidationTask.selection_run_id == run_id)
        .order_by(ValidationTask.created_at.desc(), ValidationTask.id)
        .all()
    )


@router.get("/validation-tasks/{task_id}", response_model=ValidationTaskDetailRead)
def get_validation_task(task_id: str, db: Session = Depends(get_db)) -> dict:
    task = db.get(ValidationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Validation task not found")

    results = (
        db.query(ValidationResult)
        .filter(ValidationResult.validation_task_id == task_id)
        .order_by(ValidationResult.created_at)
        .all()
    )

    data = ValidationTaskRead.model_validate(task, from_attributes=True).model_dump()
    data["results"] = [ValidationResultRead.model_validate(r, from_attributes=True).model_dump() for r in results]
    return data


@router.get("/foundation-runs/{run_id}/dossier", response_model=FoundationDossierRead)
def get_run_dossier(run_id: str, db: Session = Depends(get_db)) -> FoundationDossier:
    if not db.get(FoundationSelectionRun, run_id):
        raise HTTPException(status_code=404, detail="Selection run not found")
    dossier = (
        db.query(FoundationDossier)
        .filter(FoundationDossier.selection_run_id == run_id)
        .order_by(FoundationDossier.created_at.desc(), FoundationDossier.id.desc())
        .first()
    )
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    return dossier
