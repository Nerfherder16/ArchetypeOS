"""Tests for the LLM tier router (AOS-LLM-EVAL-001, slice 2).

The load-bearing assertion is the privacy guardrail: a PRIVATE task must NEVER be
routed to the free hosted tier, even when it is first in the table and fully
configured. Hermetic — no provider is invoked, only selected.
"""
from __future__ import annotations

import types

from aos_core.llm import (
    ClaudeCodeProvider,
    DeterministicProvider,
    OpenAICompatibleProvider,
)
from aos_core.services.llm_router import (
    Sensitivity,
    Tier,
    route,
)


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
    assert r.tier is Tier.LOCAL  # DEFAULT_ORDER starts LOCAL, which is configured
