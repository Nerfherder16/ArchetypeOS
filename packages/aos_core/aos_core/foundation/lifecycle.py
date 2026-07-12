"""Lifecycle transition tables — data-driven, not code-branching.

One ``dict[str, frozenset[str]]`` per entity lifecycle, keyed and valued by each
entity's status enum ``.value`` strings (design §12/§13 and the per-entity status
fields in §4-§11). ``can_transition``/``next_states`` are pure and total: an
unknown kind or state never raises, it simply returns "no legal edge."

Slice 4/5's persisted state machine (the ``services/jobs.py`` owned-transition CAS
pattern) validates the *edge* through this table — one source for "is this
transition legal," testable without a DB.
"""
from __future__ import annotations

from enum import Enum

from .enums import (
    BaselineStatus,
    CandidateStatus,
    ClaimStatus,
    ConflictStatus,
    GenomeStatus,
    SelectionRunState,
    ValidationStatus,
)


class LifecycleKind(str, Enum):
    """Which entity's status machine a transition check applies to."""

    SELECTION_RUN = "selection_run"
    CLAIM = "claim"
    CONFLICT = "conflict"
    GENOME = "genome"
    CANDIDATE = "candidate"
    VALIDATION = "validation"
    BASELINE = "baseline"


# design §13 — the forward progression through the Selection Run stages.
_SELECTION_RUN_FORWARD: dict[str, str] = {
    SelectionRunState.DRAFT.value: SelectionRunState.INTAKE_COMPLETE.value,
    SelectionRunState.INTAKE_COMPLETE.value: SelectionRunState.CORPUS_FROZEN.value,
    SelectionRunState.CORPUS_FROZEN.value: SelectionRunState.EVIDENCE_EXTRACTED.value,
    SelectionRunState.EVIDENCE_EXTRACTED.value: SelectionRunState.CURRENT_STATE_RECONSTRUCTED.value,
    SelectionRunState.CURRENT_STATE_RECONSTRUCTED.value: SelectionRunState.INTENT_RECONSTRUCTED.value,
    SelectionRunState.INTENT_RECONSTRUCTED.value: SelectionRunState.RECONCILED.value,
    SelectionRunState.RECONCILED.value: SelectionRunState.GENOME_REVIEW.value,
    SelectionRunState.GENOME_REVIEW.value: SelectionRunState.REQUIREMENTS_COMPILED.value,
    SelectionRunState.REQUIREMENTS_COMPILED.value: SelectionRunState.CANDIDATES_GENERATED.value,
    SelectionRunState.CANDIDATES_GENERATED.value: SelectionRunState.ELIGIBILITY_REVIEW.value,
    SelectionRunState.ELIGIBILITY_REVIEW.value: SelectionRunState.COUNCIL_REVIEW.value,
    SelectionRunState.COUNCIL_REVIEW.value: SelectionRunState.VALIDATION_REQUIRED.value,
    SelectionRunState.VALIDATION_REQUIRED.value: SelectionRunState.VALIDATION_COMPLETE.value,
    SelectionRunState.VALIDATION_COMPLETE.value: SelectionRunState.READY_FOR_SELECTION.value,
    SelectionRunState.READY_FOR_SELECTION.value: SelectionRunState.SELECTED.value,
    SelectionRunState.SELECTED.value: SelectionRunState.BASELINED.value,
    SelectionRunState.BASELINED.value: SelectionRunState.EXECUTION_COMPILED.value,
    SelectionRunState.EXECUTION_COMPILED.value: SelectionRunState.MONITORING.value,
    # design §16 — drift-triggered reevaluation reopens Genome review.
    SelectionRunState.MONITORING.value: SelectionRunState.GENOME_REVIEW.value,
}

# Terminal lateral states every non-terminal Selection Run state may reach.
_SELECTION_RUN_LATERALS: frozenset[str] = frozenset(
    {
        SelectionRunState.BLOCKED.value,
        SelectionRunState.CANCELLED.value,
        SelectionRunState.SUPERSEDED.value,
    }
)

# Every state that is NOT itself a lateral terminal is "non-terminal" and may
# also transition to any of the three laterals.
_SELECTION_RUN_NON_TERMINAL: frozenset[str] = frozenset(
    s.value for s in SelectionRunState if s.value not in _SELECTION_RUN_LATERALS
)

SELECTION_RUN_TRANSITIONS: dict[str, frozenset[str]] = {
    frm: frozenset({to}) | _SELECTION_RUN_LATERALS for frm, to in _SELECTION_RUN_FORWARD.items()
}
# The laterals themselves are terminal (no outgoing edges).
for _lateral in _SELECTION_RUN_LATERALS:
    SELECTION_RUN_TRANSITIONS.setdefault(_lateral, frozenset())


CLAIM_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    ClaimStatus.ACTIVE.value: frozenset(
        {ClaimStatus.DISPUTED.value, ClaimStatus.SUPERSEDED.value, ClaimStatus.REJECTED.value, ClaimStatus.RESOLVED.value}
    ),
    ClaimStatus.DISPUTED.value: frozenset(
        {ClaimStatus.ACTIVE.value, ClaimStatus.RESOLVED.value, ClaimStatus.REJECTED.value, ClaimStatus.SUPERSEDED.value}
    ),
    ClaimStatus.RESOLVED.value: frozenset({ClaimStatus.SUPERSEDED.value}),
    ClaimStatus.REJECTED.value: frozenset(),
    ClaimStatus.SUPERSEDED.value: frozenset(),
}

CONFLICT_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    ConflictStatus.OPEN.value: frozenset(
        {ConflictStatus.ACCEPTED_EXCEPTION.value, ConflictStatus.RESOLVED.value, ConflictStatus.SUPERSEDED.value}
    ),
    ConflictStatus.ACCEPTED_EXCEPTION.value: frozenset({ConflictStatus.RESOLVED.value, ConflictStatus.SUPERSEDED.value}),
    ConflictStatus.RESOLVED.value: frozenset({ConflictStatus.SUPERSEDED.value}),
    ConflictStatus.SUPERSEDED.value: frozenset(),
}

GENOME_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    GenomeStatus.DRAFT.value: frozenset({GenomeStatus.REVIEWED.value}),
    GenomeStatus.REVIEWED.value: frozenset({GenomeStatus.DRAFT.value, GenomeStatus.APPROVED.value}),
    GenomeStatus.APPROVED.value: frozenset({GenomeStatus.SUPERSEDED.value}),
    GenomeStatus.SUPERSEDED.value: frozenset(),
}

CANDIDATE_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    CandidateStatus.DRAFT.value: frozenset({CandidateStatus.ELIGIBLE.value, CandidateStatus.REJECTED.value}),
    CandidateStatus.ELIGIBLE.value: frozenset({CandidateStatus.CHALLENGED.value, CandidateStatus.REJECTED.value}),
    CandidateStatus.CHALLENGED.value: frozenset(
        {CandidateStatus.VALIDATION_REQUIRED.value, CandidateStatus.SELECTABLE.value, CandidateStatus.REJECTED.value}
    ),
    CandidateStatus.VALIDATION_REQUIRED.value: frozenset({CandidateStatus.SELECTABLE.value, CandidateStatus.REJECTED.value}),
    CandidateStatus.SELECTABLE.value: frozenset({CandidateStatus.SELECTED.value, CandidateStatus.REJECTED.value}),
    CandidateStatus.SELECTED.value: frozenset(),
    CandidateStatus.REJECTED.value: frozenset(),
}

VALIDATION_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    ValidationStatus.PROPOSED.value: frozenset({ValidationStatus.APPROVED.value}),
    ValidationStatus.APPROVED.value: frozenset({ValidationStatus.RUNNING.value}),
    ValidationStatus.RUNNING.value: frozenset(
        {ValidationStatus.PASSED.value, ValidationStatus.FAILED.value, ValidationStatus.INCONCLUSIVE.value}
    ),
    ValidationStatus.PASSED.value: frozenset(),
    ValidationStatus.FAILED.value: frozenset({ValidationStatus.PROPOSED.value}),
    ValidationStatus.INCONCLUSIVE.value: frozenset({ValidationStatus.PROPOSED.value}),
}

BASELINE_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    BaselineStatus.ACTIVE.value: frozenset({BaselineStatus.SUPERSEDED.value, BaselineStatus.RETIRED.value}),
    BaselineStatus.SUPERSEDED.value: frozenset({BaselineStatus.RETIRED.value}),
    BaselineStatus.RETIRED.value: frozenset(),
}

_TABLES: dict[LifecycleKind, dict[str, frozenset[str]]] = {
    LifecycleKind.SELECTION_RUN: SELECTION_RUN_TRANSITIONS,
    LifecycleKind.CLAIM: CLAIM_STATUS_TRANSITIONS,
    LifecycleKind.CONFLICT: CONFLICT_STATUS_TRANSITIONS,
    LifecycleKind.GENOME: GENOME_STATUS_TRANSITIONS,
    LifecycleKind.CANDIDATE: CANDIDATE_STATUS_TRANSITIONS,
    LifecycleKind.VALIDATION: VALIDATION_STATUS_TRANSITIONS,
    LifecycleKind.BASELINE: BASELINE_STATUS_TRANSITIONS,
}


def next_states(kind: LifecycleKind, frm: str) -> frozenset[str]:
    """Legal next states from ``frm`` under ``kind``'s transition table.

    Pure and total: an unknown ``kind`` or unknown ``frm`` returns the empty
    frozenset rather than raising.
    """
    table = _TABLES.get(kind)
    if table is None:
        return frozenset()
    return table.get(frm, frozenset())


def can_transition(kind: LifecycleKind, frm: str, to: str) -> bool:
    """Is ``frm -> to`` a legal edge under ``kind``'s transition table?

    Pure and total: an unknown ``kind``/``frm``/``to`` returns ``False``, never
    raises.
    """
    return to in next_states(kind, frm)
