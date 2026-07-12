"""Foundation Intelligence engine (RFC-0020, AOS-FOUNDATION-MODELS-001).

``open_selection_run`` opens a :class:`~aos_core.models.FoundationSelectionRun`
in ``draft``. ``compile_requirements`` derives
:class:`~aos_core.models.FoundationRequirement` rows from the run's target
Genome snapshot's traits + the project's claims (``services/foundation_rules.py``'s
deterministic rule table — the foundation analog of ``genome_rules.py``);
``generate_candidates`` runs the deterministic candidate templates (plus
``create_candidate``/``add_element`` for manual authoring); ``evaluate_eligibility``
implements **AD-8**: every candidate's elements are checked against every
``hard_constraint`` requirement *before* any weighted score, and a violator is
marked ``rejected`` regardless of its would-be score; ``score_candidate``
produces the design §10.3 score **vector** (never a lone scalar) and refuses
to score anything but an ``eligible`` candidate.

Every :class:`~aos_core.models.FoundationSelectionRun` state change is
validated through :mod:`aos_core.foundation.lifecycle` — the Slice-0
transition table is the single source of edge legality; this slice does not
add a second one. This slice does not expose separate service calls for the
earlier corpus/evidence-extraction/reconciliation stages (Slices 1-2's
concern) — :func:`_advance_run` walks a run's state forward through the
lifecycle table's single-path linear chain one legal hop at a time until it
reaches the requested milestone, so those unexposed intermediate states are
still recorded as legitimate transitions, never skipped illegally.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..foundation.enums import (
    CandidateStatus,
    FoundationDomain,
    RequirementType,
    Reversibility,
    SelectionRunState,
)
from ..foundation.lifecycle import LifecycleKind, can_transition, next_states
from ..models import (
    Claim,
    FoundationCandidate,
    FoundationElement,
    FoundationRequirement,
    FoundationScore,
    FoundationSelectionRun,
    GenomeSnapshot,
    GenomeTrait,
    GenomeTraitClaim,
)
from .foundation_rules import (
    CANDIDATE_TEMPLATES,
    REQUIREMENT_COMPILATION_RULES,
    element_violates_requirement,
    requirement_satisfaction,
    score_criteria,
)

__all__ = [
    "IllegalTransition",
    "open_selection_run",
    "compile_requirements",
    "generate_candidates",
    "create_candidate",
    "add_element",
    "evaluate_eligibility",
    "score_candidate",
]


class IllegalTransition(ValueError):
    """A :class:`~aos_core.models.FoundationSelectionRun`/
    :class:`~aos_core.models.FoundationCandidate` status change is not a legal
    edge in :mod:`aos_core.foundation.lifecycle`'s transition table. The (future)
    API package maps this to HTTP 409 (RFC-0020 design)."""


# The three lateral terminal states every non-terminal SelectionRunState may
# reach (design §13) — kept local (not imported private from lifecycle.py)
# since the enum itself is the public source.
_LATERAL_RUN_STATES: frozenset[str] = frozenset(
    {SelectionRunState.BLOCKED.value, SelectionRunState.CANCELLED.value, SelectionRunState.SUPERSEDED.value}
)

# Only an ``eligible`` candidate may be scored (AD-8) — this slice stops at
# eligibility_review, so no candidate reaches challenged/selectable/etc. yet.
_SCORABLE_CANDIDATE_STATUSES: frozenset[str] = frozenset({CandidateStatus.ELIGIBLE.value})


def _advance_run(run: FoundationSelectionRun, target: SelectionRunState, *, actor: str) -> None:
    """Walk ``run.state`` forward one legal hop at a time until it reaches
    ``target``, validating every hop via ``lifecycle.can_transition``. Raises
    :class:`IllegalTransition` if no legal forward path exists (e.g. ``target``
    is behind ``run.state``, or ``run.state`` is already a terminal lateral)."""
    target_value = target.value
    hops = 0
    max_hops = len(SelectionRunState) + 1
    while run.state != target_value:
        hops += 1
        if hops > max_hops:
            raise IllegalTransition(
                f"selection run {run.id}: no legal forward path from {run.state!r} to {target_value!r}"
            )
        reachable = next_states(LifecycleKind.SELECTION_RUN, run.state)
        step = target_value if target_value in reachable else next(
            (state for state in reachable if state not in _LATERAL_RUN_STATES), None
        )
        if step is None or not can_transition(LifecycleKind.SELECTION_RUN, run.state, step):
            raise IllegalTransition(f"selection run {run.id}: illegal transition {run.state!r} -> {step!r}")
        run.state = step
    run.updated_by = actor


def _set_candidate_status(candidate: FoundationCandidate, to_status: CandidateStatus, *, actor: str) -> None:
    to_value = to_status.value
    if candidate.status == to_value:
        return
    if not can_transition(LifecycleKind.CANDIDATE, candidate.status, to_value):
        raise IllegalTransition(f"candidate {candidate.id}: illegal transition {candidate.status!r} -> {to_value!r}")
    candidate.status = to_value
    candidate.updated_by = actor


def open_selection_run(
    db: Session,
    *,
    project_id: str,
    target_genome_snapshot_id: str,
    corpus_snapshot_id: str | None = None,
    created_by: str = "system",
) -> FoundationSelectionRun:
    """Open a new :class:`~aos_core.models.FoundationSelectionRun` in ``draft`` (design §13).

    Enforces the RFC-0020 invariant: at most one active (non-terminal) run per
    project — an existing non-terminal run must reach a lateral terminal
    state (blocked/cancelled/superseded) before a new one opens.
    """
    active = (
        db.query(FoundationSelectionRun)
        .filter(
            FoundationSelectionRun.project_id == project_id,
            FoundationSelectionRun.state.notin_(list(_LATERAL_RUN_STATES)),
        )
        .first()
    )
    if active is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"project {project_id} already has an active selection run ({active.id}, state="
                f"{active.state!r}); resolve or terminate it before opening a new one."
            ),
        )

    run = FoundationSelectionRun(
        project_id=project_id,
        target_genome_snapshot_id=target_genome_snapshot_id,
        corpus_snapshot_id=corpus_snapshot_id,
        state=SelectionRunState.DRAFT.value,
        summary="",
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def compile_requirements(
    db: Session, *, selection_run_id: str, created_by: str = "system"
) -> list[FoundationRequirement]:
    """Compile :class:`~aos_core.models.FoundationRequirement` rows from the run's
    target Genome snapshot's traits + the project's claims (design §8), then
    advance the run to ``requirements_compiled``.

    Gate: a ``hard_constraint`` requirement is only persisted when it carries
    at least one source ``claim_id`` AND a ``verification_method`` — an
    unverifiable hard constraint is never silently emitted (design §8).
    """
    run = db.get(FoundationSelectionRun, selection_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Selection run not found")

    genome_snapshot = db.get(GenomeSnapshot, run.target_genome_snapshot_id)
    if genome_snapshot is None:
        raise HTTPException(status_code=404, detail="Target genome snapshot not found")

    claims = db.query(Claim).filter(Claim.project_id == run.project_id).all()
    traits = db.query(GenomeTrait).filter(GenomeTrait.genome_snapshot_id == genome_snapshot.id).all()

    supporting_by_trait: dict[str, list[str]] = defaultdict(list)
    if traits:
        trait_ids = [t.id for t in traits]
        links = db.query(GenomeTraitClaim).filter(GenomeTraitClaim.trait_id.in_(trait_ids)).all()
        for link in links:
            if link.polarity == "supporting":
                supporting_by_trait[link.trait_id].append(link.claim_id)

    rows: list[FoundationRequirement] = []
    for rule in REQUIREMENT_COMPILATION_RULES:
        for spec in rule(claims=claims, traits=traits, supporting_by_trait=supporting_by_trait):
            if spec.requirement_type == RequirementType.HARD_CONSTRAINT and (
                not spec.claim_ids or not spec.verification_method
            ):
                # design §8 gate: never silently emit an unverifiable hard constraint.
                continue
            row = FoundationRequirement(
                selection_run_id=run.id,
                genome_snapshot_id=genome_snapshot.id,
                requirement_type=spec.requirement_type.value,
                domain=spec.domain.value,
                statement=spec.statement,
                priority=spec.priority.value,
                weight=spec.weight,
                veto_if_unsatisfied=spec.veto_if_unsatisfied,
                verification_method=spec.verification_method,
                claim_ids=list(spec.claim_ids),
                created_by=created_by,
                updated_by=created_by,
            )
            db.add(row)
            rows.append(row)
    db.flush()

    _advance_run(run, SelectionRunState.REQUIREMENTS_COMPILED, actor=created_by)
    db.commit()
    for row in rows:
        db.refresh(row)
    db.refresh(run)
    return rows


def create_candidate(
    db: Session,
    *,
    selection_run_id: str,
    name: str,
    summary: str = "",
    architecture_style: list[str] | None = None,
    reversibility: Reversibility | str = Reversibility.MEDIUM,
    recommendation_ref: str | None = None,
    created_by: str = "system",
) -> FoundationCandidate:
    """Manually author a :class:`~aos_core.models.FoundationCandidate` (design §9.3).

    Also the primitive :func:`generate_candidates` builds on top of.
    """
    candidate = FoundationCandidate(
        selection_run_id=selection_run_id,
        name=name,
        summary=summary,
        status=CandidateStatus.DRAFT.value,
        architecture_style=list(architecture_style or []),
        recommendation_ref=recommendation_ref,
        reversibility=reversibility.value if isinstance(reversibility, Reversibility) else reversibility,
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def add_element(
    db: Session,
    *,
    candidate_id: str,
    domain: FoundationDomain | str,
    title: str,
    decision: str,
    verification_method: str,
    rationale: str = "",
    technology_refs: list[str] | None = None,
    claim_ids: list[str] | None = None,
    requirement_ids: list[str] | None = None,
    alternatives_rejected: list[str] | None = None,
    tradeoffs: list[str] | None = None,
    risks: list[str] | None = None,
    created_by: str = "system",
) -> FoundationElement:
    """Manually author a :class:`~aos_core.models.FoundationElement` on a candidate
    (design §9.4). Also the primitive :func:`generate_candidates` builds on top of.
    """
    element = FoundationElement(
        candidate_id=candidate_id,
        domain=domain.value if isinstance(domain, FoundationDomain) else domain,
        title=title,
        decision=decision,
        rationale=rationale,
        technology_refs=list(technology_refs or []),
        claim_ids=list(claim_ids or []),
        requirement_ids=list(requirement_ids or []),
        alternatives_rejected=list(alternatives_rejected or []),
        tradeoffs=list(tradeoffs or []),
        risks=list(risks or []),
        verification_method=verification_method,
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(element)
    db.commit()
    db.refresh(element)
    return element


def generate_candidates(
    db: Session, *, selection_run_id: str, created_by: str = "system"
) -> list[FoundationCandidate]:
    """Run the deterministic candidate-generation templates (design §9,
    ``services/foundation_rules.py``'s ``CANDIDATE_TEMPLATES``) over the run's
    compiled requirements, then advance the run to ``candidates_generated``.
    """
    run = db.get(FoundationSelectionRun, selection_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Selection run not found")

    requirements = db.query(FoundationRequirement).filter(FoundationRequirement.selection_run_id == run.id).all()

    candidates: list[FoundationCandidate] = []
    for template in CANDIDATE_TEMPLATES:
        skeleton = template(requirements)
        candidate = create_candidate(
            db,
            selection_run_id=run.id,
            name=skeleton.name,
            summary=skeleton.summary,
            architecture_style=skeleton.architecture_style,
            reversibility=skeleton.reversibility,
            created_by=created_by,
        )
        for element_spec in skeleton.elements:
            add_element(
                db,
                candidate_id=candidate.id,
                domain=element_spec.domain,
                title=element_spec.title,
                decision=element_spec.decision,
                rationale=element_spec.rationale,
                technology_refs=element_spec.technology_refs,
                claim_ids=element_spec.claim_ids,
                requirement_ids=element_spec.requirement_ids,
                alternatives_rejected=element_spec.alternatives_rejected,
                tradeoffs=element_spec.tradeoffs,
                risks=element_spec.risks,
                verification_method=element_spec.verification_method,
                created_by=created_by,
            )
        candidates.append(candidate)

    _advance_run(run, SelectionRunState.CANDIDATES_GENERATED, actor=created_by)
    db.commit()
    for candidate in candidates:
        db.refresh(candidate)
    db.refresh(run)
    return candidates


def evaluate_eligibility(
    db: Session, *, selection_run_id: str, actor: str = "system"
) -> list[FoundationCandidate]:
    """AD-8 — before any weighted score, deterministically check every candidate's
    elements against every ``hard_constraint`` requirement; a violator's
    ``hard_constraint_violations`` is populated and its status set to
    ``rejected`` regardless of what its score would have been. Then advance
    the run to ``eligibility_review``.
    """
    run = db.get(FoundationSelectionRun, selection_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Selection run not found")

    hard_constraints = (
        db.query(FoundationRequirement)
        .filter(
            FoundationRequirement.selection_run_id == run.id,
            FoundationRequirement.requirement_type == RequirementType.HARD_CONSTRAINT.value,
        )
        .all()
    )
    candidates = db.query(FoundationCandidate).filter(FoundationCandidate.selection_run_id == run.id).all()

    for candidate in candidates:
        elements = db.query(FoundationElement).filter(FoundationElement.candidate_id == candidate.id).all()
        violated_ids = [
            requirement.id
            for requirement in hard_constraints
            if any(element_violates_requirement(requirement, element) for element in elements)
        ]
        candidate.hard_constraint_violations = violated_ids
        if violated_ids:
            _set_candidate_status(candidate, CandidateStatus.REJECTED, actor=actor)
        elif candidate.status == CandidateStatus.DRAFT.value:
            _set_candidate_status(candidate, CandidateStatus.ELIGIBLE, actor=actor)

    _advance_run(run, SelectionRunState.ELIGIBILITY_REVIEW, actor=actor)
    db.commit()
    for candidate in candidates:
        db.refresh(candidate)
    db.refresh(run)
    return candidates


def score_candidate(db: Session, *, candidate_id: str, actor: str = "system") -> FoundationCandidate:
    """Persist a design §10.3 score **vector** (one :class:`~aos_core.models.FoundationScore`
    row per criterion — never a lone scalar) for an ``eligible`` candidate.

    **AD-8**: refuses (HTTP 409) any candidate that is not currently
    ``eligible`` — most importantly a ``rejected`` (hard-constraint-violating)
    one; a candidate can never be score-laundered past an eligibility failure.
    ``uncertainty_penalty`` grows with evidence thinness (LES-023,
    ``foundation_rules.evidence_thinness``): a sparse-evidence candidate's
    penalty is strictly larger than a dense one's.
    """
    candidate = db.get(FoundationCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if candidate.status not in _SCORABLE_CANDIDATE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=(
                f"candidate {candidate.id} is {candidate.status!r}; only an 'eligible' candidate may be "
                "scored (AD-8: hard-constraint eligibility gates scoring, run evaluate_eligibility first)."
            ),
        )

    requirements = db.query(FoundationRequirement).filter(
        FoundationRequirement.selection_run_id == candidate.selection_run_id
    ).all()
    elements = db.query(FoundationElement).filter(FoundationElement.candidate_id == candidate.id).all()

    # Idempotent re-score: drop any prior vector for this candidate first.
    db.query(FoundationScore).filter(FoundationScore.candidate_id == candidate.id).delete()

    satisfied, unsatisfied = requirement_satisfaction(requirements, elements)
    candidate.satisfied_requirement_ids = satisfied
    candidate.unsatisfied_requirement_ids = unsatisfied

    vector: list[dict] = []
    for criterion_spec in score_criteria(requirements=requirements, elements=elements):
        adjusted_score = criterion_spec.raw_score * criterion_spec.weight - criterion_spec.uncertainty_penalty
        row = FoundationScore(
            candidate_id=candidate.id,
            criterion=criterion_spec.criterion.value,
            raw_score=criterion_spec.raw_score,
            weight=criterion_spec.weight,
            confidence=criterion_spec.confidence,
            uncertainty_penalty=criterion_spec.uncertainty_penalty,
            adjusted_score=adjusted_score,
            rationale=criterion_spec.rationale,
            supporting_claim_ids=list(criterion_spec.supporting_claim_ids),
            created_by=actor,
            updated_by=actor,
        )
        db.add(row)
        vector.append(
            {
                "criterion": row.criterion,
                "raw_score": row.raw_score,
                "weight": row.weight,
                "confidence": row.confidence,
                "uncertainty_penalty": row.uncertainty_penalty,
                "adjusted_score": row.adjusted_score,
            }
        )

    # design §10.3: the UI shows the vector, never a lone scalar — shape
    # metadata makes that explicit rather than implicit-by-convention.
    candidate.score_summary = {
        "vector_shape": "per_criterion",
        "criterion_count": len(vector),
        "criteria": vector,
    }
    candidate.confidence = sum(v["confidence"] for v in vector) / len(vector) if vector else 0.0
    candidate.updated_by = actor
    db.commit()
    db.refresh(candidate)
    return candidate
