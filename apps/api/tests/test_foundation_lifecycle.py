"""Lifecycle transition tables — pure, total (RFC-0017 / AOS-FOUND-CONTRACTS-001)."""
from __future__ import annotations

from aos_core.foundation.enums import SelectionRunState
from aos_core.foundation.lifecycle import (
    BASELINE_STATUS_TRANSITIONS,
    CANDIDATE_STATUS_TRANSITIONS,
    CLAIM_STATUS_TRANSITIONS,
    CONFLICT_STATUS_TRANSITIONS,
    GENOME_STATUS_TRANSITIONS,
    SELECTION_RUN_TRANSITIONS,
    VALIDATION_STATUS_TRANSITIONS,
    LifecycleKind,
    can_transition,
    next_states,
)

_LATERALS = {"blocked", "cancelled", "superseded"}


def test_known_forward_edge_is_legal() -> None:
    assert can_transition(LifecycleKind.SELECTION_RUN, "draft", "intake_complete") is True


def test_illegal_edge_is_false() -> None:
    assert can_transition(LifecycleKind.SELECTION_RUN, "draft", "baselined") is False


def test_unknown_kind_returns_false_not_raise() -> None:
    assert can_transition("not_a_kind", "draft", "intake_complete") is False  # type: ignore[arg-type]


def test_unknown_state_returns_false_not_raise() -> None:
    assert can_transition(LifecycleKind.SELECTION_RUN, "nonexistent_state", "draft") is False
    assert can_transition(LifecycleKind.SELECTION_RUN, "draft", "nonexistent_state") is False


def test_next_states_unknown_kind_returns_empty_frozenset() -> None:
    assert next_states("bogus", "draft") == frozenset()  # type: ignore[arg-type]


def test_every_non_terminal_selection_run_state_reaches_all_laterals() -> None:
    for state in SelectionRunState:
        if state.value in _LATERALS:
            continue
        reachable = next_states(LifecycleKind.SELECTION_RUN, state.value)
        assert _LATERALS <= reachable, f"{state.value} missing a lateral edge: {reachable}"


def test_laterals_are_terminal() -> None:
    for lateral in _LATERALS:
        assert next_states(LifecycleKind.SELECTION_RUN, lateral) == frozenset()


def test_monitoring_reopens_to_genome_review() -> None:
    assert can_transition(LifecycleKind.SELECTION_RUN, "monitoring", "genome_review") is True


def test_full_forward_progression_is_legal() -> None:
    progression = [
        "draft",
        "intake_complete",
        "corpus_frozen",
        "evidence_extracted",
        "current_state_reconstructed",
        "intent_reconstructed",
        "reconciled",
        "genome_review",
        "requirements_compiled",
        "candidates_generated",
        "eligibility_review",
        "council_review",
        "validation_required",
        "validation_complete",
        "ready_for_selection",
        "selected",
        "baselined",
        "execution_compiled",
        "monitoring",
    ]
    for frm, to in zip(progression, progression[1:]):
        assert can_transition(LifecycleKind.SELECTION_RUN, frm, to) is True, f"{frm} -> {to}"


def test_claim_status_transitions_table_is_total_and_pure() -> None:
    assert can_transition(LifecycleKind.CLAIM, "active", "disputed") is True
    assert can_transition(LifecycleKind.CLAIM, "rejected", "active") is False
    assert SELECTION_RUN_TRANSITIONS  # sanity: module-level tables are populated
    assert CLAIM_STATUS_TRANSITIONS["active"]


def test_conflict_status_transitions() -> None:
    assert can_transition(LifecycleKind.CONFLICT, "open", "resolved") is True
    assert can_transition(LifecycleKind.CONFLICT, "superseded", "open") is False
    assert CONFLICT_STATUS_TRANSITIONS["superseded"] == frozenset()


def test_genome_status_transitions() -> None:
    assert can_transition(LifecycleKind.GENOME, "draft", "reviewed") is True
    assert can_transition(LifecycleKind.GENOME, "approved", "draft") is False
    assert GENOME_STATUS_TRANSITIONS["approved"] == frozenset({"superseded"})


def test_candidate_status_transitions() -> None:
    assert can_transition(LifecycleKind.CANDIDATE, "draft", "eligible") is True
    assert can_transition(LifecycleKind.CANDIDATE, "selected", "draft") is False
    assert CANDIDATE_STATUS_TRANSITIONS["selected"] == frozenset()


def test_validation_status_transitions() -> None:
    assert can_transition(LifecycleKind.VALIDATION, "running", "passed") is True
    assert can_transition(LifecycleKind.VALIDATION, "passed", "running") is False
    assert VALIDATION_STATUS_TRANSITIONS["passed"] == frozenset()


def test_baseline_status_transitions() -> None:
    assert can_transition(LifecycleKind.BASELINE, "active", "superseded") is True
    assert can_transition(LifecycleKind.BASELINE, "retired", "active") is False
    assert BASELINE_STATUS_TRANSITIONS["retired"] == frozenset()
