"""LLM tier router (AOS-LLM-EVAL-001, slice 2) — pick a reasoned-tier backend per
task, under a hard privacy guardrail.

The reasoned tier is a routed pool (ADR-0001): deterministic / local 7B (Tier 1) /
free hosted (Tier 2) / Claude (Tier 3). This router chooses which, given:

- a **task class** (e.g. ``code_review``, ``research``, ``final_judge``) whose
  preferred tier ordering lives in ``ROUTING_TABLE``, and
- a **data sensitivity** (``PRIVATE`` vs ``PUBLIC``).

**The privacy guardrail is non-negotiable and enforced here:** a ``PRIVATE`` task
is NEVER routed to Tier 2 (free hosted), because most free tiers train on
submitted data. Private work stays local or Claude. This is the single most
important line in the file — it keeps ArchetypeOS inside its local-first
constitution while still using free frontier models for public work.

A tier is only chosen if it is actually **available** (configured). The
deterministic tier is always available, so ``route`` always returns a provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..llm import (
    ClaudeCodeProvider,
    DeterministicProvider,
    InstrumentedProvider,
    OpenAICompatibleProvider,
    Provider,
)
from .llm_pool import build_free_pool, free_pool_provider


class Sensitivity(str, Enum):
    PRIVATE = "private"  # proprietary code/data — Tier 1 or Tier 3 only
    PUBLIC = "public"    # public repos / general reasoning — any tier


class Tier(str, Enum):
    DETERMINISTIC = "deterministic"
    LOCAL = "local"        # Tier 1 — on-node Ollama
    FREE_HOSTED = "free"   # Tier 2 — Groq/Cerebras/Gemini/... (non-private only)
    CLAUDE = "claude"      # Tier 3 — subscription


# Per-task-class preferred tier ordering (first available wins). Sensitivity is
# applied on top (PRIVATE strips FREE_HOSTED). Unknown task classes use DEFAULT.
DEFAULT_ORDER = [Tier.LOCAL, Tier.FREE_HOSTED, Tier.CLAUDE]
ROUTING_TABLE: dict[str, list[Tier]] = {
    "code_review": [Tier.LOCAL, Tier.FREE_HOSTED, Tier.CLAUDE],
    "distillation": [Tier.LOCAL, Tier.FREE_HOSTED, Tier.CLAUDE],
    "research": [Tier.FREE_HOSTED, Tier.CLAUDE],          # capability > privacy; public inputs
    "council_agent": [Tier.FREE_HOSTED, Tier.LOCAL, Tier.CLAUDE],
    "design": [Tier.FREE_HOSTED, Tier.CLAUDE],            # multimodal free models
    "final_judge": [Tier.CLAUDE],                          # highest stakes — always Claude
    "reconciliation": [Tier.FREE_HOSTED, Tier.LOCAL, Tier.CLAUDE],
}


@dataclass
class RouteResult:
    tier: Tier
    provider: Provider
    reason: str


def _available(tier: Tier, settings) -> bool:
    if tier is Tier.DETERMINISTIC:
        return True
    if tier is Tier.LOCAL:
        return bool(getattr(settings, "llm_base_url", "") and getattr(settings, "llm_model", ""))
    if tier is Tier.FREE_HOSTED:
        # A free hosted tier needs a key — from the env rotation pool (slice 3) or
        # the single configured provider. Without either, the endpoint 401s.
        return bool(build_free_pool()) or bool(getattr(settings, "llm_free_api_key", ""))
    if tier is Tier.CLAUDE:
        # Claude Code provider shells the local `claude` CLI; treat as available
        # when explicitly enabled (opt-in, since it spends subscription tokens).
        return bool(getattr(settings, "llm_claude_enabled", False))
    return False


def _provider_for(tier: Tier, settings) -> Provider:
    if tier is Tier.LOCAL:
        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=getattr(settings, "llm_api_key", ""),
        )
    if tier is Tier.FREE_HOSTED:
        # Prefer the rotation pool (429-resilient across providers); fall back to
        # the single configured free provider when no pool keys are in the env.
        pool = free_pool_provider()
        if pool is not None:
            return pool
        return OpenAICompatibleProvider(
            base_url=settings.llm_free_base_url,
            model=settings.llm_free_model,
            api_key=settings.llm_free_api_key,
        )
    if tier is Tier.CLAUDE:
        return ClaudeCodeProvider()
    return DeterministicProvider()


def route(task_class: str, sensitivity: Sensitivity, settings) -> RouteResult:
    """Return the backend for ``task_class`` at ``sensitivity``, privacy-safe.

    Always returns a provider — falls back to the deterministic tier if nothing
    else is configured.
    """
    order = list(ROUTING_TABLE.get(task_class, DEFAULT_ORDER))

    # THE GUARDRAIL: private data never reaches a free hosted tier.
    if sensitivity is Sensitivity.PRIVATE and Tier.FREE_HOSTED in order:
        order = [t for t in order if t is not Tier.FREE_HOSTED]

    for tier in order:
        if _available(tier, settings):
            return RouteResult(
                tier=tier,
                provider=_provider_for(tier, settings),
                reason=f"{task_class}/{sensitivity.value} -> {tier.value} (first available)",
            )

    return RouteResult(
        tier=Tier.DETERMINISTIC,
        provider=DeterministicProvider(),
        reason=f"{task_class}/{sensitivity.value} -> deterministic (no configured tier available)",
    )


def routed_provider(
    task_class: str,
    sensitivity: Sensitivity,
    settings,
    sink=None,
    *,
    context: str | None = None,
    agent: str | None = None,
    session: str | None = None,
) -> Provider:
    """Router-aware sibling of :func:`aos_core.llm.get_provider`.

    ``get_provider`` pins ``settings.llm_provider`` (a single backend); this picks
    the tier per ``task_class`` at ``sensitivity`` via :func:`route` — cheapest
    configured tier first, under the privacy guardrail — so a service opts into
    cheap-first routing by swapping ``get_provider`` for this. When a ledger
    ``sink`` is given the resolved provider is wrapped in
    :class:`~aos_core.llm.InstrumentedProvider` (AOS-USAGE-001), exactly like
    ``get_provider``; without a sink the bare provider is returned unchanged so
    hermetic / DB-less paths are untouched.
    """
    provider = route(task_class, sensitivity, settings).provider
    if sink is not None:
        return InstrumentedProvider(
            provider, sink, context=context, agent=agent, session=session
        )
    return provider
