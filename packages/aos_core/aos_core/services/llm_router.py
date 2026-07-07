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
    OpenAICompatibleProvider,
    Provider,
)


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
        # A free hosted tier needs a key — without it the endpoint 401s.
        return bool(getattr(settings, "llm_free_api_key", ""))
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
