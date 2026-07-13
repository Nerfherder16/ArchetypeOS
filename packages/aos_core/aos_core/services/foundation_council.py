"""Council & Validation engine (RFC-0021, Foundation Intelligence Slice 4,
AOS-COUNCIL-VALIDATION-MODELS-001).

Orchestrates the design's Stages 11-13 over Slice 3's eligible candidates:
:func:`review_candidate` reuses the existing, now-typed Council (``run_council``
+ ``synthesize_verdict`` + the typed ``{kind, detail, ref}`` payloads,
``services/council.py`` — RFC-0016 C2: a candidate review *is* a council review
with a subject, not a parallel review engine) and derives
:class:`~aos_core.models.FoundationObjection` rows from blocking concerns/
unsupported findings and :class:`~aos_core.models.ValidationTask` rows from (a)
high-uncertainty ``FoundationScore`` rows on the requirement-coverage criterion
and (b) a council agent that abstained (``status == "Needs Evidence"``) — the
deterministic reading of RFC-0021's Open Question 1 (AD-10: uncertainty becomes
validation work, never invented certainty). :func:`resolve_objection` runs the
open -> resolved/accepted_exception/converted_to_validation workflow (design
§11). :func:`record_validation_result` persists a pass/fail/inconclusive result,
flips the task's status through :mod:`aos_core.foundation.lifecycle`, and (on a
failed *blocking* task) marks its candidate ``challenged`` rather than rejected
— recoverable, per RFC-0021 Open Question 3. :func:`synthesize_dossier` re-runs
``synthesize_verdict`` over each reviewed candidate's agent outputs and
recommends — never selects (AD-9) — the top candidate with no unresolved
blocking objection and every blocking validation cleared. :func:`select_candidate`
is the mandatory human gate (design §13, Constitution IX/XIX): it 409s unless
those same two conditions hold, then sets the candidate ``selected``, advances
the run, and writes an :class:`~aos_core.models.ApprovalRecord` (the same
human-approval pattern ``services/decisions.py`` uses).

Every :class:`~aos_core.models.FoundationSelectionRun`/
:class:`~aos_core.models.FoundationCandidate`/:class:`~aos_core.models.ValidationTask`
state change is validated through :mod:`aos_core.foundation.lifecycle` — this
module adds no second transition table. ``_advance_run_at_least`` guards the
multi-candidate/multi-call case (this engine's calls are naturally idempotent
and out-of-order across a run's several candidates) against ever *overshooting*
a run past the caller's requested milestone via ``foundation._advance_run``'s
walk-to-target semantics.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..foundation.enums import (
    CandidateStatus,
    EvaluationCriterion,
    Materiality,
    SelectionRunState,
    ValidationStatus,
    ValidationType,
)
from ..foundation.lifecycle import LifecycleKind, can_transition, next_states
from ..models import (
    ApprovalRecord,
    Claim,
    CouncilReview,
    FoundationCandidate,
    FoundationDossier,
    FoundationElement,
    FoundationObjection,
    FoundationRequirement,
    FoundationScore,
    FoundationSelectionRun,
    ValidationResult,
    ValidationTask,
    now_utc,
)
from .council import run_council, synthesize_verdict
from .foundation import IllegalTransition, _advance_run, _set_candidate_status

__all__ = [
    "review_candidate",
    "resolve_objection",
    "record_validation_result",
    "synthesize_dossier",
    "select_candidate",
]

# design §10.3's REQUIREMENT_COVERAGE is this slice's designated "blocking"
# criterion (RFC-0021 Open Q1a) — the one whose thinness a human cannot simply
# accept without evidence. A score's ``uncertainty_penalty`` maxes at 0.5
# (``foundation_rules._MAX_UNCERTAINTY_PENALTY``); >= half that ceiling reads as
# "high uncertainty" and prescribes a validation task rather than a lower score
# standing in for missing evidence (AD-10).
_HIGH_UNCERTAINTY_THRESHOLD = 0.25

# The run-state forward order (mirrors foundation.py's linear chain) used by
# ``_advance_run_at_least`` to detect "already past the requested milestone"
# and skip, rather than letting ``_advance_run``'s walk overshoot it.
_RUN_ORDER: list[str] = [
    s.value
    for s in SelectionRunState
    if s.value not in (SelectionRunState.BLOCKED.value, SelectionRunState.CANCELLED.value, SelectionRunState.SUPERSEDED.value)
]

_OBJECTION_OPEN = "open"
_OBJECTION_TERMINAL_STATUSES = frozenset({"resolved", "accepted_exception", "converted_to_validation"})

_VALIDATION_OUTCOMES = frozenset({"passed", "failed", "inconclusive"})
_VALIDATION_OUTCOME_TO_STATUS: dict[str, str] = {
    "passed": ValidationStatus.PASSED.value,
    "failed": ValidationStatus.FAILED.value,
    "inconclusive": ValidationStatus.INCONCLUSIVE.value,
}


def _run_order_index(state: str) -> int:
    try:
        return _RUN_ORDER.index(state)
    except ValueError:
        return -1


def _advance_run_at_least(run: FoundationSelectionRun, target: SelectionRunState, *, actor: str) -> None:
    """Advance ``run`` to ``target`` unless it has already reached/passed it.

    ``foundation._advance_run`` walks forward one legal hop at a time until it
    reaches exactly ``target`` — safe when the caller knows the run is behind,
    but this engine's calls happen once per *candidate* (a run may already sit
    at or beyond a later milestone by the time a second candidate is reviewed).
    Without this guard a stale ``target`` would make ``_advance_run`` walk the
    run *past* its true state. A no-op when already there or further along.
    """
    if _run_order_index(run.state) >= _run_order_index(target.value):
        return
    _advance_run(run, target, actor=actor)


def _advance_validation_task(task: ValidationTask, target_status: str, *, actor: str) -> None:
    """Walk ``task.status`` forward through ``LifecycleKind.VALIDATION`` to
    ``target_status``, one legal hop at a time (mirrors
    ``foundation._advance_run``'s walk-to-target pattern for the selection-run
    table). Raises :class:`IllegalTransition` if no legal forward path exists."""
    if task.status == target_status:
        task.updated_by = actor
        return
    hops = 0
    max_hops = len(ValidationStatus) + 1
    while task.status != target_status:
        hops += 1
        if hops > max_hops:
            raise IllegalTransition(
                f"validation task {task.id}: no legal forward path from {task.status!r} to {target_status!r}"
            )
        reachable = next_states(LifecycleKind.VALIDATION, task.status)
        step = target_status if target_status in reachable else next(iter(reachable), None)
        if step is None or not can_transition(LifecycleKind.VALIDATION, task.status, step):
            raise IllegalTransition(f"validation task {task.id}: illegal transition {task.status!r} -> {step!r}")
        task.status = step
    task.updated_by = actor


def _item_text(item) -> str:
    """Human-readable text for a typed ``{kind, detail, ref}`` item or a plain string."""
    if isinstance(item, dict):
        detail = item.get("detail")
        return str(detail) if detail is not None else str(item)
    return str(item)


def review_candidate(db: Session, *, candidate_id: str, provider) -> CouncilReview:
    """Run the Council over a candidate's context and adjudicate the result.

    Builds a concise question/context string from the candidate's elements,
    the run's compiled requirements, its score vector, and its assumption/
    supporting claims; calls the existing ``run_council`` (project-scoped, per
    RFC-0016 C2 — no parallel evidence pipeline); tags the resulting
    :class:`~aos_core.models.CouncilReview` with the candidate/run; derives
    :class:`~aos_core.models.FoundationObjection` rows from every agent's
    ``concerns`` (blocking) and the review's ``unsupported_claims``
    (non-blocking, informational); derives :class:`~aos_core.models.ValidationTask`
    rows from (a) a high-``uncertainty_penalty`` ``FoundationScore`` on the
    requirement-coverage criterion and (b) any agent output that abstained
    (``status == "Needs Evidence"`` — the "required validation" signal, RFC-0021
    Open Q1b). Advances the candidate ``eligible -> challenged`` and the run
    ``-> council_review`` (``-> validation_required`` too if a blocking task was
    created).
    """
    candidate = db.get(FoundationCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    run = db.get(FoundationSelectionRun, candidate.selection_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Selection run not found")

    elements = db.query(FoundationElement).filter(FoundationElement.candidate_id == candidate.id).all()
    requirements = db.query(FoundationRequirement).filter(FoundationRequirement.selection_run_id == run.id).all()
    scores = db.query(FoundationScore).filter(FoundationScore.candidate_id == candidate.id).all()
    claim_ids = sorted({c for e in elements for c in (e.claim_ids or [])} | set(candidate.assumption_claim_ids or []))
    claims = db.query(Claim).filter(Claim.id.in_(claim_ids)).all() if claim_ids else []

    score_summary = ", ".join(f"{s.criterion}={s.adjusted_score:.3f}" for s in scores) or "no score vector yet"
    question = (
        f"Review foundation candidate '{candidate.name}' ({candidate.id}) for selection run {run.id}. "
        f"{len(elements)} element(s) across {len({e.domain for e in elements})} domain(s); "
        f"{len(requirements)} compiled requirement(s); score vector: {score_summary}; "
        f"{len(claims)} assumption/supporting claim(s)."
    )

    review = run_council(db, project_id=run.project_id, question=question, provider=provider)
    review.candidate_id = candidate.id
    review.selection_run_id = run.id
    db.add(review)

    if candidate.status == CandidateStatus.ELIGIBLE.value:
        _set_candidate_status(candidate, CandidateStatus.CHALLENGED, actor="foundation_council")

    objections: list[FoundationObjection] = []
    for output in review.agent_outputs:
        for concern in output.concerns or []:
            objections.append(
                FoundationObjection(
                    candidate_id=candidate.id,
                    review_id=review.id,
                    raised_by=output.agent_name,
                    objection=_item_text(concern),
                    materiality=(
                        Materiality.HIGH.value
                        if review.verdict in ("Reject", "Escalate to human")
                        else Materiality.MEDIUM.value
                    ),
                    blocking=True,
                    status=_OBJECTION_OPEN,
                )
            )
    for entry in review.unsupported_claims or []:
        raised_by = (entry.get("agent") if isinstance(entry, dict) else None) or "final_judge"
        claim_detail = _item_text(entry.get("claim")) if isinstance(entry, dict) else str(entry)
        objections.append(
            FoundationObjection(
                candidate_id=candidate.id,
                review_id=review.id,
                raised_by=raised_by,
                objection=f"Unsupported claim: {claim_detail}",
                materiality=Materiality.LOW.value,
                blocking=False,
                status=_OBJECTION_OPEN,
            )
        )
    db.add_all(objections)

    validation_tasks: list[ValidationTask] = []
    for score in scores:
        if score.criterion != EvaluationCriterion.REQUIREMENT_COVERAGE.value:
            continue
        if score.uncertainty_penalty < _HIGH_UNCERTAINTY_THRESHOLD:
            continue
        validation_tasks.append(
            ValidationTask(
                candidate_id=candidate.id,
                selection_run_id=run.id,
                title=f"Validate {score.criterion} for candidate '{candidate.name}'",
                validation_type=ValidationType.BENCHMARK.value,
                question=(
                    f"Is the {score.criterion} score for candidate '{candidate.name}' reliable given thin "
                    f"evidence (uncertainty_penalty={score.uncertainty_penalty:.3f})?"
                ),
                method="Gather additional supporting evidence/claims for the elements addressing this criterion.",
                success_criteria=["Evidence density for the criterion clears the uncertainty threshold."],
                failure_criteria=["Evidence remains insufficient to support the criterion's score."],
                required_evidence=["Additional claim(s) linked to the candidate's elements."],
                blocking=True,
                status=ValidationStatus.PROPOSED.value,
                result_claim_ids=[],
            )
        )
    for output in review.agent_outputs:
        if output.status != "Needs Evidence":
            continue
        validation_tasks.append(
            ValidationTask(
                candidate_id=candidate.id,
                selection_run_id=run.id,
                title=f"Gather evidence for {output.agent_name}'s assessment of '{candidate.name}'",
                validation_type=ValidationType.BENCHMARK.value,
                question=(
                    f"Does the project have sufficient evidence for {output.agent_name} to assess "
                    f"candidate '{candidate.name}'?"
                ),
                method="Council agent abstained (status='Needs Evidence') — RFC-0021 Open Q1b's required-validation signal.",
                success_criteria=["The re-run council agent reaches 'Complete' status."],
                failure_criteria=["Evidence remains absent after the validation window."],
                required_evidence=["Primary evidence for this project (research notes, decisions, DNA)."],
                blocking=True,
                status=ValidationStatus.PROPOSED.value,
                result_claim_ids=[],
            )
        )
    db.add_all(validation_tasks)
    db.flush()

    _advance_run_at_least(run, SelectionRunState.COUNCIL_REVIEW, actor="foundation_council")
    if any(task.blocking for task in validation_tasks):
        _advance_run_at_least(run, SelectionRunState.VALIDATION_REQUIRED, actor="foundation_council")

    db.commit()
    db.refresh(review)
    db.refresh(candidate)
    db.refresh(run)
    for objection in objections:
        db.refresh(objection)
    for task in validation_tasks:
        db.refresh(task)
    return review


def resolve_objection(
    db: Session,
    *,
    objection_id: str,
    status: str,
    resolution: str | None = None,
    validation_task_id: str | None = None,
    decision_id: str | None = None,
) -> FoundationObjection:
    """The objection resolution workflow (design §11): ``open`` ->
    ``resolved`` | ``accepted_exception`` | ``converted_to_validation``.

    404s a missing objection; **409** if it is not currently ``open`` (only an
    open objection is resolvable). ``status`` outside the three legal targets
    raises :class:`~aos_core.services.foundation.IllegalTransition`.
    ``converted_to_validation`` links an existing ``validation_task_id`` or —
    if none is supplied — creates a new blocking :class:`~aos_core.models.ValidationTask`
    for the objection's candidate and links that.
    """
    objection = db.get(FoundationObjection, objection_id)
    if objection is None:
        raise HTTPException(status_code=404, detail="Objection not found")
    if objection.status != _OBJECTION_OPEN:
        raise HTTPException(
            status_code=409,
            detail=f"objection {objection.id} is {objection.status!r}; only an 'open' objection may be resolved",
        )
    if status not in _OBJECTION_TERMINAL_STATUSES:
        raise IllegalTransition(
            f"objection {objection.id}: illegal target status {status!r}; must be one of "
            f"{sorted(_OBJECTION_TERMINAL_STATUSES)}"
        )

    if status == "converted_to_validation":
        if validation_task_id is None:
            candidate = db.get(FoundationCandidate, objection.candidate_id)
            if candidate is None:
                raise HTTPException(status_code=404, detail="Candidate not found for objection")
            task = ValidationTask(
                candidate_id=candidate.id,
                selection_run_id=candidate.selection_run_id,
                title=f"Validate objection: {objection.objection[:120]}",
                validation_type=ValidationType.BENCHMARK.value,
                question=objection.objection,
                method="Converted from a council objection (design §11 resolution workflow).",
                success_criteria=["The underlying objection's concern is evidenced and cleared."],
                failure_criteria=["The concern remains substantiated after validation."],
                required_evidence=["Evidence addressing the objection's stated concern."],
                blocking=objection.blocking,
                status=ValidationStatus.PROPOSED.value,
                result_claim_ids=[],
            )
            db.add(task)
            db.flush()
            validation_task_id = task.id
        objection.resolution_validation_task_id = validation_task_id

    if decision_id is not None:
        objection.resolution_decision_id = decision_id

    objection.status = status
    objection.resolution = resolution
    objection.updated_by = "foundation_council"
    db.commit()
    db.refresh(objection)
    return objection


def record_validation_result(
    db: Session,
    *,
    validation_task_id: str,
    outcome: str,
    summary: str | None = None,
    evidence: list | None = None,
    benchmark_ref: str | None = None,
    experiment_ref: str | None = None,
) -> ValidationResult:
    """Persist a :class:`~aos_core.models.ValidationResult`, flip the task's
    status through the lifecycle table, and propagate the outcome (design §11,
    AD-10).

    404s a missing task. ``outcome`` outside ``passed``/``failed``/
    ``inconclusive`` raises :class:`~aos_core.services.foundation.IllegalTransition`.
    A failed **blocking** task marks its candidate ``challenged`` — not
    ``rejected`` (RFC-0021 Open Q3: recoverable via re-validation) — when the
    candidate is still ``eligible`` (the common case, since ``review_candidate``
    already moves a reviewed candidate to ``challenged``; if it is already
    ``challenged`` this is a legal no-op). Once every *blocking*
    :class:`~aos_core.models.ValidationTask` for the run is ``passed``, the run
    advances to ``validation_complete``.
    """
    task = db.get(ValidationTask, validation_task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Validation task not found")
    if outcome not in _VALIDATION_OUTCOMES:
        raise IllegalTransition(f"validation task {task.id}: illegal outcome {outcome!r}; must be one of {sorted(_VALIDATION_OUTCOMES)}")

    _advance_validation_task(task, _VALIDATION_OUTCOME_TO_STATUS[outcome], actor="foundation_council")

    result = ValidationResult(
        validation_task_id=task.id,
        outcome=outcome,
        summary=summary,
        evidence=list(evidence or []),
        benchmark_ref=benchmark_ref,
        experiment_ref=experiment_ref,
        result_claim_ids=[],
    )
    db.add(result)

    candidate = db.get(FoundationCandidate, task.candidate_id)
    if outcome == "failed" and task.blocking and candidate is not None:
        if candidate.status == CandidateStatus.ELIGIBLE.value:
            _set_candidate_status(candidate, CandidateStatus.CHALLENGED, actor="foundation_council")
        # Already CHALLENGED (or beyond, legally unreachable backward) — the
        # candidate is not force-regressed; select_candidate's own gate is what
        # actually blocks selection (never invented certainty, AD-10).

    run = db.get(FoundationSelectionRun, task.selection_run_id)
    if run is not None:
        # The session runs with autoflush=False (conftest.py's db_session /
        # every hermetic fixture in this suite) — task.status was just mutated
        # in-memory by _advance_validation_task and must be flushed before this
        # query can see it, or a same-call "last blocking task just passed"
        # would misread the run as still having one outstanding.
        db.flush()
        remaining_blocking = (
            db.query(ValidationTask)
            .filter(
                ValidationTask.selection_run_id == run.id,
                ValidationTask.blocking.is_(True),
                ValidationTask.status != ValidationStatus.PASSED.value,
            )
            .count()
        )
        if remaining_blocking == 0:
            _advance_run_at_least(run, SelectionRunState.VALIDATION_COMPLETE, actor="foundation_council")

    db.commit()
    db.refresh(result)
    db.refresh(task)
    if candidate is not None:
        db.refresh(candidate)
    if run is not None:
        db.refresh(run)
    return result


def _has_council_review(db: Session, candidate_id: str) -> bool:
    return db.query(CouncilReview.id).filter(CouncilReview.candidate_id == candidate_id).first() is not None


def _candidate_clear_eligible(db: Session, candidate: FoundationCandidate) -> tuple[bool, int, int]:
    """Is ``candidate`` reviewed, free of unresolved blocking objections, AND
    free of unpassed blocking validation tasks? Returns ``(clear,
    open_blocking_objections, unpassed_blocking_tasks)``.

    A candidate with **no** ``CouncilReview`` at all is never "clear" — it has
    trivially zero objections/tasks, but recommending or selecting something
    that was never adversarially reviewed would defeat the point of this slice
    (design §13: the payoff of the review/objection/validation chain).
    """
    if not _has_council_review(db, candidate.id):
        return False, 0, 0
    open_blocking_objections = (
        db.query(FoundationObjection)
        .filter(
            FoundationObjection.candidate_id == candidate.id,
            FoundationObjection.blocking.is_(True),
            FoundationObjection.status == _OBJECTION_OPEN,
        )
        .count()
    )
    unpassed_blocking_tasks = (
        db.query(ValidationTask)
        .filter(
            ValidationTask.candidate_id == candidate.id,
            ValidationTask.blocking.is_(True),
            ValidationTask.status != ValidationStatus.PASSED.value,
        )
        .count()
    )
    clear = (
        candidate.status != CandidateStatus.REJECTED.value
        and open_blocking_objections == 0
        and unpassed_blocking_tasks == 0
    )
    return clear, open_blocking_objections, unpassed_blocking_tasks


_REVERSIBILITY_RANK = {"high": 0, "medium": 1, "low": 2}


def synthesize_dossier(db: Session, *, selection_run_id: str) -> FoundationDossier:
    """The Final Judge dossier (design §13): re-synthesizes each reviewed
    candidate's council output, then recommends — **never selects** (AD-9) —
    the top clear-eligible candidate (no unresolved blocking objection, every
    blocking validation cleared), ranked by adjusted score (ties broken toward
    higher reversibility, RFC-0021 Open Q2). Advances the run to
    ``ready_for_selection``. Idempotent: a second call updates the run's single
    dossier row rather than creating a duplicate ("one active dossier per run").
    """
    run = db.get(FoundationSelectionRun, selection_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Selection run not found")

    candidates = db.query(FoundationCandidate).filter(FoundationCandidate.selection_run_id == run.id).all()
    reviews = db.query(CouncilReview).filter(CouncilReview.selection_run_id == run.id).all()
    reviews_by_candidate: dict[str, list[CouncilReview]] = defaultdict(list)
    for review in reviews:
        if review.candidate_id:
            reviews_by_candidate[review.candidate_id].append(review)

    remaining_uncertainty: list[dict] = []
    rejected_alternatives: list[dict] = []
    ranked: list[tuple[float, FoundationCandidate]] = []

    for candidate in candidates:
        for review in reviews_by_candidate.get(candidate.id, []):
            synthesis = synthesize_verdict(review.agent_outputs)
            for entry in synthesis.get("unsupported_claims", []):
                remaining_uncertainty.append({"candidate_id": candidate.id, **entry})
            if synthesis.get("follow_up"):
                remaining_uncertainty.append(
                    {"candidate_id": candidate.id, "follow_up": synthesis["follow_up"]}
                )

        adjusted = sum(entry.get("adjusted_score", 0.0) for entry in (candidate.score_summary or {}).get("criteria", []))
        clear, open_objections, unpassed_tasks = _candidate_clear_eligible(db, candidate)
        if clear:
            ranked.append((adjusted, candidate))
        else:
            reason = (
                f"candidate status {candidate.status!r}"
                if candidate.status == CandidateStatus.REJECTED.value
                else (
                    f"{open_objections} unresolved blocking objection(s), "
                    f"{unpassed_tasks} unpassed blocking validation task(s)"
                )
            )
            rejected_alternatives.append({"candidate_id": candidate.id, "name": candidate.name, "reason": reason})

    ranked.sort(key=lambda pair: (-pair[0], _REVERSIBILITY_RANK.get(pair[1].reversibility, 1)))
    recommended = ranked[0][1] if ranked else None
    reasons: list[dict] = []
    if recommended is not None:
        reasons.append(
            {
                "candidate_id": recommended.id,
                "reason": (
                    f"Top clear-eligible candidate by adjusted score ({ranked[0][0]:.3f}); no unresolved "
                    "blocking objections; every blocking validation cleared."
                ),
            }
        )
        for adjusted, candidate in ranked[1:]:
            rejected_alternatives.append(
                {
                    "candidate_id": candidate.id,
                    "name": candidate.name,
                    "reason": f"Lower adjusted score ({adjusted:.3f}) than the recommended candidate.",
                }
            )

    verdict = "Recommended" if recommended is not None else "No clear-eligible candidate"

    dossier = (
        db.query(FoundationDossier)
        .filter(FoundationDossier.selection_run_id == run.id)
        .order_by(FoundationDossier.created_at.desc(), FoundationDossier.id.desc())
        .first()
    )
    if dossier is None:
        dossier = FoundationDossier(selection_run_id=run.id, created_by="foundation_council")
        db.add(dossier)

    dossier.recommended_candidate_id = recommended.id if recommended is not None else None
    dossier.verdict = verdict
    dossier.reasons = reasons
    dossier.remaining_uncertainty = remaining_uncertainty
    dossier.rejected_alternatives = rejected_alternatives
    dossier.conditions_of_approval = (
        ["Address any remaining non-blocking objections before baselining."] if recommended is not None else []
    )
    dossier.required_future_reviews = [
        "Re-run the council if the recommended candidate's elements change materially."
    ]
    dossier.updated_by = "foundation_council"

    _advance_run_at_least(run, SelectionRunState.READY_FOR_SELECTION, actor="foundation_council")

    db.commit()
    db.refresh(dossier)
    db.refresh(run)
    return dossier


def select_candidate(
    db: Session, *, selection_run_id: str, candidate_id: str, approver: str
) -> FoundationCandidate:
    """The mandatory human selection gate (design §13, Constitution IX/XIX, AD-9).

    404s a missing run/candidate (or a candidate not belonging to ``run``).
    **409** unless the candidate is not rejected/already-selected, has no
    unresolved blocking objection, and every blocking validation task is
    ``passed`` — ``ValidationStatus`` has no ``accepted_exception`` state (that
    vocabulary is an objection resolution, not a validation outcome; see the
    RFC-0021 build report). On success: sets the candidate ``selected``,
    advances the run to ``selected``, writes an
    :class:`~aos_core.models.ApprovalRecord` (the ``services/decisions.py``
    human-approval pattern), and stamps the run's dossier's
    ``approved_by``/``approved_at`` if one exists.
    """
    run = db.get(FoundationSelectionRun, selection_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Selection run not found")
    candidate = db.get(FoundationCandidate, candidate_id)
    if candidate is None or candidate.selection_run_id != run.id:
        raise HTTPException(status_code=404, detail="Candidate not found for this selection run")

    if candidate.status == CandidateStatus.SELECTED.value:
        raise HTTPException(status_code=409, detail=f"candidate {candidate.id} is already selected")
    if candidate.status in (CandidateStatus.REJECTED.value, CandidateStatus.DRAFT.value):
        raise HTTPException(
            status_code=409,
            detail=f"candidate {candidate.id} is {candidate.status!r}; not eligible for selection",
        )

    if not _has_council_review(db, candidate.id):
        raise HTTPException(
            status_code=409,
            detail=f"candidate {candidate.id} has not been through a council review yet (call review_candidate first)",
        )

    clear, open_objections, unpassed_tasks = _candidate_clear_eligible(db, candidate)
    if open_objections:
        raise HTTPException(
            status_code=409,
            detail=f"candidate {candidate.id} has {open_objections} unresolved blocking objection(s)",
        )
    if unpassed_tasks:
        raise HTTPException(
            status_code=409,
            detail=f"candidate {candidate.id} has {unpassed_tasks} unpassed blocking validation task(s)",
        )
    if not clear:
        # Defensive: _candidate_clear_eligible's third condition (candidate.status
        # != rejected) is already covered above, but keeps the gate total.
        raise HTTPException(status_code=409, detail=f"candidate {candidate.id} is not selectable")

    try:
        if candidate.status != CandidateStatus.SELECTABLE.value:
            _set_candidate_status(candidate, CandidateStatus.SELECTABLE, actor=approver)
        _set_candidate_status(candidate, CandidateStatus.SELECTED, actor=approver)
    except IllegalTransition as exc:
        raise HTTPException(
            status_code=409,
            detail=f"candidate {candidate.id} cannot be selected from status {candidate.status!r}: {exc}",
        ) from exc

    _advance_run_at_least(run, SelectionRunState.SELECTED, actor=approver)

    db.add(
        ApprovalRecord(
            project_id=run.project_id,
            actor=approver,
            reason=f"Foundation candidate '{candidate.name}' selected for run {run.id}",
            requested_capability="foundation.select_candidate",
            target=candidate.id,
            approval_status="approved",
        )
    )

    dossier = (
        db.query(FoundationDossier)
        .filter(FoundationDossier.selection_run_id == run.id)
        .order_by(FoundationDossier.created_at.desc(), FoundationDossier.id.desc())
        .first()
    )
    if dossier is not None:
        dossier.approved_by = approver
        dossier.approved_at = now_utc()
        dossier.updated_by = approver

    db.commit()
    db.refresh(candidate)
    db.refresh(run)
    return candidate
