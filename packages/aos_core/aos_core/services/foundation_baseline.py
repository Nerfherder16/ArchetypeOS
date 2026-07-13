"""Foundation Baseline engine (RFC-0022, Foundation Intelligence Slice 5,
AOS-FOUNDATION-BASELINE-MODELS-001).

Turns a **selected** foundation candidate (Slice 4's human-gated output) into
an immutable, versioned :class:`~aos_core.models.FoundationBaseline` — the
durable root-of-trust RFC-0015 Decisions and build plans derive from (design
§12 Stage 14, AD-12, AD-15). Minting is a **second mandatory human gate**:

- **409** unless the run is ``SELECTED`` with exactly one ``SELECTED``
  candidate.
- Freezes the candidate's approved :class:`~aos_core.models.FoundationElement`
  rows into :class:`~aos_core.models.FoundationBaselineElement` snapshots,
  each carrying a reproducible ``content_hash`` (``_element_content_hash``,
  projected through the RFC-0017 ``contracts.FoundationElement`` contract).
- Computes ``element_set_hash`` (permutation-invariant ``set_hash`` over the
  frozen elements' content hashes) and ``baseline_hash`` (a field-prefixed
  ``set_hash`` over the baseline's constituent identities — reproducible from
  the frozen constituents alone, so any tamper is detectable, C4).
- Mints and approves a governing anchor :class:`~aos_core.models.Decision`
  (AD-15) atomically with the baseline.
- Supersedes the project's prior ``active`` baseline (``status ->
  superseded``, version chain, ``baseline_version`` bumped) rather than
  editing it.
- Writes an :class:`~aos_core.models.ApprovalRecord` (the
  ``services/foundation_council.py::select_candidate`` human-approval
  pattern) and advances the run ``SELECTED -> BASELINED`` via
  ``foundation_council._advance_run_at_least``.

Every field except ``status`` is set at construction time and the row is
flushed exactly once (an INSERT, never followed by a further attribute
mutation before commit) — so the C4 ``before_update`` guard
(``models._assert_content_immutable``) never sees an UPDATE on a freshly
minted baseline/element row; only a later, explicit status transition
(:func:`supersede_baseline` / :func:`retire_baseline`) mutates a baseline
post-mint, and those touch only ``status`` (excluded from the guard's field
set), so they are permitted.

No new transition table — baseline status changes go through
:mod:`aos_core.foundation.lifecycle` (``LifecycleKind.BASELINE``).
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..foundation import contracts
from ..foundation.enums import BaselineStatus, CandidateStatus, SelectionRunState
from ..foundation.lifecycle import LifecycleKind, can_transition
from ..foundation.serialization import content_hash, set_hash
from ..foundation.truth import MinterClass
from ..models import (
    ApprovalRecord,
    Decision,
    FoundationBaseline,
    FoundationBaselineElement,
    FoundationCandidate,
    FoundationElement,
    FoundationSelectionRun,
    now_utc,
)
from .decisions import DECISION_DRAFT, approve_decision
from .foundation import IllegalTransition
from .foundation_council import _advance_run_at_least

__all__ = [
    "mint_baseline",
    "compare_baselines",
    "supersede_baseline",
    "retire_baseline",
]


def _element_content_hash(el: FoundationElement) -> str:
    """C4 — the reproducible content hash of a frozen element (design §12)."""
    return content_hash(
        contracts.FoundationElement(
            id=el.id,
            candidate_id=el.candidate_id,
            domain=el.domain,
            title=el.title,
            decision=el.decision,
            rationale=el.rationale,
            technology_refs=list(el.technology_refs or []),
            claim_ids=list(el.claim_ids or []),
            requirement_ids=list(el.requirement_ids or []),
            alternatives_rejected=list(el.alternatives_rejected or []),
            tradeoffs=list(el.tradeoffs or []),
            risks=list(el.risks or []),
            verification_method=el.verification_method,
            minted_by=MinterClass.DETERMINISTIC_TOOL,
        )
    )


def _baseline_hash(
    *,
    target_genome_snapshot_id: str,
    corpus_snapshot_id: str | None,
    approved_decision_id: str,
    candidate_id: str,
    element_set_hash: str,
    baseline_version: str,
    review_triggers: list[str] | None,
) -> str:
    """C4 — a field-prefixed ``set_hash`` so identity is unambiguous and
    reproducible from the baseline's constituents (design §12)."""
    parts = [
        f"genome:{target_genome_snapshot_id}",
        f"corpus:{corpus_snapshot_id or ''}",
        f"decision:{approved_decision_id}",
        f"candidate:{candidate_id}",
        f"elements:{element_set_hash}",
        f"version:{baseline_version}",
    ] + [f"trigger:{t}" for t in sorted(review_triggers or [])]
    return set_hash(parts)


def mint_baseline(
    db: Session, *, selection_run_id: str, approver: str, review_triggers: list[str] | None = None
) -> FoundationBaseline:
    """The mandatory human baseline gate (design §12 Stage 14, AD-12/AD-15).

    404s a missing run. **409** unless the run is ``SELECTED``; **409** if no
    ``SELECTED`` candidate exists for it. Freezes the candidate's elements,
    mints + approves an anchor Decision, supersedes the project's prior
    ``active`` baseline (version bump), inserts the new ``active`` baseline,
    writes an ``ApprovalRecord``, and advances the run to ``BASELINED``. All
    in one transaction (a single ``db.commit()``).
    """
    run = db.get(FoundationSelectionRun, selection_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Selection run not found")
    if run.state != SelectionRunState.SELECTED.value:
        raise HTTPException(
            status_code=409,
            detail=f"selection run {run.id} is in state {run.state!r}; must be 'selected' to mint a baseline",
        )

    candidate = (
        db.query(FoundationCandidate)
        .filter(
            FoundationCandidate.selection_run_id == run.id,
            FoundationCandidate.status == CandidateStatus.SELECTED.value,
        )
        .first()
    )
    if candidate is None:
        raise HTTPException(
            status_code=409, detail=f"selection run {run.id} has no selected candidate to baseline"
        )

    elements = db.query(FoundationElement).filter(FoundationElement.candidate_id == candidate.id).all()
    element_hashes = [_element_content_hash(el) for el in elements]
    element_set_hash = set_hash(element_hashes) if element_hashes else ""

    # AD-15: mint + approve the governing anchor Decision atomically with the
    # baseline. approve_decision commits its own unit of work — done BEFORE
    # the baseline/elements are constructed so no committed baseline row is
    # ever mutated afterward (C4).
    decision = Decision(
        project_id=run.project_id,
        title=f"Adopt foundation '{candidate.name}' for project {run.project_id}",
        context=f"Foundation baseline for selection run {run.id}; candidate {candidate.id}.",
        decision=f"Adopt foundation candidate '{candidate.name}'.",
        evidence=[
            {"type": "foundation_candidate", "id": candidate.id},
            {"type": "selection_run", "id": run.id},
        ],
        confidence=candidate.confidence or 0.0,
        status=DECISION_DRAFT,
        meta={"selection_run_id": run.id, "candidate_id": candidate.id},
    )
    db.add(decision)
    db.flush()
    decision = approve_decision(
        db, decision_id=decision.id, approver=approver, rationale="Foundation baseline approval"
    )

    prior = (
        db.query(FoundationBaseline)
        .filter(
            FoundationBaseline.project_id == run.project_id,
            FoundationBaseline.status == BaselineStatus.ACTIVE.value,
        )
        .order_by(FoundationBaseline.baseline_version.desc(), FoundationBaseline.created_at.desc())
        .first()
    )
    if prior is not None:
        target = BaselineStatus.SUPERSEDED.value
        if not can_transition(LifecycleKind.BASELINE, prior.status, target):
            raise IllegalTransition(f"baseline {prior.id}: illegal transition {prior.status!r} -> {target!r}")
        baseline_version = f"{int(float(prior.baseline_version)) + 1}.0"
        supersedes_baseline_id = prior.id
    else:
        baseline_version = "1.0"
        supersedes_baseline_id = None

    baseline_hash_value = _baseline_hash(
        target_genome_snapshot_id=run.target_genome_snapshot_id,
        corpus_snapshot_id=run.corpus_snapshot_id,
        approved_decision_id=decision.id,
        candidate_id=candidate.id,
        element_set_hash=element_set_hash,
        baseline_version=baseline_version,
        review_triggers=review_triggers,
    )

    if prior is not None:
        prior.status = BaselineStatus.SUPERSEDED.value
        prior.updated_by = approver

    baseline = FoundationBaseline(
        status=BaselineStatus.ACTIVE.value,
        project_id=run.project_id,
        candidate_id=candidate.id,
        selection_run_id=run.id,
        target_genome_snapshot_id=run.target_genome_snapshot_id,
        corpus_snapshot_id=run.corpus_snapshot_id,
        approved_decision_id=decision.id,
        supersedes_baseline_id=supersedes_baseline_id,
        baseline_version=baseline_version,
        element_set_hash=element_set_hash,
        baseline_hash=baseline_hash_value,
        review_triggers=list(review_triggers or []),
        minted_by="approval_process",
        approved_by=approver,
        approved_at=now_utc(),
        effective_from=now_utc(),
        created_by=approver,
        updated_by=approver,
    )
    db.add(baseline)
    db.flush()  # INSERT only — need baseline.id for the element rows' FK.

    element_rows = [
        FoundationBaselineElement(
            baseline_id=baseline.id,
            source_element_id=el.id,
            domain=el.domain,
            title=el.title,
            decision=el.decision,
            rationale=el.rationale or "",
            verification_method=el.verification_method,
            technology_refs=list(el.technology_refs or []),
            claim_ids=list(el.claim_ids or []),
            requirement_ids=list(el.requirement_ids or []),
            alternatives_rejected=list(el.alternatives_rejected or []),
            tradeoffs=list(el.tradeoffs or []),
            risks=list(el.risks or []),
            content_hash=el_hash,
            created_by=approver,
            updated_by=approver,
        )
        for el, el_hash in zip(elements, element_hashes)
    ]
    db.add_all(element_rows)

    db.add(
        ApprovalRecord(
            project_id=run.project_id,
            actor=approver,
            reason=f"Foundation baseline '{baseline.baseline_version}' minted for run {run.id}",
            requested_capability="foundation.mint_baseline",
            target=baseline.id,
            approval_status="approved",
        )
    )

    _advance_run_at_least(run, SelectionRunState.BASELINED, actor=approver)

    db.commit()
    db.refresh(baseline)
    db.refresh(run)
    return baseline


def compare_baselines(db: Session, *, base_id: str, other_id: str) -> dict:
    """A deterministic, read-only diff between two baselines (design §12).

    404s either missing baseline. Elements are diffed keyed by
    ``source_element_id``: ``elements_added`` are in ``other`` but not
    ``base``, ``elements_removed`` are in ``base`` but not ``other``,
    ``elements_changed`` share a ``source_element_id`` but differ in
    ``content_hash``. All lists are sorted deterministically.
    """
    base = db.get(FoundationBaseline, base_id)
    if base is None:
        raise HTTPException(status_code=404, detail="Baseline not found")
    other = db.get(FoundationBaseline, other_id)
    if other is None:
        raise HTTPException(status_code=404, detail="Baseline not found")

    base_elements = {
        e.source_element_id: e
        for e in db.query(FoundationBaselineElement).filter(FoundationBaselineElement.baseline_id == base.id).all()
    }
    other_elements = {
        e.source_element_id: e
        for e in db.query(FoundationBaselineElement).filter(FoundationBaselineElement.baseline_id == other.id).all()
    }

    added_ids = sorted(set(other_elements) - set(base_elements))
    removed_ids = sorted(set(base_elements) - set(other_elements))
    common_ids = sorted(set(base_elements) & set(other_elements))

    elements_added = [
        {"source_element_id": sid, "domain": other_elements[sid].domain, "title": other_elements[sid].title}
        for sid in added_ids
    ]
    elements_removed = [
        {"source_element_id": sid, "domain": base_elements[sid].domain, "title": base_elements[sid].title}
        for sid in removed_ids
    ]
    elements_changed = [
        {
            "source_element_id": sid,
            "domain": other_elements[sid].domain,
            "base_content_hash": base_elements[sid].content_hash,
            "other_content_hash": other_elements[sid].content_hash,
        }
        for sid in common_ids
        if base_elements[sid].content_hash != other_elements[sid].content_hash
    ]

    review_triggers_added = sorted(set(other.review_triggers or []) - set(base.review_triggers or []))
    review_triggers_removed = sorted(set(base.review_triggers or []) - set(other.review_triggers or []))

    return {
        "base_id": base.id,
        "other_id": other.id,
        "hash_equal": base.baseline_hash == other.baseline_hash,
        "elements_added": elements_added,
        "elements_removed": elements_removed,
        "elements_changed": elements_changed,
        "genome_changed": base.target_genome_snapshot_id != other.target_genome_snapshot_id,
        "genome": {"base": base.target_genome_snapshot_id, "other": other.target_genome_snapshot_id},
        "review_triggers_added": review_triggers_added,
        "review_triggers_removed": review_triggers_removed,
    }


def supersede_baseline(db: Session, *, baseline_id: str, actor: str) -> FoundationBaseline:
    """Transition a baseline ``active -> superseded`` (design §12, C4's one
    mutable field). 404s missing; raises :class:`IllegalTransition` if the
    current status has no legal edge to ``superseded``."""
    baseline = db.get(FoundationBaseline, baseline_id)
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")
    target = BaselineStatus.SUPERSEDED.value
    if not can_transition(LifecycleKind.BASELINE, baseline.status, target):
        raise IllegalTransition(f"baseline {baseline.id}: illegal transition {baseline.status!r} -> {target!r}")
    baseline.status = target
    baseline.updated_by = actor
    db.commit()
    db.refresh(baseline)
    return baseline


def retire_baseline(db: Session, *, baseline_id: str, actor: str) -> FoundationBaseline:
    """Transition a baseline to ``retired`` (design §12). 404s missing;
    raises :class:`IllegalTransition` if the current status has no legal edge
    to ``retired`` (e.g. from ``active`` directly is legal; ``superseded`` too)."""
    baseline = db.get(FoundationBaseline, baseline_id)
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")
    target = BaselineStatus.RETIRED.value
    if not can_transition(LifecycleKind.BASELINE, baseline.status, target):
        raise IllegalTransition(f"baseline {baseline.id}: illegal transition {baseline.status!r} -> {target!r}")
    baseline.status = target
    baseline.updated_by = actor
    db.commit()
    db.refresh(baseline)
    return baseline
