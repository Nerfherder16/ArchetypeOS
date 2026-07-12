"""System Genome derivation + review/approval + comparison (RFC-0019, AOS-GENOME-MODELS-001).

``generate_genome`` derives a :class:`~aos_core.models.GenomeSnapshot` for one
``state_view`` (``current``/``intended``) from a project's ``claims`` —
**never** from :class:`~aos_core.models.RepositoryDNA` directly (AD-4, locked
in RFC-0016; DNA already reaches here as ``observed`` claims via the C5
backfill, RFC-0018 #214). Derivation is entirely deterministic
(``services/genome_rules.py``'s rule table); this slice ships **no LLM
classification** (RFC-0019 non-goal — that attaches behind this same seam
later, exactly as RFC-0005 did for the Final Judge).

``review_genome``/``approve_genome`` mirror ``services/decisions.py``'s
draft -> approved gate, writing an :class:`~aos_core.models.ApprovalRecord`.
``compare_genomes`` is a pure diff between two snapshots.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..foundation.enums import (
    AnswerType,
    ConflictStatus,
    Criticality,
    GenomeDimension,
    GenomeStatus,
    Materiality,
    StateView,
    TraitClassification,
)
from ..foundation.truth import MinterClass
from ..models import (
    ApprovalRecord,
    Claim,
    EvidenceConflict,
    GenomeDelta,
    GenomeSnapshot,
    GenomeTrait,
    GenomeTraitClaim,
    OpenQuestion,
    SystemArchetype,
    now_utc,
)
from .genome_rules import FOUNDATION_SHAPING_DIMENSIONS, GENOME_RULES, RULESET_VERSION, TraitResult, TraitRule

__all__ = [
    "generate_genome",
    "review_genome",
    "approve_genome",
    "compare_genomes",
]

# Below this per-trait confidence, a foundation-shaping dimension's best trait
# is treated as "not really answered yet" for open-question generation —
# distinct from the coverage-calibration floor below (which only cares whether
# a dimension has ANY non-unknown trait at all).
_LOW_CONFIDENCE_THRESHOLD = 0.4


def _coerce_state_view(state_view: StateView | str) -> StateView:
    return state_view if isinstance(state_view, StateView) else StateView(state_view)


def _is_machine_inferred_over_facts(claim: Claim, observed_ids: set[str]) -> bool:
    """RFC-0019 Design Open Q2 (resolved): an ``inferred`` claim counts toward
    ``current`` only if EVERY parent named in its ``derivation.parent_claim_ids``
    is an ``observed`` claim — i.e. a purely-machine inference over facts, not
    one derived even partly from stated intent (``claimed``) or another
    intent-flavored inference. A claim with no parents at all is never treated
    as a fact-only inference (nothing to verify it is fact-derived)."""
    if claim.truth_layer != "inferred":
        return False
    parents = (claim.derivation or {}).get("parent_claim_ids") or []
    return bool(parents) and all(parent_id in observed_ids for parent_id in parents)


def _claims_for_state_view(db: Session, *, project_id: str, state_view: StateView | str) -> list[Claim]:
    """The current/intended claim-set split (design §20 step 6->8; RFC-0019 Open Q2).

    - **current** = ``observed`` claims + ``inferred`` claims whose derivation
      parents are ALL ``observed`` (a machine inference purely over facts).
    - **intended** = ``claimed`` claims + every OTHER ``inferred`` claim (one
      derived even partly from stated intent rather than pure observed fact).
    - ``target``/``candidate`` are out of scope for this slice (Slices 3+ per
      RFC-0019 non-goals) and raise ``ValueError``.
    """
    state_view = _coerce_state_view(state_view)
    all_claims = db.query(Claim).filter(Claim.project_id == project_id).all()
    observed_ids = {claim.id for claim in all_claims if claim.truth_layer == "observed"}

    if state_view == StateView.CURRENT:
        return [
            claim for claim in all_claims
            if claim.truth_layer == "observed" or _is_machine_inferred_over_facts(claim, observed_ids)
        ]
    if state_view == StateView.INTENDED:
        return [
            claim for claim in all_claims
            if claim.truth_layer == "claimed"
            or (claim.truth_layer == "inferred" and not _is_machine_inferred_over_facts(claim, observed_ids))
        ]
    raise ValueError(
        f"generate_genome: state_view {state_view.value!r} is out of scope for AOS-GENOME-MODELS-001 "
        "('target'/'candidate' arrive in a later slice)."
    )


def _compute_quality(trait_rows: list[GenomeTrait]) -> tuple[float, float]:
    """Coverage-calibrated aggregate confidence (LES-023 — CRITICAL, RFC-0019 Design).

    ``coverage`` is the fraction of :data:`FOUNDATION_SHAPING_DIMENSIONS` that
    have at least one evidence-backed (non-``unknown``) trait.
    ``aggregate_confidence`` is the mean confidence of every evidence-backed
    trait, **multiplied by coverage** — never a naive average. A dimension
    with no evidence contributes an explicit ``unknown`` trait at confidence
    0.0 that is excluded from the mean (so it cannot inflate it), while its
    absence from ``coverage``'s numerator still drags the aggregate down. This
    is what makes a sparse-evidence genome score strictly lower than a dense
    one with identical per-trait confidences.
    """
    foundation_dims_covered = {
        GenomeDimension(trait.dimension)
        for trait in trait_rows
        if trait.classification != TraitClassification.UNKNOWN.value
        and GenomeDimension(trait.dimension) in FOUNDATION_SHAPING_DIMENSIONS
    }
    coverage = len(foundation_dims_covered) / len(FOUNDATION_SHAPING_DIMENSIONS)

    evidence_backed = [trait for trait in trait_rows if trait.classification != TraitClassification.UNKNOWN.value]
    mean_confidence = (
        sum(trait.confidence for trait in evidence_backed) / len(evidence_backed) if evidence_backed else 0.0
    )

    return coverage, mean_confidence * coverage


def _derive_archetypes(trait_rows: list[GenomeTrait]) -> list[tuple[str, str, float, list[str]]]:
    """Roll up 1-3 readable archetypes from trait combinations (design §6.6, RFC-0019 Open Q3).

    Small and readable by design — summaries of the underlying traits, never a
    substitute for them. Returns ``(tier, name, confidence, trait_ids)`` tuples.
    """
    by_key = {(trait.dimension, trait.trait_key): trait for trait in trait_rows}
    archetypes: list[tuple[str, str, float, list[str]]] = []

    local_first = by_key.get((GenomeDimension.DEPLOYMENT_OWNERSHIP.value, "local_first"))
    if local_first is not None and local_first.classification != TraitClassification.UNKNOWN.value:
        archetypes.append(("primary", "Local-First Control Plane", local_first.confidence, [local_first.id]))

    distributed = by_key.get((GenomeDimension.RUNTIME_TOPOLOGY.value, "distributed_workers"))
    if distributed is not None and distributed.classification != TraitClassification.UNKNOWN.value:
        archetypes.append(("primary", "Distributed Worker System", distributed.confidence, [distributed.id]))

    agentic = by_key.get((GenomeDimension.AI_AUTONOMY.value, "agentic"))
    if agentic is not None and agentic.classification != TraitClassification.UNKNOWN.value:
        archetypes.append(("secondary", "Human-Governed Agent Execution Platform", agentic.confidence, [agentic.id]))

    return archetypes[:3]


def _generate_open_questions(
    db: Session, *, project_id: str, snapshot: GenomeSnapshot, trait_rows: list[GenomeTrait], created_by: str
) -> list[OpenQuestion]:
    """One :class:`~aos_core.models.OpenQuestion` per foundation-shaping dimension
    whose best trait is ``unknown`` or below :data:`_LOW_CONFIDENCE_THRESHOLD` (design §7)."""
    questions: list[OpenQuestion] = []
    for dimension in sorted(FOUNDATION_SHAPING_DIMENSIONS, key=lambda d: d.value):
        dim_traits = [trait for trait in trait_rows if trait.dimension == dimension.value]
        if dim_traits:
            best = max(dim_traits, key=lambda trait: trait.confidence)
            classification, confidence = best.classification, best.confidence
        else:
            classification, confidence = TraitClassification.UNKNOWN.value, 0.0

        if classification != TraitClassification.UNKNOWN.value and confidence >= _LOW_CONFIDENCE_THRESHOLD:
            continue

        question = OpenQuestion(
            project_id=project_id,
            genome_snapshot_id=snapshot.id,
            question=f"What is the system's {dimension.value.replace('_', ' ')}?",
            affected_dimensions=[dimension.value],
            affected_foundation_domains=[],
            materiality=(
                Materiality.HIGH.value if classification == TraitClassification.UNKNOWN.value else Materiality.MEDIUM.value
            ),
            reason=(
                f"The {dimension.value} dimension has no evidence-backed trait above the low-confidence "
                f"floor (classification={classification!r}, confidence={confidence:.2f}); an answer here "
                "materially affects foundation selection."
            ),
            answer_type=AnswerType.TEXT.value,
            minted_by=MinterClass.AGENT.value,
            created_by=created_by,
            updated_by=created_by,
        )
        db.add(question)
        questions.append(question)
    db.flush()
    return questions


def _critical_conflict_count(db: Session, *, project_id: str, claim_ids: set[str]) -> int:
    """Open, ``critical``-materiality :class:`~aos_core.models.EvidenceConflict` rows
    touching this genome's claim set."""
    if not claim_ids:
        return 0
    conflicts = (
        db.query(EvidenceConflict)
        .filter(
            EvidenceConflict.project_id == project_id,
            EvidenceConflict.status == ConflictStatus.OPEN.value,
            EvidenceConflict.materiality == Materiality.CRITICAL.value,
        )
        .all()
    )
    return sum(1 for conflict in conflicts if set(conflict.claim_ids or []) & claim_ids)


def generate_genome(
    db: Session,
    *,
    project_id: str,
    state_view: StateView | str,
    corpus_snapshot_id: str | None = None,
    generated_by: str = RULESET_VERSION,
    created_by: str = "system",
) -> GenomeSnapshot:
    """Derive a :class:`~aos_core.models.GenomeSnapshot` for ``state_view`` from ``project_id``'s claims.

    Deterministic only (RFC-0019 non-goal: no LLM in this slice). Steps
    (RFC-0019 Design):

    1. Select the claim set for ``state_view`` (:func:`_claims_for_state_view`).
    2. Run every rule in ``services.genome_rules.GENOME_RULES``; persist a
       :class:`~aos_core.models.GenomeTrait` + supporting/opposing
       :class:`~aos_core.models.GenomeTraitClaim` links for each firing rule.
    3. Every dimension in :data:`~aos_core.services.genome_rules.FOUNDATION_SHAPING_DIMENSIONS`
       with no firing rule gets an explicit ``unknown`` trait at confidence 0.0
       (never silently omitted).
    4. Roll up 1-3 :class:`~aos_core.models.SystemArchetype` rows.
    5. Compute coverage-calibrated quality indicators (LES-023).
    6. Generate targeted :class:`~aos_core.models.OpenQuestion` rows.
    7. Supersede any prior non-superseded snapshot for ``(project_id, state_view)``.

    The new snapshot is always ``draft`` — :func:`review_genome`/
    :func:`approve_genome` gate human review before ``approved``.
    """
    state_view_enum = _coerce_state_view(state_view)
    claims = _claims_for_state_view(db, project_id=project_id, state_view=state_view_enum)
    claim_ids = {claim.id for claim in claims}

    prior = (
        db.query(GenomeSnapshot)
        .filter(
            GenomeSnapshot.project_id == project_id,
            GenomeSnapshot.state_view == state_view_enum.value,
            GenomeSnapshot.status != GenomeStatus.SUPERSEDED.value,
        )
        .order_by(GenomeSnapshot.version.desc())
        .first()
    )
    next_version = (prior.version + 1) if prior else 1

    fired_by_dimension: dict[GenomeDimension, list[tuple[TraitRule, TraitResult]]] = defaultdict(list)
    for rule in GENOME_RULES:
        result = rule.derive(claims)
        if result is not None:
            fired_by_dimension[rule.dimension].append((rule, result))

    snapshot = GenomeSnapshot(
        project_id=project_id,
        corpus_snapshot_id=corpus_snapshot_id,
        state_view=state_view_enum.value,
        version=next_version,
        summary=f"{state_view_enum.value.capitalize()} genome (version {next_version}) derived from {len(claims)} claim(s).",
        generated_by=generated_by,
        status=GenomeStatus.DRAFT.value,
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(snapshot)
    db.flush()

    trait_rows: list[GenomeTrait] = []
    for dimension in GenomeDimension:
        fired = fired_by_dimension.get(dimension, [])
        if fired:
            for rule, result in fired:
                trait = GenomeTrait(
                    genome_snapshot_id=snapshot.id,
                    dimension=dimension.value,
                    trait_key=rule.trait_key,
                    value=result.value,
                    value_type=result.value_type,
                    classification=result.classification.value,
                    confidence=result.confidence,
                    stability=result.stability.value,
                    criticality=rule.criticality.value,
                    rationale=result.rationale,
                    source_methods=result.source_methods,
                    created_by=created_by,
                    updated_by=created_by,
                )
                db.add(trait)
                db.flush()
                for supporting_id in result.supporting_claim_ids:
                    db.add(
                        GenomeTraitClaim(
                            trait_id=trait.id,
                            claim_id=supporting_id,
                            polarity="supporting",
                            created_by=created_by,
                            updated_by=created_by,
                        )
                    )
                for opposing_id in result.opposing_claim_ids:
                    db.add(
                        GenomeTraitClaim(
                            trait_id=trait.id,
                            claim_id=opposing_id,
                            polarity="opposing",
                            created_by=created_by,
                            updated_by=created_by,
                        )
                    )
                trait_rows.append(trait)
        elif dimension in FOUNDATION_SHAPING_DIMENSIONS:
            # design §6.4 / RFC-0019: no trait without provenance OR an
            # explicit `unknown` — never silently omitted.
            trait = GenomeTrait(
                genome_snapshot_id=snapshot.id,
                dimension=dimension.value,
                trait_key="unknown",
                value=None,
                value_type="unknown",
                classification=TraitClassification.UNKNOWN.value,
                confidence=0.0,
                stability="unknown",
                criticality=Criticality.FOUNDATION_SHAPING.value,
                rationale="No firing rule found evidence for this foundation-shaping dimension.",
                source_methods=[],
                created_by=created_by,
                updated_by=created_by,
            )
            db.add(trait)
            db.flush()
            trait_rows.append(trait)
        # Non-foundation-shaping dimensions with no firing rule are simply
        # skipped this slice: rule breadth beyond the 6 seed dimensions grows
        # later; only FOUNDATION_SHAPING_DIMENSIONS get the explicit `unknown` floor.

    for tier, name, confidence, trait_ids in _derive_archetypes(trait_rows):
        db.add(
            SystemArchetype(
                genome_snapshot_id=snapshot.id,
                name=name,
                tier=tier,
                confidence=confidence,
                trait_ids=trait_ids,
                created_by=created_by,
                updated_by=created_by,
            )
        )

    coverage, aggregate_confidence = _compute_quality(trait_rows)
    snapshot.coverage = coverage
    snapshot.aggregate_confidence = aggregate_confidence

    open_questions = _generate_open_questions(
        db, project_id=project_id, snapshot=snapshot, trait_rows=trait_rows, created_by=created_by
    )
    snapshot.open_question_count = len(open_questions)
    snapshot.critical_conflict_count = _critical_conflict_count(db, project_id=project_id, claim_ids=claim_ids)

    if prior is not None:
        prior.status = GenomeStatus.SUPERSEDED.value
        prior.updated_by = created_by

    db.commit()
    db.refresh(snapshot)
    return snapshot


def review_genome(db: Session, *, genome_id: str, reviewer: str) -> GenomeSnapshot:
    """Transition a ``draft`` :class:`~aos_core.models.GenomeSnapshot` to ``reviewed``.

    404s a missing snapshot; 409s if it is not currently ``draft``.
    """
    snapshot = db.get(GenomeSnapshot, genome_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Genome snapshot not found")
    if snapshot.status != GenomeStatus.DRAFT.value:
        raise HTTPException(
            status_code=409,
            detail=f"Genome snapshot in status '{snapshot.status}' cannot be reviewed (only 'draft' is reviewable).",
        )
    snapshot.status = GenomeStatus.REVIEWED.value
    snapshot.updated_by = reviewer
    db.commit()
    db.refresh(snapshot)
    return snapshot


def approve_genome(db: Session, *, genome_id: str, approver: str, rationale: str | None = None) -> GenomeSnapshot:
    """Approve a ``reviewed`` :class:`~aos_core.models.GenomeSnapshot`, writing an
    :class:`~aos_core.models.ApprovalRecord` (mirrors ``services.decisions.approve_decision``).

    404s a missing snapshot; 409s if it is not currently ``reviewed``. An
    approved snapshot's traits are never rewritten afterward — a later
    ``generate_genome`` call creates a new snapshot and only supersedes this one.
    """
    snapshot = db.get(GenomeSnapshot, genome_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Genome snapshot not found")
    if snapshot.status != GenomeStatus.REVIEWED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Genome snapshot in status '{snapshot.status}' cannot be approved (only 'reviewed' is approvable).",
        )
    snapshot.status = GenomeStatus.APPROVED.value
    snapshot.approved_by = approver
    snapshot.approved_at = now_utc()
    snapshot.updated_by = approver
    db.add(
        ApprovalRecord(
            project_id=snapshot.project_id,
            actor=approver,
            reason=rationale,
            requested_capability="genome.approve",
            target=genome_id,
            approval_status="approved",
        )
    )
    db.commit()
    db.refresh(snapshot)
    return snapshot


def compare_genomes(db: Session, *, from_id: str, to_id: str, created_by: str = "system") -> GenomeDelta:
    """A pure diff between two :class:`~aos_core.models.GenomeSnapshot` rows.

    404s if either snapshot is missing. ``changes`` holds added/removed/changed
    traits (keyed by ``(dimension, trait_key)``) plus coverage/confidence deltas.
    """
    from_snapshot = db.get(GenomeSnapshot, from_id)
    to_snapshot = db.get(GenomeSnapshot, to_id)
    if not from_snapshot or not to_snapshot:
        raise HTTPException(status_code=404, detail="Genome snapshot not found")

    from_traits = {
        (trait.dimension, trait.trait_key): trait
        for trait in db.query(GenomeTrait).filter(GenomeTrait.genome_snapshot_id == from_id).all()
    }
    to_traits = {
        (trait.dimension, trait.trait_key): trait
        for trait in db.query(GenomeTrait).filter(GenomeTrait.genome_snapshot_id == to_id).all()
    }

    added = [
        {"dimension": dimension, "trait_key": trait_key, "value": trait.value, "classification": trait.classification}
        for (dimension, trait_key), trait in to_traits.items()
        if (dimension, trait_key) not in from_traits
    ]
    removed = [
        {"dimension": dimension, "trait_key": trait_key, "value": trait.value, "classification": trait.classification}
        for (dimension, trait_key), trait in from_traits.items()
        if (dimension, trait_key) not in to_traits
    ]
    changed = []
    for key in set(from_traits) & set(to_traits):
        from_trait, to_trait = from_traits[key], to_traits[key]
        if from_trait.value != to_trait.value or from_trait.classification != to_trait.classification:
            changed.append(
                {
                    "dimension": key[0],
                    "trait_key": key[1],
                    "from_value": from_trait.value,
                    "to_value": to_trait.value,
                    "from_classification": from_trait.classification,
                    "to_classification": to_trait.classification,
                }
            )

    changes = {
        "added_traits": added,
        "removed_traits": removed,
        "changed_traits": changed,
        "coverage_delta": (to_snapshot.coverage or 0.0) - (from_snapshot.coverage or 0.0),
        "confidence_delta": (to_snapshot.aggregate_confidence or 0.0) - (from_snapshot.aggregate_confidence or 0.0),
    }
    summary = (
        f"{len(added)} trait(s) added, {len(removed)} removed, {len(changed)} changed "
        f"between snapshot {from_id} and {to_id}."
    )

    delta = GenomeDelta(
        project_id=to_snapshot.project_id,
        from_snapshot_id=from_id,
        to_snapshot_id=to_id,
        changes=changes,
        summary=summary,
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(delta)
    db.commit()
    db.refresh(delta)
    return delta
