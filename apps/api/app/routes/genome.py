"""HTTP API over the System Genome derivation/review/approval/compare core
(AOS-GENOME-API-001, RFC-0019 §16).

Thin wrappers only — every route builds a request DTO, calls the matching
``services/genome.py`` function, and returns a response DTO. No business
logic lives here (exactly like ``routes/evidence.py`` over ``services/
evidence.py``).

Error-mapping discipline (matches ``routes/evidence.py`` / ``routes/
decisions.py``):

- A missing parent entity (project/genome snapshot) this route itself looks
  up -> 404, raised here.
- ``generate_genome``'s only failure mode is a ``ValueError`` from an
  out-of-scope ``state_view`` (``target``/``candidate``) -> caught here, 422.
- ``review_genome``/``approve_genome``/``compare_genomes`` already raise
  ``HTTPException`` directly (404 missing / 409 illegal transition — mirrors
  ``services/decisions.py``'s ``approve_decision``/``reject_decision``), so
  these routes call them straight through and let the exception propagate;
  no try/except needed for those three.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import (
    GenomeSnapshot,
    GenomeTrait,
    GenomeTraitClaim,
    OpenQuestion,
    Project,
    SystemArchetype,
)
from aos_core.services.genome import (
    approve_genome,
    compare_genomes,
    generate_genome,
    review_genome,
)
from aos_core.services.genome_rules import RULESET_VERSION

from ..schemas import (
    GenomeApproveRequest,
    GenomeDeltaRead,
    GenomeGenerateRequest,
    GenomeReviewRequest,
    GenomeSnapshotDetailRead,
    GenomeSnapshotRead,
    GenomeTraitRead,
    OpenQuestionRead,
    SystemArchetypeRead,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Generate / list
# ---------------------------------------------------------------------------


@router.post("/projects/{project_id}/genomes/generate", response_model=GenomeSnapshotRead)
def generate_genome_endpoint(
    project_id: str, payload: GenomeGenerateRequest, db: Session = Depends(get_db)
) -> GenomeSnapshot:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return generate_genome(
            db,
            project_id=project_id,
            state_view=payload.state_view,
            corpus_snapshot_id=payload.corpus_snapshot_id,
            generated_by=payload.generated_by or RULESET_VERSION,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/genomes", response_model=list[GenomeSnapshotRead])
def list_genomes(
    project_id: str, state_view: str | None = None, db: Session = Depends(get_db)
) -> list[GenomeSnapshot]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    query = db.query(GenomeSnapshot).filter(GenomeSnapshot.project_id == project_id)
    if state_view is not None:
        query = query.filter(GenomeSnapshot.state_view == state_view)
    return query.order_by(GenomeSnapshot.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Detail (traits + archetypes)
# ---------------------------------------------------------------------------


@router.get("/genomes/{genome_id}", response_model=GenomeSnapshotDetailRead)
def get_genome(genome_id: str, db: Session = Depends(get_db)) -> dict:
    snapshot = db.get(GenomeSnapshot, genome_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Genome snapshot not found")

    traits = (
        db.query(GenomeTrait)
        .filter(GenomeTrait.genome_snapshot_id == genome_id)
        .order_by(GenomeTrait.dimension, GenomeTrait.trait_key)
        .all()
    )
    trait_ids = [trait.id for trait in traits]
    trait_claims = (
        db.query(GenomeTraitClaim).filter(GenomeTraitClaim.trait_id.in_(trait_ids)).all() if trait_ids else []
    )
    supporting_by_trait: dict[str, list[str]] = defaultdict(list)
    opposing_by_trait: dict[str, list[str]] = defaultdict(list)
    for link in trait_claims:
        if link.polarity == "supporting":
            supporting_by_trait[link.trait_id].append(link.claim_id)
        else:
            opposing_by_trait[link.trait_id].append(link.claim_id)

    trait_reads = []
    for trait in traits:
        data = GenomeTraitRead.model_validate(trait, from_attributes=True).model_dump()
        data["supporting_claim_ids"] = supporting_by_trait.get(trait.id, [])
        data["opposing_claim_ids"] = opposing_by_trait.get(trait.id, [])
        trait_reads.append(data)

    archetypes = (
        db.query(SystemArchetype)
        .filter(SystemArchetype.genome_snapshot_id == genome_id)
        .order_by(SystemArchetype.created_at)
        .all()
    )

    data = GenomeSnapshotRead.model_validate(snapshot, from_attributes=True).model_dump()
    data["traits"] = trait_reads
    data["archetypes"] = [
        SystemArchetypeRead.model_validate(archetype, from_attributes=True).model_dump() for archetype in archetypes
    ]
    return data


# ---------------------------------------------------------------------------
# Review / approve
# ---------------------------------------------------------------------------


@router.post("/genomes/{genome_id}/review", response_model=GenomeSnapshotRead)
def review_genome_endpoint(
    genome_id: str, payload: GenomeReviewRequest, db: Session = Depends(get_db)
) -> GenomeSnapshot:
    # Service 404s a missing snapshot and 409s a non-draft snapshot.
    return review_genome(db, genome_id=genome_id, reviewer=payload.reviewer)


@router.post("/genomes/{genome_id}/approve", response_model=GenomeSnapshotRead)
def approve_genome_endpoint(
    genome_id: str, payload: GenomeApproveRequest, db: Session = Depends(get_db)
) -> GenomeSnapshot:
    # Service 404s a missing snapshot and 409s a non-reviewed snapshot (only
    # "reviewed" is approvable — mirrors services/decisions.py's approve gate).
    return approve_genome(db, genome_id=genome_id, approver=payload.approver, rationale=payload.rationale)


# ---------------------------------------------------------------------------
# Open questions
# ---------------------------------------------------------------------------


@router.get("/genomes/{genome_id}/questions", response_model=list[OpenQuestionRead])
def list_genome_questions(genome_id: str, db: Session = Depends(get_db)) -> list[OpenQuestion]:
    if not db.get(GenomeSnapshot, genome_id):
        raise HTTPException(status_code=404, detail="Genome snapshot not found")
    return (
        db.query(OpenQuestion)
        .filter(OpenQuestion.genome_snapshot_id == genome_id)
        .order_by(OpenQuestion.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------


@router.post("/genomes/{from_id}/compare/{to_id}", response_model=GenomeDeltaRead)
def compare_genomes_endpoint(from_id: str, to_id: str, db: Session = Depends(get_db)):
    # Service 404s either missing snapshot.
    return compare_genomes(db, from_id=from_id, to_id=to_id)
