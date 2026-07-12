"""HTTP API over the Foundation Intelligence selection-run/candidate/eligibility/
scoring core (AOS-FOUNDATION-API-001, RFC-0020 design §16).

Thin wrappers only — every route builds a request DTO, calls the matching
``services/foundation.py`` function, and returns a response DTO. No business
logic lives here (exactly like ``routes/genome.py`` over ``services/genome.py``).

Error-mapping discipline (matches ``routes/genome.py``):

- A missing parent entity (project/genome snapshot/selection run/candidate)
  this route itself looks up -> 404, raised here via ``db.get``.
- ``compile_requirements``/``generate_candidates``/``evaluate_eligibility``
  already 404 a missing run themselves; they can also raise
  ``IllegalTransition`` (a run stuck outside the linear compile ->
  generate -> evaluate chain) -> caught here, 409.
- ``open_selection_run`` already 409s a second active run per project;
  ``score_candidate`` already 404s a missing candidate and 409s a
  non-``eligible`` one (AD-8) -> these propagate straight through, unwrapped.
- Any other ``ValueError`` -> caught here, 422 (defensive; no current
  ``services/foundation.py`` path raises one outside ``IllegalTransition``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import (
    FoundationCandidate,
    FoundationElement,
    FoundationRequirement,
    FoundationScore,
    FoundationSelectionRun,
    GenomeSnapshot,
    Project,
)
from aos_core.services.foundation import (
    IllegalTransition,
    add_element,
    compile_requirements,
    create_candidate,
    evaluate_eligibility,
    generate_candidates,
    open_selection_run,
    score_candidate,
)

from ..schemas import (
    FoundationCandidateCreate,
    FoundationCandidateDetailRead,
    FoundationCandidateRead,
    FoundationElementCreate,
    FoundationElementRead,
    FoundationRequirementRead,
    FoundationRunActionRequest,
    FoundationRunCreate,
    FoundationRunDetailRead,
    FoundationScoreRead,
    FoundationSelectionRunRead,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Open run / compile / generate / evaluate (the linear lifecycle chain)
# ---------------------------------------------------------------------------


@router.post("/projects/{project_id}/foundation-runs", response_model=FoundationSelectionRunRead)
def open_foundation_run(
    project_id: str, payload: FoundationRunCreate, db: Session = Depends(get_db)
) -> FoundationSelectionRun:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if not db.get(GenomeSnapshot, payload.target_genome_snapshot_id):
        raise HTTPException(status_code=404, detail="Target genome snapshot not found")
    # Service 409s a second active (non-terminal) run for this project.
    return open_selection_run(
        db,
        project_id=project_id,
        target_genome_snapshot_id=payload.target_genome_snapshot_id,
        corpus_snapshot_id=payload.corpus_snapshot_id,
        created_by=payload.created_by,
    )


@router.post("/foundation-runs/{run_id}/compile-requirements", response_model=list[FoundationRequirementRead])
def compile_requirements_endpoint(
    run_id: str, payload: FoundationRunActionRequest, db: Session = Depends(get_db)
) -> list[FoundationRequirement]:
    # Service 404s a missing run/target genome snapshot itself.
    try:
        return compile_requirements(db, selection_run_id=run_id, created_by=payload.actor)
    except IllegalTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/foundation-runs/{run_id}/generate-candidates", response_model=list[FoundationCandidateRead])
def generate_candidates_endpoint(
    run_id: str, payload: FoundationRunActionRequest, db: Session = Depends(get_db)
) -> list[FoundationCandidate]:
    # Service 404s a missing run itself.
    try:
        return generate_candidates(db, selection_run_id=run_id, created_by=payload.actor)
    except IllegalTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/foundation-runs/{run_id}/evaluate-eligibility", response_model=list[FoundationCandidateRead])
def evaluate_eligibility_endpoint(
    run_id: str, payload: FoundationRunActionRequest, db: Session = Depends(get_db)
) -> list[FoundationCandidate]:
    # Service 404s a missing run itself.
    try:
        return evaluate_eligibility(db, selection_run_id=run_id, actor=payload.actor)
    except IllegalTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Scoring (AD-8: only an eligible candidate may be scored)
# ---------------------------------------------------------------------------


@router.post("/candidates/{candidate_id}/score", response_model=FoundationCandidateRead)
def score_candidate_endpoint(
    candidate_id: str, payload: FoundationRunActionRequest, db: Session = Depends(get_db)
) -> FoundationCandidate:
    # Service 404s a missing candidate and 409s a non-'eligible' one (AD-8) —
    # let both propagate unwrapped, exactly like routes/genome.py's
    # review/approve endpoints do for services/genome.py's HTTPExceptions.
    return score_candidate(db, candidate_id=candidate_id, actor=payload.actor)


# ---------------------------------------------------------------------------
# List / detail
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/foundation-runs", response_model=list[FoundationSelectionRunRead])
def list_foundation_runs(project_id: str, db: Session = Depends(get_db)) -> list[FoundationSelectionRun]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(FoundationSelectionRun)
        .filter(FoundationSelectionRun.project_id == project_id)
        .order_by(FoundationSelectionRun.created_at.desc())
        .all()
    )


@router.get("/foundation-runs/{run_id}", response_model=FoundationRunDetailRead)
def get_foundation_run(run_id: str, db: Session = Depends(get_db)) -> dict:
    run = db.get(FoundationSelectionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Selection run not found")

    requirements = (
        db.query(FoundationRequirement)
        .filter(FoundationRequirement.selection_run_id == run_id)
        .order_by(FoundationRequirement.created_at)
        .all()
    )
    candidates = (
        db.query(FoundationCandidate)
        .filter(FoundationCandidate.selection_run_id == run_id)
        .order_by(FoundationCandidate.created_at)
        .all()
    )

    data = FoundationSelectionRunRead.model_validate(run, from_attributes=True).model_dump()
    data["requirements"] = [
        FoundationRequirementRead.model_validate(r, from_attributes=True).model_dump() for r in requirements
    ]
    data["candidates"] = [
        FoundationCandidateRead.model_validate(c, from_attributes=True).model_dump() for c in candidates
    ]
    return data


@router.get("/candidates/{candidate_id}", response_model=FoundationCandidateDetailRead)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> dict:
    candidate = db.get(FoundationCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    elements = (
        db.query(FoundationElement)
        .filter(FoundationElement.candidate_id == candidate_id)
        .order_by(FoundationElement.created_at)
        .all()
    )
    scores = (
        db.query(FoundationScore)
        .filter(FoundationScore.candidate_id == candidate_id)
        .order_by(FoundationScore.criterion)
        .all()
    )

    data = FoundationCandidateRead.model_validate(candidate, from_attributes=True).model_dump()
    data["elements"] = [FoundationElementRead.model_validate(e, from_attributes=True).model_dump() for e in elements]
    data["scores"] = [FoundationScoreRead.model_validate(s, from_attributes=True).model_dump() for s in scores]
    return data


# ---------------------------------------------------------------------------
# Manual authoring (design §9.3/§9.4 primitives — also what generate_candidates
# builds on top of)
# ---------------------------------------------------------------------------


@router.post("/foundation-runs/{run_id}/candidates", response_model=FoundationCandidateRead)
def create_candidate_endpoint(
    run_id: str, payload: FoundationCandidateCreate, db: Session = Depends(get_db)
) -> FoundationCandidate:
    if not db.get(FoundationSelectionRun, run_id):
        raise HTTPException(status_code=404, detail="Selection run not found")
    return create_candidate(
        db,
        selection_run_id=run_id,
        name=payload.name,
        summary=payload.summary,
        architecture_style=payload.architecture_style,
        reversibility=payload.reversibility,
        recommendation_ref=payload.recommendation_ref,
        created_by=payload.created_by,
    )


@router.post("/candidates/{candidate_id}/elements", response_model=FoundationElementRead)
def add_element_endpoint(
    candidate_id: str, payload: FoundationElementCreate, db: Session = Depends(get_db)
) -> FoundationElement:
    if not db.get(FoundationCandidate, candidate_id):
        raise HTTPException(status_code=404, detail="Candidate not found")
    return add_element(
        db,
        candidate_id=candidate_id,
        domain=payload.domain,
        title=payload.title,
        decision=payload.decision,
        verification_method=payload.verification_method,
        rationale=payload.rationale,
        technology_refs=payload.technology_refs,
        claim_ids=payload.claim_ids,
        requirement_ids=payload.requirement_ids,
        alternatives_rejected=payload.alternatives_rejected,
        tradeoffs=payload.tradeoffs,
        risks=payload.risks,
        created_by=payload.created_by,
    )
