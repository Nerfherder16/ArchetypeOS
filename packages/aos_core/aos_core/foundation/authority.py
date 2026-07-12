"""Evidence authority matrix — design §4.7 made concrete.

Domain-specific authority: there is no universal source ranking. A contract has
high authority for legal constraints but none over runtime behavior; a
repository has high authority for current implementation but low authority over
business intent. ``authority_of`` is advisory input to conflict resolution and
requirement compilation in later slices; Slice 0 only defines and tests the
matrix.
"""
from __future__ import annotations

from enum import Enum

from .enums import SourceType


class AuthorityDomain(str, Enum):
    """A subject-matter domain a source may or may not be entitled to define."""

    RUNTIME = "runtime"
    PRODUCT = "product"
    LEGAL = "legal"
    SECURITY = "security"
    DATA = "data"
    ARCHITECTURE = "architecture"
    OPERATIONS = "operations"
    COST = "cost"
    COMPLIANCE = "compliance"


class AuthorityLevel(int, Enum):
    """An ordering (comparable), not a numeric score — see LES-023."""

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


# design §4.7 worked examples. Keyed by (SourceType, AuthorityDomain); an
# unspecified pair defaults to LOW (present-but-weak; never silently HIGH) via
# `authority_of`.
_MATRIX: dict[tuple[SourceType, AuthorityDomain], AuthorityLevel] = {
    # "A repository has high authority for current implementation but low
    # authority over business intent... none over legal constraints."
    (SourceType.REPOSITORY, AuthorityDomain.RUNTIME): AuthorityLevel.HIGH,
    (SourceType.REPOSITORY, AuthorityDomain.ARCHITECTURE): AuthorityLevel.HIGH,
    (SourceType.REPOSITORY, AuthorityDomain.PRODUCT): AuthorityLevel.LOW,
    (SourceType.REPOSITORY, AuthorityDomain.LEGAL): AuthorityLevel.NONE,
    # "A contract may have high authority for legal constraints but no
    # authority over runtime behavior." Modeled as a legal COMMUNICATION source.
    (SourceType.COMMUNICATION, AuthorityDomain.LEGAL): AuthorityLevel.HIGH,
    (SourceType.COMMUNICATION, AuthorityDomain.COMPLIANCE): AuthorityLevel.HIGH,
    (SourceType.COMMUNICATION, AuthorityDomain.RUNTIME): AuthorityLevel.NONE,
    (SourceType.COMMUNICATION, AuthorityDomain.PRODUCT): AuthorityLevel.LOW,
    # "A stakeholder interview may have high authority over product goals but
    # not security controls."
    (SourceType.HUMAN_INPUT, AuthorityDomain.PRODUCT): AuthorityLevel.HIGH,
    (SourceType.HUMAN_INPUT, AuthorityDomain.OPERATIONS): AuthorityLevel.MEDIUM,
    (SourceType.HUMAN_INPUT, AuthorityDomain.SECURITY): AuthorityLevel.LOW,
    (SourceType.HUMAN_INPUT, AuthorityDomain.LEGAL): AuthorityLevel.NONE,
    # Test runs / runtime records: strong authority over runtime fact, moderate
    # over security posture, none over product intent.
    (SourceType.TEST_RUN, AuthorityDomain.RUNTIME): AuthorityLevel.HIGH,
    (SourceType.TEST_RUN, AuthorityDomain.SECURITY): AuthorityLevel.MEDIUM,
    (SourceType.TEST_RUN, AuthorityDomain.PRODUCT): AuthorityLevel.NONE,
    (SourceType.RUNTIME_RECORD, AuthorityDomain.RUNTIME): AuthorityLevel.HIGH,
    (SourceType.RUNTIME_RECORD, AuthorityDomain.SECURITY): AuthorityLevel.MEDIUM,
    (SourceType.RUNTIME_RECORD, AuthorityDomain.PRODUCT): AuthorityLevel.NONE,
    # External references: research authority, never HIGH alone.
    (SourceType.EXTERNAL_REFERENCE, AuthorityDomain.RUNTIME): AuthorityLevel.MEDIUM,
    (SourceType.EXTERNAL_REFERENCE, AuthorityDomain.PRODUCT): AuthorityLevel.MEDIUM,
    (SourceType.EXTERNAL_REFERENCE, AuthorityDomain.LEGAL): AuthorityLevel.MEDIUM,
    (SourceType.EXTERNAL_REFERENCE, AuthorityDomain.SECURITY): AuthorityLevel.MEDIUM,
    (SourceType.EXTERNAL_REFERENCE, AuthorityDomain.DATA): AuthorityLevel.MEDIUM,
    (SourceType.EXTERNAL_REFERENCE, AuthorityDomain.ARCHITECTURE): AuthorityLevel.MEDIUM,
    (SourceType.EXTERNAL_REFERENCE, AuthorityDomain.OPERATIONS): AuthorityLevel.MEDIUM,
    (SourceType.EXTERNAL_REFERENCE, AuthorityDomain.COST): AuthorityLevel.MEDIUM,
    (SourceType.EXTERNAL_REFERENCE, AuthorityDomain.COMPLIANCE): AuthorityLevel.MEDIUM,
}


def authority_of(source_type: SourceType, domain: AuthorityDomain) -> AuthorityLevel:
    """The authority ``source_type`` carries in ``domain``.

    Returns the matrix value, or ``AuthorityLevel.LOW`` for any pair not
    explicitly encoded — present-but-weak, never silently HIGH.
    """
    return _MATRIX.get((source_type, domain), AuthorityLevel.LOW)
