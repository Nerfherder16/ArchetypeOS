"""Tests for the free-API rotation pool (AOS-LLM-EVAL-001, slice 3).

Hermetic: fake providers stand in for the LLM endpoints. Verifies fall-through on
failure, round-robin load spreading, all-failed behavior, and env-driven pool
assembly.
"""
from __future__ import annotations

import types

from aos_core.services.llm_pool import (
    RotatingProvider,
    build_free_pool,
    free_pool_provider,
)


class _Ok:
    name = "ok"

    def __init__(self, tag):
        self.tag = tag
        self.calls = 0

    def generate(self, **_):
        self.calls += 1
        return types.SimpleNamespace(text=self.tag, provider="ok", model=self.tag, finish_reason="stop")


class _Boom:
    name = "boom"

    def __init__(self):
        self.calls = 0

    def generate(self, **_):
        self.calls += 1
        raise RuntimeError("HTTP 429 rate limited")


def test_returns_first_success():
    a, b = _Ok("A"), _Ok("B")
    r = RotatingProvider([a, b], labels=["a", "b"])
    assert r.generate(system="", prompt="p").text == "A"
    assert a.calls == 1 and b.calls == 0


def test_falls_through_failure_to_next_member():
    boom, ok = _Boom(), _Ok("B")
    r = RotatingProvider([boom, ok], labels=["boom", "ok"])
    out = r.generate(system="", prompt="p")
    assert out.text == "B"
    assert boom.calls == 1 and ok.calls == 1  # tried boom (429), fell through to ok


def test_raises_only_when_all_fail():
    r = RotatingProvider([_Boom(), _Boom()], labels=["x", "y"])
    try:
        r.generate(system="", prompt="p")
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "all rotation-pool providers failed" in str(exc)
        assert "x:" in str(exc) and "y:" in str(exc)


def test_round_robin_spreads_start_across_calls():
    a, b = _Ok("A"), _Ok("B")
    r = RotatingProvider([a, b], labels=["a", "b"])
    first = r.generate(system="", prompt="p").text   # starts at 0 -> A
    second = r.generate(system="", prompt="p").text  # cursor advanced -> starts at 1 -> B
    assert first == "A" and second == "B"
    assert a.calls == 1 and b.calls == 1


def test_empty_pool_raises():
    r = RotatingProvider([])
    try:
        r.generate(system="", prompt="p")
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "empty" in str(exc)


def test_build_free_pool_includes_only_members_with_keys():
    env = {"GROQ_API_KEY": "gsk_x", "MISTRAL_API_KEY": "m_x"}  # cerebras/gemini absent
    names = [name for name, _ in build_free_pool(env)]
    assert "groq" in names and "mistral" in names
    assert "cerebras" not in names and "gemini" not in names


def test_free_pool_provider_none_when_no_keys():
    assert free_pool_provider({}) is None


def test_free_pool_provider_rotates_when_keys_present():
    pool = free_pool_provider({"GROQ_API_KEY": "gsk_x", "CEREBRAS_API_KEY": "c_x"})
    assert isinstance(pool, RotatingProvider)
    assert len(pool) == 2
