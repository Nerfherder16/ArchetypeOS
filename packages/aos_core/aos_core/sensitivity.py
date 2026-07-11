"""Shared sensitivity classification (AOS-NODE-EXECUTION-001).

One validated sensitivity type for the whole system. Routing eligibility, job
origination, and the API boundary all rank/validate through here, so an unknown or
misspelled value can no longer be silently treated as ``public`` (the fail-OPEN
hazard in the old ``routing._rank``: ``except ValueError: return 0``). Unknown
values rank ABOVE every real ceiling — they fail CLOSED (never eligible) — and the
API validators reject them outright.
"""

from __future__ import annotations

from enum import Enum


class Sensitivity(str, Enum):
    """Ordered data-sensitivity classes; lower index = less sensitive."""

    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"


# Ladder as a tuple (index = rank). A node runs work at or below its declared
# ``max_sensitivity`` ceiling, never above it.
SENSITIVITY_ORDER: tuple[str, ...] = tuple(s.value for s in Sensitivity)


def is_valid_sensitivity(value: str) -> bool:
    return value in SENSITIVITY_ORDER


def validate_sensitivity(value: str) -> str:
    """Return ``value`` if it is a known sensitivity, else raise ``ValueError``.

    Use at API/origination boundaries so an unknown class is a 4xx, not a silent
    downgrade to public.
    """
    if value not in SENSITIVITY_ORDER:
        raise ValueError(
            f"unknown sensitivity {value!r}; must be one of {SENSITIVITY_ORDER}"
        )
    return value


def sensitivity_rank(value: str) -> int:
    """Rank a sensitivity for ceiling comparison — FAIL CLOSED on unknown.

    A known value returns its ladder index. An unknown/misspelled value returns a
    rank ABOVE every real class, so ``rank(job) > rank(node_ceiling)`` holds for
    every node and the job is never eligible — the opposite of the old fail-open
    behaviour where an unknown value collapsed to ``public`` (rank 0).
    """
    try:
        return SENSITIVITY_ORDER.index(value)
    except ValueError:
        return len(SENSITIVITY_ORDER)


__all__ = [
    "Sensitivity",
    "SENSITIVITY_ORDER",
    "is_valid_sensitivity",
    "validate_sensitivity",
    "sensitivity_rank",
]
