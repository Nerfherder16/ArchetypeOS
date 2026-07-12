"""C1 — a decided Claim is a Decision projection (RFC-0017 / AOS-FOUND-CONTRACTS-001)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from aos_core.foundation.contracts import Claim, Derivation


def _base_fields(**overrides) -> dict:
    fields = dict(
        id="claim-1",
        project_id="proj-1",
        statement="PostgreSQL selected as the authoritative structured store.",
        claim_type="decision_candidate",
        truth_layer="decided",
        domain="data",
        created_by="approval-process",
        derivation=Derivation(method="approved"),
        minted_by="approval_process",
        decision_ref="decision-42",
    )
    fields.update(overrides)
    return fields


def test_valid_decided_claim_constructs() -> None:
    claim = Claim(**_base_fields())
    assert claim.truth_layer.value == "decided"
    assert claim.decision_ref == "decision-42"


def test_decided_claim_without_approved_derivation_raises() -> None:
    with pytest.raises(ValidationError):
        Claim(**_base_fields(derivation=Derivation(method="direct")))


def test_decided_claim_without_decision_ref_raises() -> None:
    with pytest.raises(ValidationError):
        Claim(**_base_fields(decision_ref=None))


def test_non_decided_claim_with_decision_ref_raises() -> None:
    fields = _base_fields(
        truth_layer="claimed",
        derivation=Derivation(method="direct"),
        minted_by="human",
    )
    # decision_ref left set from _base_fields — must be rejected for non-decided claims.
    with pytest.raises(ValidationError):
        Claim(**fields)


def test_non_decided_claim_without_decision_ref_constructs() -> None:
    fields = _base_fields(
        truth_layer="claimed",
        derivation=Derivation(method="direct"),
        minted_by="human",
        decision_ref=None,
    )
    claim = Claim(**fields)
    assert claim.decision_ref is None
