"""C4 — canonical serialization / content-hash determinism (RFC-0017 / AOS-FOUND-CONTRACTS-001)."""
from __future__ import annotations

from aos_core.foundation.contracts import Claim, ClaimScope, Derivation
from aos_core.foundation.serialization import canonical_bytes, content_hash, set_hash


def _make_claim(**overrides) -> Claim:
    fields = dict(
        id="claim-1",
        project_id="proj-1",
        statement="The system must operate offline.",
        claim_type="requirement",
        truth_layer="claimed",
        domain="deployment",
        scope=ClaimScope(environment="production"),
        confidence=0.913456789,
        created_by="human",
        derivation=Derivation(method="direct"),
        minted_by="human",
    )
    fields.update(overrides)
    return Claim(**fields)


def test_content_hash_deterministic_across_two_constructions() -> None:
    a = _make_claim()
    b = _make_claim()
    assert content_hash(a) == content_hash(b)


def test_content_hash_deterministic_across_dict_key_insertion_order() -> None:
    scope_a = ClaimScope(environment="production", system_id="sys-1")
    scope_b = ClaimScope(system_id="sys-1", environment="production")
    a = _make_claim(scope=scope_a)
    b = _make_claim(scope=scope_b)
    assert content_hash(a) == content_hash(b)
    assert canonical_bytes(a) == canonical_bytes(b)


def test_changing_content_field_flips_hash() -> None:
    a = _make_claim()
    b = _make_claim(statement="A different statement entirely.")
    assert content_hash(a) != content_hash(b)


def test_changing_id_does_not_flip_hash() -> None:
    a = _make_claim(id="claim-1")
    b = _make_claim(id="claim-2")
    assert content_hash(a) == content_hash(b)


def test_changing_status_does_not_flip_hash() -> None:
    a = _make_claim(status="active")
    b = _make_claim(status="disputed")
    assert content_hash(a) == content_hash(b)


def test_float_formatting_is_stable() -> None:
    a = _make_claim(confidence=0.9100000001)
    b = _make_claim(confidence=0.91)
    # Both format to the same 6-significant-digit representation.
    assert content_hash(a) == content_hash(b)


def test_set_hash_is_permutation_invariant() -> None:
    hashes = ["aaa", "bbb", "ccc"]
    assert set_hash(hashes) == set_hash(list(reversed(hashes)))
    assert set_hash(hashes) == set_hash(["ccc", "aaa", "bbb"])


def test_set_hash_changes_with_membership() -> None:
    assert set_hash(["aaa", "bbb"]) != set_hash(["aaa", "bbb", "ccc"])


def test_canonical_bytes_no_insignificant_whitespace() -> None:
    a = _make_claim()
    raw = canonical_bytes(a)
    assert b", " not in raw
    assert b": " not in raw
