"""Evidence authority matrix — design §4.7 worked examples (RFC-0017 / AOS-FOUND-CONTRACTS-001)."""
from __future__ import annotations

from aos_core.foundation.authority import AuthorityDomain, AuthorityLevel, authority_of
from aos_core.foundation.enums import SourceType


def test_repository_authority_examples() -> None:
    assert authority_of(SourceType.REPOSITORY, AuthorityDomain.RUNTIME) == AuthorityLevel.HIGH
    assert authority_of(SourceType.REPOSITORY, AuthorityDomain.ARCHITECTURE) == AuthorityLevel.HIGH
    assert authority_of(SourceType.REPOSITORY, AuthorityDomain.PRODUCT) == AuthorityLevel.LOW
    assert authority_of(SourceType.REPOSITORY, AuthorityDomain.LEGAL) == AuthorityLevel.NONE


def test_legal_communication_authority_examples() -> None:
    assert authority_of(SourceType.COMMUNICATION, AuthorityDomain.LEGAL) == AuthorityLevel.HIGH
    assert authority_of(SourceType.COMMUNICATION, AuthorityDomain.COMPLIANCE) == AuthorityLevel.HIGH
    assert authority_of(SourceType.COMMUNICATION, AuthorityDomain.RUNTIME) == AuthorityLevel.NONE
    assert authority_of(SourceType.COMMUNICATION, AuthorityDomain.PRODUCT) == AuthorityLevel.LOW


def test_human_input_authority_examples() -> None:
    assert authority_of(SourceType.HUMAN_INPUT, AuthorityDomain.PRODUCT) == AuthorityLevel.HIGH
    assert authority_of(SourceType.HUMAN_INPUT, AuthorityDomain.OPERATIONS) == AuthorityLevel.MEDIUM
    assert authority_of(SourceType.HUMAN_INPUT, AuthorityDomain.SECURITY) == AuthorityLevel.LOW
    assert authority_of(SourceType.HUMAN_INPUT, AuthorityDomain.LEGAL) == AuthorityLevel.NONE


def test_test_run_and_runtime_record_authority_examples() -> None:
    for source_type in (SourceType.TEST_RUN, SourceType.RUNTIME_RECORD):
        assert authority_of(source_type, AuthorityDomain.RUNTIME) == AuthorityLevel.HIGH
        assert authority_of(source_type, AuthorityDomain.SECURITY) == AuthorityLevel.MEDIUM
        assert authority_of(source_type, AuthorityDomain.PRODUCT) == AuthorityLevel.NONE


def test_external_reference_never_high_alone() -> None:
    for domain in AuthorityDomain:
        assert authority_of(SourceType.EXTERNAL_REFERENCE, domain) != AuthorityLevel.HIGH


def test_unknown_pair_defaults_to_low() -> None:
    # DATASET/COST is not in the seed matrix.
    assert authority_of(SourceType.DATASET, AuthorityDomain.COST) == AuthorityLevel.LOW


def test_authority_level_is_ordered() -> None:
    assert AuthorityLevel.NONE < AuthorityLevel.LOW < AuthorityLevel.MEDIUM < AuthorityLevel.HIGH
