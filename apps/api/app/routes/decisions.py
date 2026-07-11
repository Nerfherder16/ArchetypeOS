from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Decision, KnowledgePage, Project, Recommendation, ResearchNote
from aos_core.services.adr import export_decision_adr
from aos_core.services.decisions import (
    approve_decision,
    draft_decision_from_review,
    reject_decision,
)
from aos_core.services.evolution import find_stale_decisions, reevaluate_decision
from aos_core.services.recommendation import generate_recommendations

from ..schemas import (
    DecisionApprove,
    DecisionCreate,
    DecisionReevaluate,
    DecisionRead,
    DecisionReject,
    DecisionStaleness,
    KnowledgePageRead,
    RecommendationCreate,
    RecommendationRead,
    ResearchNoteCreate,
    ResearchNoteRead,
)

router = APIRouter()


@router.post("/projects/{project_id}/decisions", response_model=DecisionRead)
def create_decision(project_id: str, payload: DecisionCreate, db: Session = Depends(get_db)) -> Decision:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    for note_id in payload.research_note_ids:
        note = db.get(ResearchNote, note_id)
        if not note or note.project_id != project_id:
            raise HTTPException(status_code=404, detail="Research note not found")
    evidence = list(payload.evidence) + [{"type": "research_note", "id": nid} for nid in payload.research_note_ids]
    decision = Decision(
        project_id=project_id,
        title=payload.title,
        context=payload.context,
        decision=payload.decision,
        alternatives=payload.alternatives,
        tradeoffs=payload.tradeoffs,
        consequences=payload.consequences,
        evidence=evidence,
        confidence=payload.confidence,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


@router.get("/projects/{project_id}/decisions", response_model=list[DecisionRead])
def list_decisions(project_id: str, db: Session = Depends(get_db)) -> list[Decision]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Decision).filter(Decision.project_id == project_id).order_by(Decision.created_at.desc()).all()


@router.get("/decisions/{decision_id}", response_model=DecisionRead)
def get_decision(decision_id: str, db: Session = Depends(get_db)) -> Decision:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.post("/council-reviews/{review_id}/draft-decision", response_model=DecisionRead)
def draft_decision(review_id: str, db: Session = Depends(get_db)) -> Decision:
    # Service 404s a missing review; idempotent (one draft per review).
    return draft_decision_from_review(db, review_id=review_id)


@router.post("/decisions/{decision_id}/approve", response_model=DecisionRead)
def approve_decision_endpoint(
    decision_id: str, payload: DecisionApprove, db: Session = Depends(get_db)
) -> Decision:
    # Service 404s a missing decision and 409s an invalid transition (a
    # needs_evidence draft cannot be approved — LES-019).
    return approve_decision(db, decision_id=decision_id, approver=payload.approver, rationale=payload.rationale)


@router.post("/decisions/{decision_id}/reject", response_model=DecisionRead)
def reject_decision_endpoint(
    decision_id: str, payload: DecisionReject, db: Session = Depends(get_db)
) -> Decision:
    # Service 404s a missing decision and 409s an already-transitioned decision.
    return reject_decision(db, decision_id=decision_id, approver=payload.approver, rationale=payload.rationale)


@router.get("/projects/{project_id}/decisions/stale", response_model=list[DecisionStaleness])
def list_stale_decisions(
    project_id: str, max_age_days: int = 90, db: Session = Depends(get_db)
) -> list[dict]:
    # AOS-EVOLVE-001: read-only staleness pass over approved decisions (Article
    # X/XVIII) — no status mutation, no execution. 404s a missing project.
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return find_stale_decisions(db, project_id=project_id, max_age_days=max_age_days)


@router.post("/decisions/{decision_id}/reevaluate", response_model=DecisionRead)
def reevaluate_decision_endpoint(
    decision_id: str, payload: DecisionReevaluate = DecisionReevaluate(), db: Session = Depends(get_db)
) -> Decision:
    # Service 404s a missing decision. Advisory only (Article IX): flags
    # meta["reevaluation_requested_at"] / meta["stale_reason"] — never mutates
    # status, never deletes. Idempotent re-flag.
    return reevaluate_decision(db, decision_id=decision_id, reason=payload.reason)


@router.post("/decisions/{decision_id}/adr", response_model=KnowledgePageRead)
def export_decision_adr_endpoint(decision_id: str, db: Session = Depends(get_db)) -> KnowledgePage:
    # Service 404s a missing decision, 409s a non-approved decision or a
    # non-writable (:ro-mounted / read-only) vault — never a 500 (local-first
    # write; the ADR is projected as a re-syncable KnowledgePage).
    return export_decision_adr(db, decision_id=decision_id, knowledge_root=get_settings().knowledge_root)


@router.post("/projects/{project_id}/research-notes", response_model=ResearchNoteRead)
def create_research_note(project_id: str, payload: ResearchNoteCreate, db: Session = Depends(get_db)) -> ResearchNote:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    note = ResearchNote(
        project_id=project_id,
        title=payload.title,
        question=payload.question,
        summary=payload.summary,
        sources=payload.sources,
        findings=payload.findings,
        freshness=payload.freshness,
        confidence=payload.confidence,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/projects/{project_id}/research-notes", response_model=list[ResearchNoteRead])
def list_research_notes(project_id: str, db: Session = Depends(get_db)) -> list[ResearchNote]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(ResearchNote).filter(ResearchNote.project_id == project_id).order_by(ResearchNote.created_at.desc()).all()


@router.get("/research-notes/{note_id}", response_model=ResearchNoteRead)
def get_research_note(note_id: str, db: Session = Depends(get_db)) -> ResearchNote:
    note = db.get(ResearchNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Research note not found")
    return note


@router.post("/projects/{project_id}/recommendations", response_model=RecommendationRead)
def create_recommendation(project_id: str, payload: RecommendationCreate, db: Session = Depends(get_db)) -> Recommendation:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    recommendation = Recommendation(
        project_id=project_id,
        title=payload.title,
        recommendation=payload.recommendation,
        rationale=payload.rationale,
        alternatives=payload.alternatives,
        pros=payload.pros,
        cons=payload.cons,
        risk=payload.risk,
        effort=payload.effort,
        dependencies=payload.dependencies,
        acceptance_criteria=payload.acceptance_criteria,
        evidence=payload.evidence,
        confidence=payload.confidence,
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.get("/projects/{project_id}/recommendations", response_model=list[RecommendationRead])
def list_recommendations(project_id: str, db: Session = Depends(get_db)) -> list[Recommendation]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Recommendation).filter(Recommendation.project_id == project_id).order_by(Recommendation.created_at.desc()).all()


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationRead)
def get_recommendation(recommendation_id: str, db: Session = Depends(get_db)) -> Recommendation:
    recommendation = db.get(Recommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation


@router.post("/projects/{project_id}/recommendations/generate", response_model=list[RecommendationRead])
def generate_recommendations_endpoint(project_id: str, db: Session = Depends(get_db)) -> list[Recommendation]:
    # AOS-RECO-ENGINE-001: runs the deterministic Technology Fitness pass over
    # the project's RepositoryDNA + latest research and drafts recommendations;
    # idempotent (services/recommendation.py:generate_recommendations dedups on
    # meta["reco_signature"]) — a repeat call returns only newly-created rows.
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return generate_recommendations(db, project_id=project_id)
