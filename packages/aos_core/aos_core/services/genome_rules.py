"""Deterministic genome trait derivation rules (RFC-0019, AOS-GENOME-MODELS-001).

Each :class:`TraitRule` is a pure function over the claim set selected for one
``state_view`` (see ``services/genome.py``'s current/intended split): it
inspects claims by ``domain``/``claim_type``/keyword-in-``statement``/
``truth_layer`` and either fires (returning a :class:`TraitResult`) or
abstains (returns ``None``). No LLM, no network, no randomness — this module
is the genome analog of ``foundation/``: the single, hermetic, unit-testable
source of derivation logic (design §6.4; RFC-0019 non-goal: "no LLM trait
classification in this slice").

Seed rules cover the **foundation-shaping** dimensions first (breadth over the
full 16-dimension design grows in a later slice): ``runtime_topology``,
``deployment_ownership``, ``data_profile``, ``ai_autonomy``,
``assurance_criticality``, ``security_privacy``. :data:`FOUNDATION_SHAPING_DIMENSIONS`
is derived directly from the seed rule table — a single source, not a
second hand-maintained list.

AD-4 (RFC-0016, locked in RFC-0019): rules read **claims**, never
``RepositoryDNA`` directly. Repository facts already reach here as ``observed``
claims via the C5 backfill (RFC-0018 #214).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from ..foundation.enums import Criticality, GenomeDimension, Stability, TraitClassification
from ..models import Claim

__all__ = [
    "TraitResult",
    "TraitRule",
    "GENOME_RULES",
    "FOUNDATION_SHAPING_DIMENSIONS",
    "RULESET_VERSION",
]

# The ruleset id/version recorded on every GenomeSnapshot.generated_by — bump
# this string whenever the rule table's derivation logic changes materially,
# so a snapshot stays traceable to the rules that produced it.
RULESET_VERSION = "genome_rules_v1"


@dataclass(frozen=True)
class TraitResult:
    """What a firing :class:`TraitRule` found (design §6.4 ``GenomeTrait`` fields)."""

    value: bool | str | float | None
    classification: TraitClassification
    confidence: float
    supporting_claim_ids: list[str]
    opposing_claim_ids: list[str] = field(default_factory=list)
    rationale: str = ""
    value_type: str = "boolean"
    stability: Stability = Stability.STABLE
    source_methods: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TraitRule:
    """One deterministic derivation rule: dimension + trait_key + predicate + criticality.

    ``derive`` takes the full claim set already scoped to a ``state_view`` (by
    ``services/genome.py``) and returns a :class:`TraitResult` if it fires, or
    ``None`` if it abstains (no matching evidence in this claim set).
    """

    dimension: GenomeDimension
    trait_key: str
    criticality: Criticality
    derive: Callable[[list[Claim]], TraitResult | None]


# --- shared predicate helpers -----------------------------------------------


def _matching_claims(claims: list[Claim], *, keywords: tuple[str, ...], domain: str | None = None) -> list[Claim]:
    """Claims whose ``statement`` contains any keyword (case-insensitive), optionally filtered by ``domain``."""
    matched = []
    for claim in claims:
        if domain is not None and claim.domain != domain:
            continue
        statement = (claim.statement or "").lower()
        if any(keyword in statement for keyword in keywords):
            matched.append(claim)
    return matched


def _confidence_from(matched: list[Claim], *, cap: float = 0.95) -> float:
    """A rule's confidence: the mean confidence of its matched claims, capped so no
    single rule reports unrealistic certainty."""
    if not matched:
        return 0.0
    mean_confidence = sum(claim.confidence for claim in matched) / len(matched)
    return min(mean_confidence, cap)


def _classification_for(confidence: float) -> TraitClassification:
    return TraitClassification.PRIMARY if confidence >= 0.75 else TraitClassification.CONDITIONAL


# --- runtime_topology --------------------------------------------------------

_DISTRIBUTED_KEYWORDS = ("queue", "worker", "workers", "microservice", "message broker", "distributed")


def _derive_runtime_distributed(claims: list[Claim]) -> TraitResult | None:
    matched = _matching_claims(claims, keywords=_DISTRIBUTED_KEYWORDS, domain="runtime")
    if not matched:
        return None
    confidence = _confidence_from(matched)
    return TraitResult(
        value=True,
        classification=_classification_for(confidence),
        confidence=confidence,
        supporting_claim_ids=[claim.id for claim in matched],
        rationale="A runtime claim mentions a queue/worker/microservice/distributed execution pattern.",
        source_methods=["claim_keyword_match"],
    )


def _derive_runtime_monolithic(claims: list[Claim]) -> TraitResult | None:
    runtime_claims = [claim for claim in claims if claim.domain == "runtime"]
    if not runtime_claims:
        return None
    if _matching_claims(claims, keywords=_DISTRIBUTED_KEYWORDS, domain="runtime"):
        return None  # distributed signal present; mutually exclusive with the rule above
    confidence = _confidence_from(runtime_claims, cap=0.8)
    return TraitResult(
        value=True,
        classification=_classification_for(confidence),
        confidence=confidence,
        supporting_claim_ids=[claim.id for claim in runtime_claims],
        rationale="Runtime claims exist but none indicate a distributed/queue/worker topology.",
        source_methods=["claim_keyword_match"],
    )


# --- deployment_ownership -----------------------------------------------------

# Literal phrases that unambiguously mean local-first regardless of context.
_LOCAL_FIRST_LITERAL_KEYWORDS = (
    "local-first", "local first", "air-gapped", "air gapped", "no cloud", "offline-capable",
)
# A negation cue near "cloud" (e.g. "must not require public cloud connectivity",
# "no public cloud") also means local-first — checked separately from the
# literal keywords above because "no public cloud"/"not ... cloud" phrasing
# varies (RFC-0019 keeps the rule deterministic/simple; this regex covers the
# common negation shapes without a full NLP dependency).
_CLOUD_NEGATION_PATTERN = re.compile(r"\b(no|not|never|without)\b[^.]{0,40}\bcloud\b")
_MANAGED_CLOUD_KEYWORDS = ("managed cloud", "public cloud", "cloud provider", "cloud", "managed")


def _is_local_first_claim(statement: str) -> bool:
    lowered = statement.lower()
    if any(keyword in lowered for keyword in _LOCAL_FIRST_LITERAL_KEYWORDS):
        return True
    return bool(_CLOUD_NEGATION_PATTERN.search(lowered))


def _is_managed_cloud_claim(statement: str) -> bool:
    lowered = statement.lower()
    if _is_local_first_claim(lowered):
        return False  # a negated cloud mention is evidence AGAINST managed_cloud, not for it
    return any(keyword in lowered for keyword in _MANAGED_CLOUD_KEYWORDS)


def _derive_deployment_local_first(claims: list[Claim]) -> TraitResult | None:
    matched = [claim for claim in claims if _is_local_first_claim(claim.statement or "")]
    if not matched:
        return None
    opposing = [claim for claim in claims if _is_managed_cloud_claim(claim.statement or "") and claim not in matched]
    confidence = _confidence_from(matched)
    return TraitResult(
        value=True,
        classification=_classification_for(confidence),
        confidence=confidence,
        supporting_claim_ids=[claim.id for claim in matched],
        opposing_claim_ids=[claim.id for claim in opposing],
        rationale="A claim states the deployment must avoid public cloud / run air-gapped or local-first.",
        source_methods=["claim_keyword_match"],
    )


def _derive_deployment_managed_cloud(claims: list[Claim]) -> TraitResult | None:
    matched = [claim for claim in claims if _is_managed_cloud_claim(claim.statement or "")]
    if not matched:
        return None
    opposing = [claim for claim in claims if _is_local_first_claim(claim.statement or "")]
    confidence = _confidence_from(matched)
    return TraitResult(
        value=True,
        classification=_classification_for(confidence),
        confidence=confidence,
        supporting_claim_ids=[claim.id for claim in matched],
        opposing_claim_ids=[claim.id for claim in opposing],
        rationale="A claim mentions a managed/public cloud deployment target.",
        source_methods=["claim_keyword_match"],
    )


# --- data_profile -------------------------------------------------------------

_REGULATED_DATA_KEYWORDS = (
    "personal data", "financial data", "health data", "pii", "privileged", "category x data", "retention",
)


def _derive_data_profile_regulated(claims: list[Claim]) -> TraitResult | None:
    matched = _matching_claims(claims, keywords=_REGULATED_DATA_KEYWORDS)
    if not matched:
        return None
    confidence = _confidence_from(matched)
    return TraitResult(
        value=True,
        classification=_classification_for(confidence),
        confidence=confidence,
        supporting_claim_ids=[claim.id for claim in matched],
        rationale="A claim describes regulated/privileged/personal data handling.",
        source_methods=["claim_keyword_match"],
    )


# --- ai_autonomy ---------------------------------------------------------------

_AGENTIC_KEYWORDS = ("agent", "llm", "autonomous", "ai-generated", "agentic", "model-driven")


def _derive_ai_autonomy_agentic(claims: list[Claim]) -> TraitResult | None:
    matched = _matching_claims(claims, keywords=_AGENTIC_KEYWORDS)
    if not matched:
        return None
    confidence = _confidence_from(matched)
    return TraitResult(
        value=True,
        classification=_classification_for(confidence),
        confidence=confidence,
        supporting_claim_ids=[claim.id for claim in matched],
        rationale="A claim describes agent/LLM/autonomous execution.",
        source_methods=["claim_keyword_match"],
    )


# --- assurance_criticality -----------------------------------------------------

_CRITICAL_KEYWORDS = ("mission critical", "business critical", "safety critical", "high availability", "regulated", "auditable")


def _derive_assurance_business_critical(claims: list[Claim]) -> TraitResult | None:
    matched = _matching_claims(claims, keywords=_CRITICAL_KEYWORDS)
    if not matched:
        return None
    confidence = _confidence_from(matched)
    return TraitResult(
        value=True,
        classification=_classification_for(confidence),
        confidence=confidence,
        supporting_claim_ids=[claim.id for claim in matched],
        rationale="A claim states a mission/business/safety-critical assurance requirement.",
        source_methods=["claim_keyword_match"],
    )


# --- security_privacy -----------------------------------------------------------

_RESTRICTED_KEYWORDS = ("confidential", "restricted", "secret", "zero-trust", "tenant isolated", "data residency")


def _derive_security_restricted(claims: list[Claim]) -> TraitResult | None:
    matched = _matching_claims(claims, keywords=_RESTRICTED_KEYWORDS)
    if not matched:
        return None
    confidence = _confidence_from(matched)
    return TraitResult(
        value=True,
        classification=_classification_for(confidence),
        confidence=confidence,
        supporting_claim_ids=[claim.id for claim in matched],
        rationale="A claim describes a confidential/restricted/zero-trust security posture.",
        source_methods=["claim_keyword_match"],
    )


# --- the rule table ------------------------------------------------------------

GENOME_RULES: tuple[TraitRule, ...] = (
    TraitRule(
        GenomeDimension.RUNTIME_TOPOLOGY, "distributed_workers", Criticality.FOUNDATION_SHAPING, _derive_runtime_distributed
    ),
    TraitRule(
        GenomeDimension.RUNTIME_TOPOLOGY, "monolithic", Criticality.FOUNDATION_SHAPING, _derive_runtime_monolithic
    ),
    TraitRule(
        GenomeDimension.DEPLOYMENT_OWNERSHIP, "local_first", Criticality.FOUNDATION_SHAPING, _derive_deployment_local_first
    ),
    TraitRule(
        GenomeDimension.DEPLOYMENT_OWNERSHIP, "managed_cloud", Criticality.FOUNDATION_SHAPING,
        _derive_deployment_managed_cloud,
    ),
    TraitRule(
        GenomeDimension.DATA_PROFILE, "regulated_data", Criticality.FOUNDATION_SHAPING, _derive_data_profile_regulated
    ),
    TraitRule(
        GenomeDimension.AI_AUTONOMY, "agentic", Criticality.FOUNDATION_SHAPING, _derive_ai_autonomy_agentic
    ),
    TraitRule(
        GenomeDimension.ASSURANCE_CRITICALITY, "business_critical", Criticality.FOUNDATION_SHAPING,
        _derive_assurance_business_critical,
    ),
    TraitRule(
        GenomeDimension.SECURITY_PRIVACY, "restricted", Criticality.FOUNDATION_SHAPING, _derive_security_restricted
    ),
)

# Single source: the dimensions the seed rule table covers ARE the
# foundation-shaping dimensions for this slice (design breadth grows the rule
# table, not a second hand-maintained list).
FOUNDATION_SHAPING_DIMENSIONS: frozenset[GenomeDimension] = frozenset(rule.dimension for rule in GENOME_RULES)
