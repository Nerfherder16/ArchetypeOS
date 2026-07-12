"""C3 — the deterministic-only-``observed`` truth-layer minter guard.

RFC-0016's C3 reconciliation ("only deterministic tooling may mint `observed`
claims") becomes a pure, exhaustively-testable function here, before any row
exists to violate it. Slice 1's ``create_claim`` calls ``may_mint`` as a guard;
``contracts.Claim`` also calls it at construction time (C3 validator).

Load-bearing rows: only ``DETERMINISTIC_TOOL`` may mint ``observed``; only
``APPROVAL_PROCESS`` may mint ``decided``; ``AGENT`` can never mint ``observed``.
``DETERMINISTIC_TOOL`` also gets ``inferred`` — deterministic derivation (e.g. "a
lockfile + a Dockerfile => this service exists") is a legitimate machine
inference; the guard's job is to keep *observed* and *decided* honest.
"""
from __future__ import annotations

from enum import Enum

from .enums import TruthLayer


class MinterClass(str, Enum):
    """Who/what is asserting a claim."""

    DETERMINISTIC_TOOL = "deterministic_tool"
    AGENT = "agent"
    HUMAN = "human"
    APPROVAL_PROCESS = "approval_process"


_ALLOWED: dict[MinterClass, frozenset[TruthLayer]] = {
    MinterClass.DETERMINISTIC_TOOL: frozenset({TruthLayer.OBSERVED, TruthLayer.INFERRED}),
    MinterClass.AGENT: frozenset({TruthLayer.CLAIMED, TruthLayer.INFERRED}),
    MinterClass.HUMAN: frozenset({TruthLayer.CLAIMED}),
    MinterClass.APPROVAL_PROCESS: frozenset({TruthLayer.DECIDED}),
}


def allowed_truth_layers(minter: MinterClass) -> frozenset[TruthLayer]:
    """The truth layers ``minter`` is permitted to mint. Total: unknown key raises KeyError
    only if given something that isn't a ``MinterClass`` member (impossible with type-checked
    input); every real ``MinterClass`` member has an entry."""
    return _ALLOWED[minter]


def may_mint(minter: MinterClass, layer: TruthLayer) -> bool:
    """Is ``minter`` allowed to mint a claim at truth layer ``layer``?"""
    return layer in _ALLOWED.get(minter, frozenset())
