"""Hermetic tests for the adversarial verifier (AOS-LLM-ROUTE-COV, slice 3).

All providers are fakes — no network, no claude binary, no Ollama. The fake
Provider tracks call counts so we can assert the verifier was or was not
invoked, and that escalation happened exactly when expected.
"""
from __future__ import annotations

import types
from dataclasses import dataclass, field

from aos_core.llm import ProviderResult
from aos_core.services.llm_router import RouteResult, Sensitivity, Tier
from aos_core.services.verifier import VerifiedResult, verified_generate


# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------

def _make_result(text: str, provider: str = "fake", model: str = "fake-model") -> ProviderResult:
    return ProviderResult(
        text=text,
        provider=provider,
        model=model,
        finish_reason="stop",
    )


@dataclass
class FakeProvider:
    """Minimal Provider fake that returns canned text and counts calls."""

    responses: list[str] = field(default_factory=list)
    name: str = "fake"
    _call_count: int = field(default=0, init=False)
    _call_index: int = field(default=0, init=False)

    def generate(self, *, system: str, prompt: str, max_tokens: int = 1024) -> ProviderResult:
        self._call_count += 1
        if self._call_index < len(self.responses):
            text = self.responses[self._call_index]
            self._call_index += 1
        else:
            text = self.responses[-1] if self.responses else ""
        return _make_result(text, provider=self.name)

    @property
    def call_count(self) -> int:
        return self._call_count


def _settings(**kwargs) -> types.SimpleNamespace:
    """Minimal settings namespace for the verifier tests."""
    return types.SimpleNamespace(**kwargs)


# ---------------------------------------------------------------------------
# Helpers to build shared monkeypatches
# ---------------------------------------------------------------------------

def _patch_route(monkeypatch, tier: Tier, provider: FakeProvider) -> None:
    """Make verifier.route() return a RouteResult with the given tier+provider."""
    def _fake_route(task_class, sensitivity, settings):
        return RouteResult(tier=tier, provider=provider, reason="test")
    monkeypatch.setattr("aos_core.services.verifier.route", _fake_route)


def _patch_claude(
    monkeypatch,
    *,
    available: bool,
    claude_provider: FakeProvider | None = None,
) -> None:
    """Patch _available and _provider_for so Claude is controlled by fakes."""
    def _fake_available(t, settings):
        if t is Tier.CLAUDE:
            return available
        return False

    monkeypatch.setattr("aos_core.services.verifier._available", _fake_available)

    if claude_provider is not None:
        def _fake_provider_for(t, settings):
            if t is Tier.CLAUDE:
                return claude_provider
            raise ValueError(f"unexpected tier in test: {t}")
        monkeypatch.setattr("aos_core.services.verifier._provider_for", _fake_provider_for)


# ---------------------------------------------------------------------------
# Test 1: cheap tier + verifier says VALID → cheap result returned
# ---------------------------------------------------------------------------

def test_cheap_tier_valid_verdict_returns_cheap_result(monkeypatch):
    """FREE_HOSTED produces an answer; Claude verifier says VALID.

    Expected: the cheap result is returned, verified=True, escalated=False,
    verdict="valid". The cheap producer was called exactly once; Claude was
    called exactly once (for the verify pass only).
    """
    cheap_provider = FakeProvider(responses=["The cheap answer"], name="free_hosted")
    # Claude responses: first call is the verifier verdict, no escalation.
    claude_provider = FakeProvider(responses=["VALID"], name="claude_code")

    settings = _settings(llm_claude_enabled=True)

    _patch_route(monkeypatch, Tier.FREE_HOSTED, cheap_provider)
    _patch_claude(monkeypatch, available=True, claude_provider=claude_provider)

    vr: VerifiedResult = verified_generate(
        task_class="research",
        sensitivity=Sensitivity.PUBLIC,
        settings=settings,
        system="You are a research assistant.",
        prompt="What is 2+2?",
    )

    assert vr.result.text == "The cheap answer"
    assert vr.tier is Tier.FREE_HOSTED
    assert vr.verified is True
    assert vr.escalated is False
    assert vr.verdict == "valid"
    # cheap producer called once; Claude called once (verifier only)
    assert cheap_provider.call_count == 1
    assert claude_provider.call_count == 1


# ---------------------------------------------------------------------------
# Test 2: cheap tier + verifier says REFUTED → escalates to Claude
# ---------------------------------------------------------------------------

def test_cheap_tier_refuted_escalates_to_claude(monkeypatch):
    """FREE_HOSTED produces an answer; Claude verifier says REFUTED.

    Expected: the Claude re-production is returned, tier=CLAUDE, verified=True,
    escalated=True, verdict="refuted". Claude was called exactly twice: once
    for the verifier pass, once for the escalated re-production.
    """
    cheap_provider = FakeProvider(responses=["Wrong answer"], name="free_hosted")
    # Claude: first call is verifier verdict ("REFUTED: ..."), second is re-production.
    claude_provider = FakeProvider(
        responses=["REFUTED: the answer is factually wrong", "The correct Claude answer"],
        name="claude_code",
    )

    settings = _settings(llm_claude_enabled=True)

    _patch_route(monkeypatch, Tier.FREE_HOSTED, cheap_provider)
    _patch_claude(monkeypatch, available=True, claude_provider=claude_provider)

    vr: VerifiedResult = verified_generate(
        task_class="research",
        sensitivity=Sensitivity.PUBLIC,
        settings=settings,
        system="You are a research assistant.",
        prompt="What is the capital of France?",
    )

    assert vr.result.text == "The correct Claude answer"
    assert vr.tier is Tier.CLAUDE
    assert vr.verified is True
    assert vr.escalated is True
    assert vr.verdict == "refuted"
    assert cheap_provider.call_count == 1
    # verifier call + escalation call = 2
    assert claude_provider.call_count == 2


# ---------------------------------------------------------------------------
# Test 3: route returns CLAUDE tier directly → no verifier call
# ---------------------------------------------------------------------------

def test_claude_tier_produced_directly_skips_verifier(monkeypatch):
    """When route() returns Tier.CLAUDE, the verifier must NOT be invoked.

    Expected: verified=False, verdict=None, escalated=False. The claude_provider
    used for production is called once; the verifier path is never reached.
    """
    # The producer IS Claude (e.g. final_judge task).
    claude_producer = FakeProvider(responses=["Top-tier answer"], name="claude_code")
    # We give a separate fake to _provider_for to detect if the verifier path runs.
    verifier_spy = FakeProvider(responses=["VALID"], name="claude_verifier_spy")

    settings = _settings(llm_claude_enabled=True)

    _patch_route(monkeypatch, Tier.CLAUDE, claude_producer)
    # Even if Claude is "available", the verifier should NOT be called because
    # tier is already CLAUDE — the short-circuit fires before _provider_for.
    _patch_claude(monkeypatch, available=True, claude_provider=verifier_spy)

    vr: VerifiedResult = verified_generate(
        task_class="final_judge",
        sensitivity=Sensitivity.PUBLIC,
        settings=settings,
        system="You are a final judge.",
        prompt="Assess this.",
    )

    assert vr.result.text == "Top-tier answer"
    assert vr.tier is Tier.CLAUDE
    assert vr.verified is False
    assert vr.escalated is False
    assert vr.verdict is None
    assert claude_producer.call_count == 1
    # The verifier spy must NOT have been called.
    assert verifier_spy.call_count == 0


# ---------------------------------------------------------------------------
# Test 4: Claude NOT available → no verifier, cheap result returned as-is
# ---------------------------------------------------------------------------

def test_claude_unavailable_returns_cheap_result_unverified(monkeypatch):
    """When _available(CLAUDE) is False, skip the adversarial pass entirely.

    Expected: the cheap result is returned, verified=False, verdict=None.
    """
    cheap_provider = FakeProvider(responses=["Local model answer"], name="local")

    settings = _settings(llm_claude_enabled=False)

    _patch_route(monkeypatch, Tier.LOCAL, cheap_provider)
    # Claude is NOT available; _provider_for should never be called.
    _patch_claude(monkeypatch, available=False, claude_provider=None)

    vr: VerifiedResult = verified_generate(
        task_class="code_review",
        sensitivity=Sensitivity.PRIVATE,
        settings=settings,
        system="You are a code reviewer.",
        prompt="Review this function.",
    )

    assert vr.result.text == "Local model answer"
    assert vr.tier is Tier.LOCAL
    assert vr.verified is False
    assert vr.escalated is False
    assert vr.verdict is None
    assert cheap_provider.call_count == 1


# ---------------------------------------------------------------------------
# Test 5: DETERMINISTIC tier produced → no verifier call
# ---------------------------------------------------------------------------

def test_deterministic_tier_skips_verifier(monkeypatch):
    """Deterministic output has no reasoning to check; verifier must be skipped.

    Expected: verified=False, verdict=None, escalated=False.
    """
    det_provider = FakeProvider(
        responses=['{"summary": "deterministic", "status": "Complete"}'],
        name="deterministic",
    )
    verifier_spy = FakeProvider(responses=["VALID"], name="claude_verifier_spy")

    settings = _settings(llm_claude_enabled=True)

    _patch_route(monkeypatch, Tier.DETERMINISTIC, det_provider)
    _patch_claude(monkeypatch, available=True, claude_provider=verifier_spy)

    vr: VerifiedResult = verified_generate(
        task_class="code_review",
        sensitivity=Sensitivity.PUBLIC,
        settings=settings,
        system="Assess the diff.",
        prompt="diff goes here",
    )

    assert vr.tier is Tier.DETERMINISTIC
    assert vr.verified is False
    assert vr.escalated is False
    assert vr.verdict is None
    assert det_provider.call_count == 1
    assert verifier_spy.call_count == 0


# ---------------------------------------------------------------------------
# Test 6: sink is invoked for produce and verify calls when provided
# ---------------------------------------------------------------------------

def test_sink_invoked_for_produce_and_verify_calls(monkeypatch):
    """When a sink is supplied, the produce and verify calls each record a usage event.

    Expected: with a FREE_HOSTED produce tier and Claude saying VALID, the sink
    is called exactly twice — once for the produce call and once for the verify call.
    """
    cheap_provider = FakeProvider(responses=["The cheap answer"], name="free_hosted")
    claude_provider = FakeProvider(responses=["VALID"], name="claude_code")

    settings = _settings(llm_claude_enabled=True)

    _patch_route(monkeypatch, Tier.FREE_HOSTED, cheap_provider)
    _patch_claude(monkeypatch, available=True, claude_provider=claude_provider)

    sink_calls: list[dict] = []

    def _sink(**kwargs):
        sink_calls.append(kwargs)

    vr: VerifiedResult = verified_generate(
        task_class="distillation",
        sensitivity=Sensitivity.PUBLIC,
        settings=settings,
        system="You are a distillation agent.",
        prompt="Summarise this repo.",
        sink=_sink,
    )

    assert vr.result.text == "The cheap answer"
    assert vr.verdict == "valid"
    # Produce call recorded, verify call recorded — two total events.
    assert len(sink_calls) == 2
    # Both events carry the task context label.
    assert all(call["context"] == "distillation" for call in sink_calls)
    # Producer and verifier are distinguishable by their agent labels.
    agents = {call["agent"] for call in sink_calls}
    assert agents == {"producer", "verifier"}
