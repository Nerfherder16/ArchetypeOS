"""Multi-phase research plans (AOS-RESEARCH-003, Finding 15).

The research loop's first phase is *planning*: before any source is fetched, the
investigation records what it will look for and how it will judge what it finds.
This module builds that plan deterministically from a question and persists it as
a :class:`ResearchPlan`, so the plan exists (and is auditable) prior to any fetch
— acceptance criterion 1. The run executor that consumes a plan (search → fetch →
verify → synthesize) is a later slice; this module only plans.

Deterministic and hermetic: same question → identical plan (no wall-clock, no
randomness), mirroring the research engine's deterministic floor.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import ResearchPlan
from .llm_router import Sensitivity

# The source-type ladder a general investigation should try to cover, highest
# authority first. Mirrors the research engine's SOURCE_TIERS keys so a plan's
# required types line up with what the ranker classifies sources into.
_DEFAULT_SOURCE_TYPES: list[str] = [
    "official-docs",
    "standard-rfc",
    "reference-implementation",
    "benchmark-paper",
]

# A fixed verification checklist applied to gathered sources. Deterministic and
# question-independent so every plan is judged by the same standard.
_VERIFICATION_STEPS: list[str] = [
    "corroborate each finding across at least two accepted sources",
    "check source freshness and flag stale evidence",
    "surface conflicting claims rather than flattening them",
    "reject sources that do not address the question, with a reason",
]


def _search_queries(question: str) -> list[str]:
    """Derive a deterministic set of search queries seeded by the question.

    The question itself is always the first query; the rest are fixed analytical
    angles appended to it (best practices, alternatives, risks/limitations). Order
    is stable and de-duplicated.
    """
    base = " ".join(question.split()).strip()
    if not base:
        return []
    angles = ["", " best practices", " alternatives", " risks and limitations"]
    queries: list[str] = []
    for angle in angles:
        query = f"{base}{angle}".strip()
        if query not in queries:
            queries.append(query)
    return queries


def build_plan_spec(question: str, sensitivity: Sensitivity) -> dict:
    """Build the plan facets for a question, deterministically. Pure (no I/O)."""
    return {
        "required_source_types": list(_DEFAULT_SOURCE_TYPES),
        "search_queries": _search_queries(question),
        "verification_steps": list(_VERIFICATION_STEPS),
        "synthesis_policy": {
            "cite_sources": True,
            "record_open_questions": True,
            "min_confidence": 0.5,
            "top_n": 3,
            # Sensitivity is echoed into the policy so the synthesizer can honor it
            # (e.g. keep private investigations off public-egress sources).
            "sensitivity": sensitivity.value,
        },
    }


def create_research_plan(
    db: Session, *, project_id: str, question: str, sensitivity: Sensitivity = Sensitivity.PUBLIC
) -> ResearchPlan:
    """Build and persist a research plan (status ``planned``) before any fetch."""
    spec = build_plan_spec(question, sensitivity)
    plan = ResearchPlan(
        project_id=project_id,
        question=question,
        sensitivity=sensitivity.value,
        plan_status="planned",
        required_source_types=spec["required_source_types"],
        search_queries=spec["search_queries"],
        verification_steps=spec["verification_steps"],
        synthesis_policy=spec["synthesis_policy"],
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
