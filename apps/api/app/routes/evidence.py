"""HTTP API over the Evidence Spine write path (AOS-EVIDENCE-API-001, RFC-0018).

Thin wrappers only — every route builds a request DTO, calls the matching
``services/evidence.py`` function, and returns a response DTO. No business
logic lives here; the guards (C1/C3/C4) all live in the service layer.

No authority envelope in this package: evidence ingestion is additive/advisory
data (mirrors how research/council creation works today) — selection/approval
/baseline routes land the envelope in a later slice.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from aos_core.database import get_db
from aos_core.foundation.truth import MinterClass
from aos_core.models import (
    Claim,
    ClaimEvidenceLink,
    ClaimRelationship,
    CorpusSnapshot,
    EvidenceConflict,
    EvidenceFragment,
    EvidenceSource,
    EvidenceSourceVersion,
    Project,
)
from aos_core.services.evidence import (
    add_fragment,
    add_source_version,
    create_claim,
    create_source,
    freeze_corpus,
    link_evidence,
    open_conflict,
    project_decided_claim,
    relate_claims,
    resolve_conflict,
)

from ..schemas import (
    ClaimCreate,
    ClaimDetailRead,
    ClaimEvidenceLinkCreate,
    ClaimEvidenceLinkRead,
    ClaimRead,
    ClaimRelationshipCreate,
    ClaimRelationshipRead,
    CorpusSnapshotCreate,
    CorpusSnapshotRead,
    EvidenceConflictCreate,
    EvidenceConflictRead,
    EvidenceConflictResolve,
    EvidenceFragmentCreate,
    EvidenceFragmentRead,
    EvidenceSourceCreate,
    EvidenceSourceRead,
    EvidenceSourceVersionCreate,
    EvidenceSourceVersionRead,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


@router.post("/projects/{project_id}/sources", response_model=EvidenceSourceRead)
def create_source_endpoint(
    project_id: str, payload: EvidenceSourceCreate, db: Session = Depends(get_db)
) -> EvidenceSource:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return create_source(
            db,
            project_id=project_id,
            minted_by=payload.minted_by,
            source_type=payload.source_type,
            title=payload.title,
            origin=payload.origin,
            originator=payload.originator,
            canonical_uri=payload.canonical_uri,
            sensitivity=payload.sensitivity,
            authority_domains=payload.authority_domains,
            access_policy_id=payload.access_policy_id,
            status=payload.status,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/sources", response_model=list[EvidenceSourceRead])
def list_sources(project_id: str, db: Session = Depends(get_db)) -> list[EvidenceSource]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(EvidenceSource)
        .filter(EvidenceSource.project_id == project_id)
        .order_by(EvidenceSource.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Source versions
# ---------------------------------------------------------------------------


@router.post("/sources/{source_id}/versions", response_model=EvidenceSourceVersionRead)
def create_source_version(
    source_id: str, payload: EvidenceSourceVersionCreate, db: Session = Depends(get_db)
) -> EvidenceSourceVersion:
    if not db.get(EvidenceSource, source_id):
        raise HTTPException(status_code=404, detail="Evidence source not found")
    try:
        return add_source_version(
            db,
            source_id=source_id,
            minted_by=payload.minted_by,
            version_ref=payload.version_ref,
            content_hash=payload.content_hash,
            ingestion_method=payload.ingestion_method,
            captured_at=payload.captured_at,
            effective_from=payload.effective_from,
            effective_until=payload.effective_until,
            supersedes_version_id=payload.supersedes_version_id,
            parser_version=payload.parser_version,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/sources/{source_id}/versions", response_model=list[EvidenceSourceVersionRead])
def list_source_versions(source_id: str, db: Session = Depends(get_db)) -> list[EvidenceSourceVersion]:
    if not db.get(EvidenceSource, source_id):
        raise HTTPException(status_code=404, detail="Evidence source not found")
    return (
        db.query(EvidenceSourceVersion)
        .filter(EvidenceSourceVersion.source_id == source_id)
        .order_by(EvidenceSourceVersion.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Fragments
# ---------------------------------------------------------------------------


@router.post("/source-versions/{version_id}/fragments", response_model=EvidenceFragmentRead)
def create_fragment(
    version_id: str, payload: EvidenceFragmentCreate, db: Session = Depends(get_db)
) -> EvidenceFragment:
    if not db.get(EvidenceSourceVersion, version_id):
        raise HTTPException(status_code=404, detail="Evidence source version not found")
    try:
        return add_fragment(
            db,
            source_version_id=version_id,
            minted_by=payload.minted_by,
            content_hash=payload.content_hash,
            excerpt=payload.excerpt,
            extraction_method=payload.extraction_method,
            locator=payload.locator,
            extraction_confidence=payload.extraction_confidence,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------


@router.post("/projects/{project_id}/claims", response_model=ClaimRead)
def create_claim_endpoint(project_id: str, payload: ClaimCreate, db: Session = Depends(get_db)) -> Claim:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    # The API is an external caller, not a deterministic tool: a public POST
    # /claims request may mint as agent/human (never deterministic_tool — that
    # minter class is reserved for internal scanners/backfill, which write
    # through services/evidence.py directly, not this route).
    if payload.minted_by == MinterClass.DETERMINISTIC_TOOL.value:
        raise HTTPException(
            status_code=422,
            detail="minted_by='deterministic_tool' is not permitted via the public claims API; "
            "deterministic-tool claims come from internal scanners/backfill, not this route.",
        )
    try:
        return create_claim(
            db,
            project_id=project_id,
            minted_by=payload.minted_by,
            truth_layer=payload.truth_layer,
            statement=payload.statement,
            claim_type=payload.claim_type,
            domain=payload.domain,
            created_by=payload.created_by,
            derivation=payload.derivation,
            scope=payload.scope,
            polarity=payload.polarity,
            confidence=payload.confidence,
            materiality=payload.materiality,
            status=payload.status,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/claims", response_model=list[ClaimRead])
def list_claims(
    project_id: str, truth_layer: str | None = None, db: Session = Depends(get_db)
) -> list[Claim]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    query = db.query(Claim).filter(Claim.project_id == project_id)
    if truth_layer is not None:
        query = query.filter(Claim.truth_layer == truth_layer)
    return query.order_by(Claim.created_at.desc()).all()


@router.get("/claims/{claim_id}", response_model=ClaimDetailRead)
def get_claim(claim_id: str, db: Session = Depends(get_db)) -> dict:
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    evidence_links = (
        db.query(ClaimEvidenceLink).filter(ClaimEvidenceLink.claim_id == claim_id).order_by(
            ClaimEvidenceLink.created_at.desc()
        ).all()
    )
    relationships = (
        db.query(ClaimRelationship)
        .filter(or_(ClaimRelationship.from_claim_id == claim_id, ClaimRelationship.to_claim_id == claim_id))
        .order_by(ClaimRelationship.created_at.desc())
        .all()
    )
    data = ClaimRead.model_validate(claim, from_attributes=True).model_dump()
    data["evidence_links"] = evidence_links
    data["relationships"] = relationships
    return data


@router.post("/claims/{claim_id}/evidence", response_model=ClaimEvidenceLinkRead)
def link_evidence_endpoint(
    claim_id: str, payload: ClaimEvidenceLinkCreate, db: Session = Depends(get_db)
) -> ClaimEvidenceLink:
    if not db.get(Claim, claim_id):
        raise HTTPException(status_code=404, detail="Claim not found")
    if not db.get(EvidenceFragment, payload.fragment_id):
        raise HTTPException(status_code=404, detail="Evidence fragment not found")
    try:
        return link_evidence(
            db,
            claim_id=claim_id,
            fragment_id=payload.fragment_id,
            minted_by=payload.minted_by,
            relationship=payload.relationship,
            relevance=payload.relevance,
            strength=payload.strength,
            notes=payload.notes,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/claims/{claim_id}/relationships", response_model=ClaimRelationshipRead)
def relate_claims_endpoint(
    claim_id: str, payload: ClaimRelationshipCreate, db: Session = Depends(get_db)
) -> ClaimRelationship:
    if not db.get(Claim, claim_id):
        raise HTTPException(status_code=404, detail="Claim not found")
    if not db.get(Claim, payload.to_claim_id):
        raise HTTPException(status_code=404, detail="Related claim not found")
    try:
        return relate_claims(
            db,
            from_claim_id=claim_id,
            to_claim_id=payload.to_claim_id,
            minted_by=payload.minted_by,
            relationship=payload.relationship,
            notes=payload.notes,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------


@router.post("/projects/{project_id}/conflicts", response_model=EvidenceConflictRead)
def open_conflict_endpoint(
    project_id: str, payload: EvidenceConflictCreate, db: Session = Depends(get_db)
) -> EvidenceConflict:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return open_conflict(
            db,
            project_id=project_id,
            claim_ids=payload.claim_ids,
            minted_by=payload.minted_by,
            conflict_type=payload.conflict_type,
            materiality=payload.materiality,
            blocking_stages=payload.blocking_stages,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/conflicts", response_model=list[EvidenceConflictRead])
def list_conflicts(project_id: str, db: Session = Depends(get_db)) -> list[EvidenceConflict]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(EvidenceConflict)
        .filter(EvidenceConflict.project_id == project_id)
        .order_by(EvidenceConflict.created_at.desc())
        .all()
    )


@router.patch("/conflicts/{conflict_id}", response_model=EvidenceConflictRead)
def resolve_conflict_endpoint(
    conflict_id: str, payload: EvidenceConflictResolve, db: Session = Depends(get_db)
) -> EvidenceConflict:
    # Service 404s a missing conflict; 422s an invalid status (ValueError).
    try:
        return resolve_conflict(
            db,
            conflict_id=conflict_id,
            status=payload.status,
            resolution=payload.resolution,
            resolution_decision_id=payload.resolution_decision_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Corpus snapshots
# ---------------------------------------------------------------------------


@router.post("/projects/{project_id}/corpus-snapshots", response_model=CorpusSnapshotRead)
def create_corpus_snapshot(
    project_id: str, payload: CorpusSnapshotCreate, db: Session = Depends(get_db)
) -> CorpusSnapshot:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return freeze_corpus(
            db,
            project_id=project_id,
            source_version_ids=payload.source_version_ids,
            purpose=payload.purpose,
            repository_refs=payload.repository_refs,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/corpus-snapshots", response_model=list[CorpusSnapshotRead])
def list_corpus_snapshots(project_id: str, db: Session = Depends(get_db)) -> list[CorpusSnapshot]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(CorpusSnapshot)
        .filter(CorpusSnapshot.project_id == project_id)
        .order_by(CorpusSnapshot.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Decision -> decided claim projection (C1)
# ---------------------------------------------------------------------------


@router.post("/decisions/{decision_id}/project-claim", response_model=ClaimRead)
def project_decided_claim_endpoint(decision_id: str, db: Session = Depends(get_db)) -> Claim:
    # Service 404s a missing decision and 409s a non-approved decision (C1) —
    # both propagate as-is; no ValueError path here.
    return project_decided_claim(db, decision_id=decision_id)
