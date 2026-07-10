"""Tests for the LLM tier router (AOS-LLM-EVAL-001, slice 2).

The load-bearing assertion is the privacy guardrail: a PRIVATE task must NEVER be
routed to the free hosted tier, even when it is first in the table and fully
configured. Hermetic — no provider is invoked, only selected.
"""
from __future__ import annotations

import types

import pytest

from aos_core.llm import (
    ClaudeCodeProvider,
    DeterministicProvider,
    InstrumentedProvider,
    OpenAICompatibleProvider,
)
from aos_core.services.llm_router import (
    Sensitivity,
    Tier,
    route,
    routed_provider,
)


@pytest.fixture(autouse=True)
def _no_pool_env(monkeypatch):
    # The router consults the env rotation pool (slice 3); clear those keys so
    # these tests exercise the single-provider path deterministically.
    for key in ("GROQ_API_KEY", "CEREBRAS_API_KEY", "GEMINI_API_KEY", "MISTRAL_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def _settings(**over):
    base = dict(
        llm_base_url="http://localhost:11434/v1",
        llm_model="qwen2.5-coder:7b",
        llm_api_key="",
        llm_free_base_url="https://api.groq.com/openai/v1",
        llm_free_model="llama-3.3-70b-versatile",
        llm_free_api_key="gsk_test",
        llm_claude_enabled=False,
    )
    base.update(over)
    return types.SimpleNamespace(**base)


def test_private_task_never_routes_to_free_hosted():
    # code_review prefers LOCAL first anyway; force LOCAL unavailable so the only
    # way to reach a model is FREE — and confirm PRIVATE still refuses it.
    s = _settings(llm_base_url="", llm_model="")  # local unavailable
    r = route("code_review", Sensitivity.PRIVATE, s)
    assert r.tier is not Tier.FREE_HOSTED
    # With local off, Claude off, and free forbidden → deterministic floor.
    assert r.tier is Tier.DETERMINISTIC
    assert isinstance(r.provider, DeterministicProvider)


def test_public_task_uses_free_when_local_unavailable():
    s = _settings(llm_base_url="", llm_model="")  # local unavailable, free key present
    r = route("code_review", Sensitivity.PUBLIC, s)
    assert r.tier is Tier.FREE_HOSTED
    assert isinstance(r.provider, OpenAICompatibleProvider)
    assert r.provider.base_url == "https://api.groq.com/openai/v1"


def test_private_code_review_prefers_local():
    s = _settings()  # local configured
    r = route("code_review", Sensitivity.PRIVATE, s)
    assert r.tier is Tier.LOCAL
    assert isinstance(r.provider, OpenAICompatibleProvider)
    assert r.provider.model == "qwen2.5-coder:7b"


def test_final_judge_always_claude_when_enabled():
    r = route("final_judge", Sensitivity.PUBLIC, _settings(llm_claude_enabled=True))
    assert r.tier is Tier.CLAUDE
    assert isinstance(r.provider, ClaudeCodeProvider)


def test_final_judge_falls_back_to_deterministic_when_claude_disabled():
    # final_judge routes ONLY to Claude; with it disabled there is no other tier.
    r = route("final_judge", Sensitivity.PUBLIC, _settings(llm_claude_enabled=False))
    assert r.tier is Tier.DETERMINISTIC


def test_research_prefers_free_hosted_for_public():
    r = route("research", Sensitivity.PUBLIC, _settings())
    assert r.tier is Tier.FREE_HOSTED


def test_research_private_skips_free_and_falls_through():
    # research table is [FREE, CLAUDE]; PRIVATE strips FREE, Claude disabled →
    # deterministic. (A private research task should not silently hit a free API.)
    r = route("research", Sensitivity.PRIVATE, _settings())
    assert r.tier is not Tier.FREE_HOSTED
    assert r.tier is Tier.DETERMINISTIC


def test_free_hosted_unavailable_without_key():
    s = _settings(llm_base_url="", llm_model="", llm_free_api_key="")  # nothing configured
    r = route("code_review", Sensitivity.PUBLIC, s)
    assert r.tier is Tier.DETERMINISTIC


def test_unknown_task_uses_default_order():
    r = route("some_new_task", Sensitivity.PUBLIC, _settings())
    # DEFAULT_ORDER now starts FREE_HOSTED (best-results tuning: capable 70B free
    # before local 7B); the free key is configured in _settings so it wins.
    assert r.tier is Tier.FREE_HOSTED


# --- routed_provider: router-aware sibling of get_provider (AOS-LLM-ROUTE-COV) ---


def test_routed_provider_returns_tier_provider_bare_without_sink():
    # distillation table = [LOCAL, FREE, CLAUDE]; with LOCAL configured it wins →
    # the local OpenAI-compatible provider, unwrapped (no sink).
    p = routed_provider("distillation", Sensitivity.PRIVATE, _settings())
    assert isinstance(p, OpenAICompatibleProvider)


def test_routed_provider_wraps_in_instrumented_when_sink_given():
    calls: list = []
    p = routed_provider(
        "distillation", Sensitivity.PRIVATE, _settings(), sink=lambda **kw: calls.append(kw)
    )
    assert isinstance(p, InstrumentedProvider)
    assert isinstance(p.inner, OpenAICompatibleProvider)


def test_routed_provider_honors_privacy_guardrail():
    # research table = [FREE, CLAUDE]; PRIVATE strips FREE, CLAUDE disabled →
    # nothing configured survives → deterministic floor (never the free tier).
    p = routed_provider("research", Sensitivity.PRIVATE, _settings(llm_claude_enabled=False))
    assert isinstance(p, DeterministicProvider)
