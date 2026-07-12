"""Deterministic Foundation requirement-compilation rules + candidate-generation
templates + eligibility/scoring helpers (RFC-0020, AOS-FOUNDATION-MODELS-001).

This module is the foundation analog of ``genome_rules.py``: pure functions
over already-loaded rows (claims, genome traits, persisted requirements/
elements) that either fire or abstain. No LLM, no network, no randomness
(RFC-0020 non-goal: deterministic + human first, agent generation is Slice 4).

Three families of pure function live here:

- **Requirement compilation** (``REQUIREMENT_COMPILATION_RULES``): a
  ``constraint`` claim -> ``hard_constraint`` (veto-bearing); a
  ``preference`` claim -> ``preference``; a foundation-shaping
  :class:`~aos_core.models.GenomeTrait` -> ``required_capability``/
  ``quality_attribute`` (design §8).
- **Candidate generation templates** (``CANDIDATE_TEMPLATES``): a
  *recommended* (feature-complete) and a *conservative* (reduced-complexity)
  candidate skeleton, both derived from the same compiled requirement set
  (design §9, RFC-0020 Open Q2).
- **Eligibility + scoring** (:func:`element_violates_requirement`,
  :func:`score_criteria`): the AD-8 hard-constraint check and the
  deterministic subset of design §10.2's 20 evaluation criteria this slice
  can score from requirement-coverage/evidence-density alone (RFC-0020 Open
  Q3) — the rest are not invented.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from ..foundation.enums import (
    ClaimType,
    Criticality,
    EvaluationCriterion,
    FoundationDomain,
    GenomeDimension,
    Priority,
    RequirementType,
    Reversibility,
    TraitClassification,
)

__all__ = [
    "RequirementSpec",
    "ElementSpec",
    "CandidateSkeleton",
    "CriterionScoreSpec",
    "compile_hard_constraints_from_claims",
    "compile_preferences_from_claims",
    "compile_capabilities_from_foundation_shaping_traits",
    "REQUIREMENT_COMPILATION_RULES",
    "recommended_candidate_template",
    "conservative_candidate_template",
    "CANDIDATE_TEMPLATES",
    "element_violates_requirement",
    "evidence_thinness",
    "requirement_satisfaction",
    "score_criteria",
]


# --------------------------------------------------------------------------
# domain mapping (claim.domain free-text / GenomeDimension -> FoundationDomain)
# --------------------------------------------------------------------------

# Ordered so more-specific keywords are checked first; a claim/trait domain
# that matches nothing falls back to ARCHITECTURE (never invents a domain).
_DOMAIN_KEYWORD_MAP: tuple[tuple[tuple[str, ...], FoundationDomain], ...] = (
    (("deployment", "infrastructure", "infra"), FoundationDomain.DEPLOYMENT),
    (("data", "privacy", "pii"), FoundationDomain.DATA),
    (("security",), FoundationDomain.SECURITY_PRIVACY),
    (("runtime", "workload"), FoundationDomain.RUNTIME),
    (("integration",), FoundationDomain.INTEGRATION),
    (("identity", "auth"), FoundationDomain.IDENTITY_AUTHORITY),
    (("reliability", "availability", "assurance"), FoundationDomain.RELIABILITY),
    (("observability", "monitoring"), FoundationDomain.OBSERVABILITY),
    (("verification", "testing"), FoundationDomain.VERIFICATION),
    (("workflow", "development"), FoundationDomain.DEVELOPMENT_WORKFLOW),
    (("agent", "ai", "autonomy"), FoundationDomain.AGENT_GOVERNANCE),
    (("operations", "ops"), FoundationDomain.OPERATIONS),
    (("economics", "cost", "budget"), FoundationDomain.ECONOMICS),
    (("migration",), FoundationDomain.MIGRATION_EVOLUTION),
    (("product", "boundary", "scope"), FoundationDomain.PRODUCT_BOUNDARY),
    (("architecture",), FoundationDomain.ARCHITECTURE),
)


def _map_domain(domain: str) -> FoundationDomain:
    lowered = (domain or "").lower()
    for keywords, foundation_domain in _DOMAIN_KEYWORD_MAP:
        if any(keyword in lowered for keyword in keywords):
            return foundation_domain
    return FoundationDomain.ARCHITECTURE


# The seed genome_rules.py dimensions (FOUNDATION_SHAPING_DIMENSIONS) mapped
# to the foundation domain each dimension's trait most directly shapes.
_DIMENSION_DOMAIN_MAP: dict[GenomeDimension, FoundationDomain] = {
    GenomeDimension.RUNTIME_TOPOLOGY: FoundationDomain.RUNTIME,
    GenomeDimension.DEPLOYMENT_OWNERSHIP: FoundationDomain.DEPLOYMENT,
    GenomeDimension.DATA_PROFILE: FoundationDomain.DATA,
    GenomeDimension.AI_AUTONOMY: FoundationDomain.AGENT_GOVERNANCE,
    GenomeDimension.ASSURANCE_CRITICALITY: FoundationDomain.RELIABILITY,
    GenomeDimension.SECURITY_PRIVACY: FoundationDomain.SECURITY_PRIVACY,
}

_VERIFICATION_METHOD_BY_DOMAIN: dict[FoundationDomain, str] = {
    FoundationDomain.DEPLOYMENT: "deployment topology review against the constraint statement",
    FoundationDomain.DATA: "data-handling / retention audit against the constraint statement",
    FoundationDomain.SECURITY_PRIVACY: "security review (design ValidationType.SECURITY_REVIEW)",
    FoundationDomain.RUNTIME: "runtime architecture review against the constraint statement",
    FoundationDomain.RELIABILITY: "reliability/availability benchmark against the constraint statement",
    FoundationDomain.AGENT_GOVERNANCE: "agent-governance / autonomy policy review",
}
_DEFAULT_VERIFICATION_METHOD = "manual review against the constraint statement (no domain-specific method seeded yet)"


# --------------------------------------------------------------------------
# requirement compilation
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RequirementSpec:
    """What a firing requirement-compilation rule produced (design §8 fields)."""

    requirement_type: RequirementType
    domain: FoundationDomain
    statement: str
    priority: Priority
    weight: float
    veto_if_unsatisfied: bool
    verification_method: str
    claim_ids: list[str]
    rationale: str = ""


def compile_hard_constraints_from_claims(
    *, claims: Iterable, traits: Iterable = (), supporting_by_trait: dict | None = None
) -> list[RequirementSpec]:
    """design §8: every ``constraint`` claim is a veto-bearing ``hard_constraint``."""
    specs: list[RequirementSpec] = []
    for claim in claims:
        if claim.claim_type != ClaimType.CONSTRAINT.value:
            continue
        domain = _map_domain(claim.domain)
        specs.append(
            RequirementSpec(
                requirement_type=RequirementType.HARD_CONSTRAINT,
                domain=domain,
                statement=claim.statement,
                priority=Priority.MUST,
                weight=1.0,
                veto_if_unsatisfied=True,
                verification_method=_VERIFICATION_METHOD_BY_DOMAIN.get(domain, _DEFAULT_VERIFICATION_METHOD),
                claim_ids=[claim.id],
                rationale="A 'constraint' claim is always a veto-bearing hard constraint (design §8).",
            )
        )
    return specs


def compile_preferences_from_claims(
    *, claims: Iterable, traits: Iterable = (), supporting_by_trait: dict | None = None
) -> list[RequirementSpec]:
    """design §8: a ``preference`` claim becomes a non-veto ``preference`` requirement."""
    specs: list[RequirementSpec] = []
    for claim in claims:
        if claim.claim_type != ClaimType.PREFERENCE.value:
            continue
        domain = _map_domain(claim.domain)
        specs.append(
            RequirementSpec(
                requirement_type=RequirementType.PREFERENCE,
                domain=domain,
                statement=claim.statement,
                priority=Priority.COULD,
                weight=0.3,
                veto_if_unsatisfied=False,
                verification_method="stakeholder confirmation that the delivered design aligns with the stated preference",
                claim_ids=[claim.id],
                rationale="A 'preference' claim is a non-veto-bearing preference requirement (design §8).",
            )
        )
    return specs


def compile_capabilities_from_foundation_shaping_traits(
    *, claims: Iterable = (), traits: Iterable, supporting_by_trait: dict
) -> list[RequirementSpec]:
    """design §8: an evidence-backed foundation-shaping Genome trait becomes a
    ``required_capability`` (runtime/AI-autonomy dimensions) or a
    ``quality_attribute`` (the other seed dimensions). An ``unknown``
    classification never fires (nothing to compile yet — no invented
    requirement)."""
    specs: list[RequirementSpec] = []
    for trait in traits:
        if trait.criticality != Criticality.FOUNDATION_SHAPING.value:
            continue
        if trait.classification == TraitClassification.UNKNOWN.value:
            continue
        dimension = GenomeDimension(trait.dimension)
        domain = _DIMENSION_DOMAIN_MAP.get(dimension, FoundationDomain.ARCHITECTURE)
        requirement_type = (
            RequirementType.REQUIRED_CAPABILITY
            if dimension in (GenomeDimension.RUNTIME_TOPOLOGY, GenomeDimension.AI_AUTONOMY)
            else RequirementType.QUALITY_ATTRIBUTE
        )
        specs.append(
            RequirementSpec(
                requirement_type=requirement_type,
                domain=domain,
                statement=(
                    f"The system's {dimension.value.replace('_', ' ')} trait ({trait.trait_key}) must be "
                    f"honored: {trait.rationale}"
                ),
                priority=Priority.SHOULD,
                weight=max(trait.confidence, 0.3),
                veto_if_unsatisfied=False,
                verification_method=_VERIFICATION_METHOD_BY_DOMAIN.get(domain, _DEFAULT_VERIFICATION_METHOD),
                claim_ids=list((supporting_by_trait or {}).get(trait.id, [])),
                rationale=(
                    f"Foundation-shaping Genome trait {dimension.value}/{trait.trait_key} "
                    f"(confidence {trait.confidence:.2f})."
                ),
            )
        )
    return specs


# Every rule shares the ``(claims, traits, supporting_by_trait)`` signature —
# breadth grows this tuple, never a second hand-maintained call site.
REQUIREMENT_COMPILATION_RULES: tuple = (
    compile_hard_constraints_from_claims,
    compile_preferences_from_claims,
    compile_capabilities_from_foundation_shaping_traits,
)


# --------------------------------------------------------------------------
# candidate generation templates
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ElementSpec:
    """A :class:`~aos_core.models.FoundationElement` skeleton (design §9.4)."""

    domain: FoundationDomain
    title: str
    decision: str
    rationale: str
    verification_method: str
    technology_refs: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    requirement_ids: list[str] = field(default_factory=list)
    alternatives_rejected: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateSkeleton:
    """A :class:`~aos_core.models.FoundationCandidate` skeleton + its elements (design §9.3)."""

    name: str
    summary: str
    architecture_style: list[str]
    reversibility: Reversibility
    elements: list[ElementSpec]


def _group_by_domain(requirements: Iterable) -> dict[str, list]:
    groups: dict[str, list] = defaultdict(list)
    for requirement in requirements:
        groups[requirement.domain].append(requirement)
    return groups


def _domain_verification_method(domain_requirements: list) -> str:
    hard = [r for r in domain_requirements if r.requirement_type == RequirementType.HARD_CONSTRAINT.value]
    if hard:
        return hard[0].verification_method
    return domain_requirements[0].verification_method


def recommended_candidate_template(requirements: Iterable) -> CandidateSkeleton:
    """A feature-complete candidate: every requirement domain gets an element that
    honors its hard constraints AND its capabilities/quality-attributes/preferences."""
    elements: list[ElementSpec] = []
    for domain, domain_reqs in sorted(_group_by_domain(requirements).items()):
        hard = [r for r in domain_reqs if r.requirement_type == RequirementType.HARD_CONSTRAINT.value]
        other = [r for r in domain_reqs if r.requirement_type != RequirementType.HARD_CONSTRAINT.value]
        forbidden = sorted({term for r in hard for term in _forbidden_terms(r.statement)})
        decision_parts = []
        if hard:
            avoid_clause = f", avoiding {', '.join(forbidden)}" if forbidden else ""
            decision_parts.append(f"Fully honor every hard constraint in {domain}{avoid_clause}.")
        if other:
            decision_parts.append(
                f"Additionally address {len(other)} required-capability/quality-attribute/preference "
                f"requirement(s) in {domain} with a feature-complete, requirement-driven design."
            )
        if not decision_parts:
            decision_parts.append(f"No requirements recorded in {domain} yet; default coherent design applied.")
        claim_ids = sorted({c for r in domain_reqs for c in (r.claim_ids or [])})
        elements.append(
            ElementSpec(
                domain=FoundationDomain(domain),
                title=f"{domain.replace('_', ' ').title()} approach (recommended)",
                decision=" ".join(decision_parts),
                rationale=(
                    f"Recommended candidate: maximizes requirement coverage in {domain} "
                    f"({len(domain_reqs)} requirement(s))."
                ),
                technology_refs=[],
                claim_ids=claim_ids,
                requirement_ids=[r.id for r in domain_reqs],
                alternatives_rejected=["the conservative/reduced-complexity candidate's simpler approach"],
                tradeoffs=["higher operational complexity in exchange for broader requirement coverage"],
                risks=[] if hard else ["no hard constraint recorded in this domain yet"],
                verification_method=_domain_verification_method(domain_reqs),
            )
        )
    return CandidateSkeleton(
        name="Recommended",
        summary="Feature-complete candidate addressing every compiled requirement domain.",
        architecture_style=["modular-service-with-workers"],
        reversibility=Reversibility.MEDIUM,
        elements=elements,
    )


def conservative_candidate_template(requirements: Iterable) -> CandidateSkeleton:
    """A reduced-complexity candidate: only domains with a hard_constraint or
    required_capability get an element (design §9 — genuinely distinct from
    the recommended candidate, per-domain, not a cosmetic variant)."""
    elements: list[ElementSpec] = []
    for domain, domain_reqs in sorted(_group_by_domain(requirements).items()):
        hard = [r for r in domain_reqs if r.requirement_type == RequirementType.HARD_CONSTRAINT.value]
        must_have = [
            r
            for r in domain_reqs
            if r.requirement_type in (RequirementType.HARD_CONSTRAINT.value, RequirementType.REQUIRED_CAPABILITY.value)
        ]
        if not must_have:
            continue
        forbidden = sorted({term for r in hard for term in _forbidden_terms(r.statement)})
        avoid_clause = f", avoiding {', '.join(forbidden)}" if forbidden else ""
        decision = (
            f"Honor every hard constraint and required capability in {domain} using the simplest compliant "
            f"approach{avoid_clause}, deferring optional quality attributes and preferences to reduce complexity."
        )
        claim_ids = sorted({c for r in must_have for c in (r.claim_ids or [])})
        elements.append(
            ElementSpec(
                domain=FoundationDomain(domain),
                title=f"{domain.replace('_', ' ').title()} approach (conservative)",
                decision=decision,
                rationale=(
                    f"Conservative candidate: minimal viable coverage of {len(must_have)} must-have "
                    f"requirement(s) in {domain}."
                ),
                technology_refs=[],
                claim_ids=claim_ids,
                requirement_ids=[r.id for r in must_have],
                alternatives_rejected=["the recommended/feature-complete candidate's broader approach"],
                tradeoffs=["reduced capability/preference coverage in exchange for lower operational complexity"],
                risks=[],
                verification_method=_domain_verification_method(must_have),
            )
        )
    return CandidateSkeleton(
        name="Conservative (reduced-complexity)",
        summary="Minimal-viable candidate addressing only must-have requirements per domain.",
        architecture_style=["single-service-monolith"],
        reversibility=Reversibility.HIGH,
        elements=elements,
    )


CANDIDATE_TEMPLATES: tuple = (recommended_candidate_template, conservative_candidate_template)


# --------------------------------------------------------------------------
# AD-8 eligibility: deterministic hard-constraint violation detection
# --------------------------------------------------------------------------

# A hard-constraint statement is read as FORBIDDING a term only when the term
# follows a negation cue — a statement merely mentioning a term isn't treated
# as prohibiting it (keeps this a keyword rule, not free NLP, matching
# genome_rules.py's style).
_NEGATION_CUES: tuple[str, ...] = ("must not", "may not", "shall not", "cannot", "without", "never", "no ")

# A small, extensible vocabulary of terms hard constraints commonly forbid.
# Breadth grows this tuple as new constraint domains get evidenced rules
# (mirrors genome_rules.py's keyword-bank style) — never invented per-test.
_KNOWN_CONSTRAINT_TERMS: tuple[str, ...] = (
    "public cloud",
    "managed cloud",
    "cloud provider",
    "third-party hosting",
    "unencrypted storage",
    "shared tenancy",
    "cross-border transfer",
    "manual deployment",
    "single point of failure",
)


def _forbidden_terms(statement: str) -> list[str]:
    lowered = (statement or "").lower()
    if not any(cue in lowered for cue in _NEGATION_CUES):
        return []
    return [term for term in _KNOWN_CONSTRAINT_TERMS if term in lowered]


# Cues that mean an element's mention of a forbidden term is itself a
# negation/compliance statement (e.g. "avoiding public cloud dependencies"),
# not an affirmative violation.
_AFFIRMATION_NEGATION_CUES: tuple[str, ...] = (
    "no ",
    "not ",
    "without",
    "never",
    "avoid",
    "honoring",
    "honors",
    "compliant with",
    "consistent with",
    "in line with",
    "excludes",
    "rejects",
    "prohibit",
)


def _term_is_affirmed(text: str, term: str, *, window: int = 48) -> bool:
    """Does ``text`` assert ``term`` (rather than negate/avoid it)? Looks at
    the ``window`` characters immediately preceding the term's first
    occurrence for a negation/avoidance cue."""
    lowered = text.lower()
    idx = lowered.find(term)
    if idx == -1:
        return False
    preceding = lowered[max(0, idx - window) : idx]
    return not any(cue in preceding for cue in _AFFIRMATION_NEGATION_CUES)


def element_violates_requirement(requirement, element) -> bool:
    """AD-8: does ``element`` affirmatively do what ``requirement`` (a
    ``hard_constraint``) forbids, in the same domain? Pure/deterministic —
    both ``requirement`` and ``element`` need only ``.requirement_type``/
    ``.domain``/``.statement`` and ``.domain``/``.decision``/``.rationale``
    respectively (works against ORM rows or any duck-typed stand-in)."""
    if requirement.requirement_type != RequirementType.HARD_CONSTRAINT.value:
        return False
    if element.domain != requirement.domain:
        return False
    forbidden = _forbidden_terms(requirement.statement)
    if not forbidden:
        return False
    combined_text = f"{element.decision} {element.rationale}"
    return any(_term_is_affirmed(combined_text, term) for term in forbidden)


# --------------------------------------------------------------------------
# scoring (design §10.3 score vector) + LES-023 coverage-honest uncertainty
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CriterionScoreSpec:
    """One :class:`~aos_core.models.FoundationScore` row's worth of computed values."""

    criterion: EvaluationCriterion
    raw_score: float
    weight: float
    confidence: float
    uncertainty_penalty: float
    rationale: str
    supporting_claim_ids: list[str]


_THINNESS_CLAIMS_PER_ELEMENT_CEILING = 3.0
_MAX_UNCERTAINTY_PENALTY = 0.5


def evidence_thinness(elements: Iterable) -> float:
    """LES-023 — coverage-honest thinness in ``[0, 1]``: ``0`` when elements are
    richly evidence-linked (mean claim_ids/element at or above
    :data:`_THINNESS_CLAIMS_PER_ELEMENT_CEILING`), ``1`` when elements carry no
    claim linkage at all. A sparse-evidence candidate therefore always reads
    strictly thinner (higher penalty, lower confidence) than a dense one with
    the same requirement coverage — never a naive average that could hide it."""
    elements = list(elements)
    if not elements:
        return 1.0
    mean_claims = sum(len(e.claim_ids or []) for e in elements) / len(elements)
    return max(0.0, min(1.0, 1.0 - (mean_claims / _THINNESS_CLAIMS_PER_ELEMENT_CEILING)))


def requirement_satisfaction(requirements: Iterable, elements: Iterable) -> tuple[list[str], list[str]]:
    """A requirement is *satisfied* if some element's ``requirement_ids`` names it."""
    addressed: set[str] = set()
    for element in elements:
        addressed.update(element.requirement_ids or [])
    requirements = list(requirements)
    satisfied = [r.id for r in requirements if r.id in addressed]
    unsatisfied = [r.id for r in requirements if r.id not in addressed]
    return satisfied, unsatisfied


def score_criteria(*, requirements: Iterable, elements: Iterable) -> list[CriterionScoreSpec]:
    """The deterministic subset of design §10.2's 20 criteria this slice can score
    from requirement-coverage/evidence-density alone (RFC-0020 Open Q3): the
    rest are intentionally not emitted rather than invented."""
    requirements = list(requirements)
    elements = list(elements)

    thinness = evidence_thinness(elements)
    confidence = 1.0 - thinness
    penalty = thinness * _MAX_UNCERTAINTY_PENALTY
    supporting_claim_ids = sorted({c for e in elements for c in (e.claim_ids or [])})

    satisfied, _unsatisfied = requirement_satisfaction(requirements, elements)
    coverage_fraction = len(satisfied) / len(requirements) if requirements else 0.0

    evidence_backed_elements = sum(1 for e in elements if e.claim_ids)
    evidence_fraction = evidence_backed_elements / len(elements) if elements else 0.0
    mean_claims_per_element = sum(len(e.claim_ids or []) for e in elements) / len(elements) if elements else 0.0

    return [
        CriterionScoreSpec(
            criterion=EvaluationCriterion.REQUIREMENT_COVERAGE,
            raw_score=coverage_fraction,
            weight=1.0,
            confidence=confidence,
            uncertainty_penalty=penalty,
            rationale=f"{len(satisfied)}/{len(requirements)} requirement(s) addressed by a candidate element.",
            supporting_claim_ids=supporting_claim_ids,
        ),
        CriterionScoreSpec(
            criterion=EvaluationCriterion.EVIDENCE_STRENGTH,
            raw_score=evidence_fraction,
            weight=0.7,
            confidence=confidence,
            uncertainty_penalty=penalty,
            rationale=f"{evidence_backed_elements}/{len(elements)} element(s) cite at least one supporting claim.",
            supporting_claim_ids=supporting_claim_ids,
        ),
        CriterionScoreSpec(
            criterion=EvaluationCriterion.RESIDUAL_UNCERTAINTY,
            raw_score=confidence,
            weight=0.5,
            confidence=confidence,
            uncertainty_penalty=penalty,
            rationale=f"Evidence thinness {thinness:.2f} (mean {mean_claims_per_element:.2f} claim(s)/element).",
            supporting_claim_ids=supporting_claim_ids,
        ),
    ]
