"""Core tests for the LLM usage ledger (AOS-USAGE-001).

Hermetic (sqlite, no network, no `claude` binary): the provider subprocess/HTTP
boundaries are mocked. Covers:

- ``record_usage`` / ``summarize_usage`` aggregation + window filtering,
- ``InstrumentedProvider`` records exactly one event per ``generate()`` and
  returns the inner result unchanged; a deterministic provider records nothing,
- provider usage parsing (OpenAI-compatible ``usage`` and Claude JSON ``usage`` +
  ``total_cost_usd``) including the length-based estimate fallback.
"""

from __future__ import annotations

import json
import subprocess
import types
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import aos_core.llm as llm
from aos_core.database import Base
from aos_core.llm import (
    ClaudeCodeProvider,
    DeterministicProvider,
    InstrumentedProvider,
    OpenAICompatibleProvider,
    ProviderResult,
    get_provider,
)
from aos_core.models import UsageEvent
from aos_core.services.usage import (
    TIER_CLAUDE,
    TIER_FREE,
    TIER_LOCAL,
    derive_tier,
    record_provider_usage,
    record_usage,
    summarize_usage,
)


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'usage.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _settings(**over):
    base = dict(
        llm_free_base_url="https://api.groq.com/openai/v1",
        usage_cost_claude_input_per_mtok=3.0,
        usage_cost_claude_output_per_mtok=15.0,
        usage_cost_local_per_mtok=0.0,
        usage_cost_free_per_mtok=0.0,
    )
    base.update(over)
    return types.SimpleNamespace(**base)


# --------------------------------------------------------------------------- #
# tier derivation
# --------------------------------------------------------------------------- #

def test_derive_tier_maps_providers_and_config():
    s = _settings()
    assert derive_tier("deterministic") == "deterministic"
    assert derive_tier("claude_code") == TIER_CLAUDE
    assert derive_tier("rotating") == TIER_FREE
    # openai_compatible: free when base_url matches a configured free endpoint,
    # else the on-node local tier.
    assert derive_tier("openai_compatible", base_url="https://api.groq.com/openai/v1", settings=s) == TIER_FREE
    assert derive_tier("openai_compatible", base_url="http://localhost:11434/v1", settings=s) == TIER_LOCAL


# --------------------------------------------------------------------------- #
# record_usage / summarize_usage
# --------------------------------------------------------------------------- #

def test_record_and_summarize_aggregates_per_tier_and_model(db):
    record_usage(db, provider="claude_code", tier=TIER_CLAUDE, model="claude-sonnet-5",
                 input_tokens=100, output_tokens=20, cost_usd=0.5)
    record_usage(db, provider="claude_code", tier=TIER_CLAUDE, model="claude-sonnet-5",
                 input_tokens=200, output_tokens=30, cost_usd=1.0)
    record_usage(db, provider="openai_compatible", tier=TIER_LOCAL, model="qwen2.5-coder:7b",
                 input_tokens=50, output_tokens=10, cost_usd=0.0)

    summary = summarize_usage(db, window="7d")

    assert summary["totals"]["input_tokens"] == 350
    assert summary["totals"]["output_tokens"] == 60
    assert summary["totals"]["total_tokens"] == 410
    assert summary["totals"]["cost_usd"] == pytest.approx(1.5)
    assert summary["totals"]["events"] == 3

    assert summary["by_tier"][TIER_CLAUDE]["input_tokens"] == 300
    assert summary["by_tier"][TIER_CLAUDE]["cost_usd"] == pytest.approx(1.5)
    assert summary["by_tier"][TIER_LOCAL]["input_tokens"] == 50
    # free tier always present even with no events
    assert summary["by_tier"][TIER_FREE]["events"] == 0

    models = {(m["model"], m["tier"]): m for m in summary["by_model"]}
    assert models[("claude-sonnet-5", TIER_CLAUDE)]["total_tokens"] == 350
    assert models[("qwen2.5-coder:7b", TIER_LOCAL)]["total_tokens"] == 60
    # busiest model first
    assert summary["by_model"][0]["model"] == "claude-sonnet-5"


def test_summarize_window_excludes_older_events(db):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)
    record_usage(db, provider="claude_code", tier=TIER_CLAUDE, model="m",
                 input_tokens=1000, output_tokens=1000, cost_usd=9.0, ts=old)
    record_usage(db, provider="claude_code", tier=TIER_CLAUDE, model="m",
                 input_tokens=5, output_tokens=5, cost_usd=0.1, ts=now)

    week = summarize_usage(db, window="7d")
    assert week["totals"]["events"] == 1
    assert week["totals"]["total_tokens"] == 10

    month = summarize_usage(db, window="30d")
    assert month["totals"]["events"] == 2


def test_summarize_estimated_flag_propagates(db):
    record_usage(db, provider="claude_code", tier=TIER_CLAUDE, model="m",
                 input_tokens=10, output_tokens=10, cost_usd=0.1, estimated=True)
    summary = summarize_usage(db, window="today")
    assert summary["totals"]["estimated"] is True
    assert summary["by_tier"][TIER_CLAUDE]["estimated"] is True


def test_summarize_rejects_unknown_window(db):
    with pytest.raises(ValueError):
        summarize_usage(db, window="all-time")


def test_record_provider_usage_deterministic_records_nothing(db):
    event = record_provider_usage(
        db, provider="deterministic", model=None, input_tokens=None,
        output_tokens=None, cost_usd=None, estimated=False, settings=_settings(),
    )
    assert event is None
    assert db.query(UsageEvent).count() == 0


def test_record_provider_usage_estimates_claude_cost_when_unreported(db):
    # No provider-reported cost → rate-table estimate, flagged estimated.
    event = record_provider_usage(
        db, provider="claude_code", model="claude-sonnet-5",
        input_tokens=1_000_000, output_tokens=1_000_000, cost_usd=None,
        estimated=False, settings=_settings(),
    )
    assert event is not None
    assert event.tier == TIER_CLAUDE
    # 1M in * $3 + 1M out * $15 = $18
    assert event.cost_usd == pytest.approx(18.0)
    assert event.estimated is True


def test_record_provider_usage_uses_reported_cost(db):
    event = record_provider_usage(
        db, provider="claude_code", model="claude-sonnet-5",
        input_tokens=100, output_tokens=20, cost_usd=0.42,
        estimated=False, settings=_settings(),
    )
    assert event.cost_usd == pytest.approx(0.42)
    assert event.estimated is False


def test_record_provider_usage_local_is_free_and_not_estimated(db):
    event = record_provider_usage(
        db, provider="openai_compatible", model="qwen2.5-coder:7b",
        input_tokens=500, output_tokens=100, cost_usd=None, estimated=False,
        base_url="http://localhost:11434/v1", settings=_settings(),
    )
    assert event.tier == TIER_LOCAL
    assert event.cost_usd == pytest.approx(0.0)
    assert event.estimated is False


# --------------------------------------------------------------------------- #
# InstrumentedProvider
# --------------------------------------------------------------------------- #

class _FakeProvider:
    name = "openai_compatible"

    def __init__(self, result: ProviderResult):
        self._result = result
        self.calls = 0

    def generate(self, *, system: str, prompt: str, max_tokens: int = 1024, **kwargs) -> ProviderResult:
        self.calls += 1
        return self._result


def test_instrumented_provider_records_one_event_and_returns_inner_result():
    result = ProviderResult(
        text="hi", provider="openai_compatible", model="qwen", finish_reason="stop",
        input_tokens=12, output_tokens=3,
    )
    inner = _FakeProvider(result)
    recorded = []
    wrapped = InstrumentedProvider(inner, lambda **fields: recorded.append(fields))

    out = wrapped.generate(system="s", prompt="p")

    assert out is result  # inner result returned unchanged
    assert inner.calls == 1
    assert len(recorded) == 1
    assert recorded[0]["provider"] == "openai_compatible"
    assert recorded[0]["input_tokens"] == 12
    assert recorded[0]["output_tokens"] == 3


def test_instrumented_deterministic_records_nothing():
    recorded = []
    wrapped = InstrumentedProvider(DeterministicProvider(), lambda **fields: recorded.append(fields))
    out = wrapped.generate(system="", prompt="Persona: agent")
    assert out.provider == "deterministic"
    assert recorded == []


def test_instrumented_provider_swallows_sink_errors():
    result = ProviderResult(text="x", provider="openai_compatible", model="m", finish_reason="stop")

    def boom(**fields):
        raise RuntimeError("ledger down")

    wrapped = InstrumentedProvider(_FakeProvider(result), boom)
    # A ledger failure must never break the real call.
    assert wrapped.generate(system="s", prompt="p") is result


def test_make_ledger_sink_records_end_to_end(db, tmp_path):
    # Full loop: InstrumentedProvider -> make_ledger_sink -> record -> summarize.
    # Uses the same engine as the `db` fixture so the summary sees the row. This
    # guards the wrapper<->sink kwarg contract (context/agent/session forwarding).
    from aos_core.services.usage import make_ledger_sink

    factory = lambda: sessionmaker(bind=db.get_bind(), expire_on_commit=False)()  # noqa: E731
    result = ProviderResult(
        text="hi", provider="claude_code", model="claude-sonnet-5", finish_reason="stop",
        input_tokens=3616, output_tokens=14, cost_usd=0.1823,
    )
    sink = make_ledger_sink(factory, _settings(), context="council")
    # The recorded tier derives from result.provider ("claude_code"), not the
    # inner object's name — so this records a claude-tier event.
    wrapped = InstrumentedProvider(_FakeProvider(result), sink)
    out = wrapped.generate(system="s", prompt="p")
    assert out is result

    summary = summarize_usage(db, window="today")
    assert summary["totals"]["events"] == 1
    assert summary["totals"]["cost_usd"] == pytest.approx(0.1823)
    # context default from the factory is applied (wrapper forwarded None).
    event = db.query(UsageEvent).one()
    assert event.context == "council"
    assert event.tier == TIER_CLAUDE


def test_get_provider_bare_by_default_wrapped_with_sink():
    s = _settings(llm_provider="deterministic")
    bare = get_provider(s)
    assert isinstance(bare, DeterministicProvider)
    wrapped = get_provider(s, sink=lambda **f: None)
    assert isinstance(wrapped, InstrumentedProvider)


# --------------------------------------------------------------------------- #
# provider usage parsing
# --------------------------------------------------------------------------- #

class _FakeHTTPResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_openai_compatible_parses_usage(monkeypatch):
    payload = {
        "model": "qwen2.5-coder:7b",
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 42, "completion_tokens": 7},
    }
    monkeypatch.setattr(
        llm.urllib.request, "urlopen",
        lambda *a, **k: _FakeHTTPResponse(json.dumps(payload)),
    )
    provider = OpenAICompatibleProvider(base_url="http://localhost:11434/v1", model="qwen2.5-coder:7b")
    result = provider.generate(system="s", prompt="p")
    assert result.input_tokens == 42
    assert result.output_tokens == 7
    assert result.usage_estimated is False


def test_openai_compatible_missing_usage_leaves_none(monkeypatch):
    payload = {"model": "m", "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
    monkeypatch.setattr(
        llm.urllib.request, "urlopen",
        lambda *a, **k: _FakeHTTPResponse(json.dumps(payload)),
    )
    provider = OpenAICompatibleProvider(base_url="http://localhost:11434/v1", model="m")
    result = provider.generate(system="s", prompt="p")
    assert result.input_tokens is None
    assert result.output_tokens is None


def _fake_completed(stdout: str):
    return subprocess.CompletedProcess(args=["claude"], returncode=0, stdout=stdout, stderr="")


def test_claude_provider_parses_real_usage(monkeypatch):
    envelope = {
        "type": "result",
        "result": "Hi there",
        "total_cost_usd": 0.1823,
        "usage": {"input_tokens": 3616, "output_tokens": 14},
    }
    monkeypatch.setattr(llm.subprocess, "run", lambda *a, **k: _fake_completed(json.dumps(envelope)))
    result = ClaudeCodeProvider().generate(system="sys", prompt="hello")
    assert result.text == "Hi there"
    assert result.input_tokens == 3616
    assert result.output_tokens == 14
    assert result.cost_usd == pytest.approx(0.1823)
    assert result.usage_estimated is False


def test_claude_provider_estimates_when_usage_absent(monkeypatch):
    # An envelope with no `usage` → length-based estimate, flagged estimated.
    envelope = {"type": "result", "result": "some response text here"}
    monkeypatch.setattr(llm.subprocess, "run", lambda *a, **k: _fake_completed(json.dumps(envelope)))
    result = ClaudeCodeProvider().generate(system="sys", prompt="a longer prompt to estimate from")
    assert result.usage_estimated is True
    assert result.input_tokens is not None and result.input_tokens > 0
    assert result.output_tokens is not None and result.output_tokens > 0
    assert result.cost_usd is None  # no reported cost; the service applies the rate estimate
