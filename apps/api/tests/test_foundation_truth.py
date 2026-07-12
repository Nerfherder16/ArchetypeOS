"""C3 — exhaustive MinterClass x TruthLayer matrix (RFC-0017 / AOS-FOUND-CONTRACTS-001)."""
from __future__ import annotations

import itertools

from aos_core.foundation.enums import TruthLayer
from aos_core.foundation.truth import MinterClass, allowed_truth_layers, may_mint

_EXPECTED: dict[MinterClass, frozenset[TruthLayer]] = {
    MinterClass.DETERMINISTIC_TOOL: frozenset({TruthLayer.OBSERVED, TruthLayer.INFERRED}),
    MinterClass.AGENT: frozenset({TruthLayer.CLAIMED, TruthLayer.INFERRED}),
    MinterClass.HUMAN: frozenset({TruthLayer.CLAIMED}),
    MinterClass.APPROVAL_PROCESS: frozenset({TruthLayer.DECIDED}),
}


def test_exhaustive_matrix_matches_design() -> None:
    for minter, layer in itertools.product(MinterClass, TruthLayer):
        expected = layer in _EXPECTED[minter]
        assert may_mint(minter, layer) is expected, f"{minter}, {layer}"


def test_allowed_truth_layers_matches_expected() -> None:
    for minter in MinterClass:
        assert allowed_truth_layers(minter) == _EXPECTED[minter]


def test_only_deterministic_tool_mints_observed() -> None:
    for minter in MinterClass:
        expected = minter is MinterClass.DETERMINISTIC_TOOL
        assert may_mint(minter, TruthLayer.OBSERVED) is expected


def test_only_approval_process_mints_decided() -> None:
    for minter in MinterClass:
        expected = minter is MinterClass.APPROVAL_PROCESS
        assert may_mint(minter, TruthLayer.DECIDED) is expected


def test_agent_never_mints_observed() -> None:
    assert may_mint(MinterClass.AGENT, TruthLayer.OBSERVED) is False


def test_deterministic_tool_mints_inferred_too() -> None:
    assert may_mint(MinterClass.DETERMINISTIC_TOOL, TruthLayer.INFERRED) is True
