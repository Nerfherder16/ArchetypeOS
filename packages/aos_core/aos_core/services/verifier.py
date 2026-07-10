"""Adversarial verifier for cheap-tier LLM output (AOS-LLM-ROUTE-COV, slice 3).

When a task is produced by a tier BELOW Claude (LOCAL or FREE_HOSTED), an
independent Claude instance is asked to REFUTE the candidate answer. If it
finds a factual error, omission, or fabrication, the task is re-produced on
Claude. This keeps cheap-first routing honest without skipping the savings.

Flow (escalate-on-refute):
  1. Route and produce on cheapest available tier.
  2. If the tier is already Claude or DETERMINISTIC, or Claude is unavailable,
     return the result as-is (nothing to verify against, or no verifier).
  3. Otherwise ask Claude to try to refute the candidate. A response that
     starts with "REFUTED" (case-insensitive after stripping) means refuted.
  4. Valid verdict  → return the cheap result, marked verified.
  5. Refuted verdict → re-produce on Claude, return that result, marked escalated.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..llm import InstrumentedProvider, Provider, ProviderResult
from .llm_router import Tier, _available, _provider_for, route

# ---------------------------------------------------------------------------
# Adversarial reviewer system prompt
# ---------------------------------------------------------------------------

_REFUTE_SYSTEM = (
    "You are an adversarial fact-checker. You will be shown a task (system "
    "prompt + user prompt) and a candidate answer produced by a language model. "
    "Your job is to try HARD to find any factual error, omission of critical "
    "information, fabrication, or hallucination in the candidate answer. "
    "Be skeptical and thorough. "
    "If you find even one clear problem, respond with exactly: "
    "REFUTED: <one-sentence reason>. "
    "If the candidate answer is factually sound and complete, respond with "
    "exactly: VALID"
)


def _verify_prompt(system: str, prompt: str, candidate: str) -> str:
    """Format the original task and candidate for the adversarial reviewer."""
    return (
        "=== ORIGINAL TASK ===\n"
        f"System: {system}\n\n"
        f"User: {prompt}\n\n"
        "=== CANDIDATE ANSWER ===\n"
        f"{candidate}\n\n"
        "Review the candidate answer against the original task. "
        "Reply REFUTED: <reason> or VALID."
    )


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

@dataclass
class VerifiedResult:
    """Outcome of a verified generation.

    ``result``    -- the answer to use (cheap result, or escalated Claude result).
    ``tier``      -- the tier that produced ``result``.
    ``verified``  -- True when an adversarial pass was actually run.
    ``escalated`` -- True when the cheap answer was refuted and Claude re-produced.
    ``verdict``   -- "valid" | "refuted" | None (None when not verified).
    """

    result: ProviderResult
    tier: Tier
    verified: bool
    escalated: bool
    verdict: str | None


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def verified_generate(
    *,
    task_class: str,
    sensitivity,
    settings,
    system: str,
    prompt: str,
    sink=None,
    max_tokens: int = 1024,
) -> VerifiedResult:
    """Route, produce, and optionally adversarially verify the output.

    When ``sink`` is not None, each provider call (produce, verify, escalate)
    is wrapped in :class:`~aos_core.llm.InstrumentedProvider` so a
    ``UsageEvent`` is recorded in the ledger for every real model call.
    When ``sink`` is None, bare providers are used and no ledger writes occur.
    """
    r = route(task_class, sensitivity, settings)
    produce_provider: Provider = (
        InstrumentedProvider(r.provider, sink, context=task_class, agent="producer")
        if sink is not None
        else r.provider
    )
    produced: ProviderResult = produce_provider.generate(
        system=system, prompt=prompt, max_tokens=max_tokens
    )

    # Already top-tier or deterministic — nothing higher to verify against.
    # Also skip when Claude is unavailable (no verifier to call).
    if r.tier in (Tier.CLAUDE, Tier.DETERMINISTIC) or not _available(Tier.CLAUDE, settings):
        return VerifiedResult(
            result=produced,
            tier=r.tier,
            verified=False,
            escalated=False,
            verdict=None,
        )

    # --- adversarial pass ---------------------------------------------------
    _claude_raw: Provider = _provider_for(Tier.CLAUDE, settings)
    claude: Provider = (
        InstrumentedProvider(_claude_raw, sink, context=task_class, agent="verifier")
        if sink is not None
        else _claude_raw
    )
    verdict_result = claude.generate(
        system=_REFUTE_SYSTEM,
        prompt=_verify_prompt(system, prompt, produced.text),
        max_tokens=300,
    )

    # A candidate is REFUTED iff the verifier's text, stripped and upper-cased,
    # starts with "REFUTED". Any other response (including "VALID") is treated
    # as valid — the verifier must be unambiguous to trigger escalation.
    verdict_text = verdict_result.text.strip().upper()
    if verdict_text.startswith("REFUTED"):
        # Re-produce on Claude using the original system + prompt.
        escalated_result = claude.generate(
            system=system, prompt=prompt, max_tokens=max_tokens
        )
        return VerifiedResult(
            result=escalated_result,
            tier=Tier.CLAUDE,
            verified=True,
            escalated=True,
            verdict="refuted",
        )

    return VerifiedResult(
        result=produced,
        tier=r.tier,
        verified=True,
        escalated=False,
        verdict="valid",
    )
