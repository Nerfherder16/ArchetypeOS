"""API tests for the usage-ledger summary (AOS-USAGE-001).

``GET /usage/summary?window=today|7d|30d``. Events are seeded directly on the same
sqlite file the ``client`` fixture uses (the ledger is normally written centrally
by the InstrumentedProvider wrapper; here we seed to assert the summary shape and
window handling). No provider is invoked.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.services.usage import TIER_CLAUDE, TIER_FREE, TIER_LOCAL, record_usage


def _same_file_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def _seed(tmp_path):
    session = _same_file_session(tmp_path)
    now = datetime.now(timezone.utc)
    try:
        record_usage(session, provider="claude_code", tier=TIER_CLAUDE, model="claude-sonnet-5",
                     input_tokens=100, output_tokens=20, cost_usd=0.5, ts=now)
        record_usage(session, provider="openai_compatible", tier=TIER_LOCAL, model="qwen2.5-coder:7b",
                     input_tokens=40, output_tokens=8, cost_usd=0.0, ts=now)
        # An event 10 days old (outside the 7d window, inside 30d).
        record_usage(session, provider="claude_code", tier=TIER_CLAUDE, model="claude-sonnet-5",
                     input_tokens=999, output_tokens=999, cost_usd=9.0, ts=now - timedelta(days=10))
    finally:
        session.close()


def test_usage_summary_shape(client, tmp_path):
    _seed(tmp_path)
    resp = client.get("/usage/summary?window=7d")
    assert resp.status_code == 200
    body = resp.json()

    assert body["window"] == "7d"
    assert "since" in body
    # 7d window excludes the 10-day-old event → 2 events.
    assert body["totals"]["events"] == 2
    assert body["totals"]["input_tokens"] == 140
    assert body["totals"]["output_tokens"] == 28
    assert body["totals"]["total_tokens"] == 168
    assert body["totals"]["cost_usd"] == 0.5

    # per-tier: all three reported tiers present (free zeroed).
    for tier in (TIER_CLAUDE, TIER_LOCAL, TIER_FREE):
        assert tier in body["by_tier"]
    assert body["by_tier"][TIER_CLAUDE]["input_tokens"] == 100
    assert body["by_tier"][TIER_LOCAL]["input_tokens"] == 40
    assert body["by_tier"][TIER_FREE]["events"] == 0

    models = {(m["model"], m["tier"]) for m in body["by_model"]}
    assert ("claude-sonnet-5", TIER_CLAUDE) in models
    assert ("qwen2.5-coder:7b", TIER_LOCAL) in models


def test_usage_summary_window_30d_includes_old_event(client, tmp_path):
    _seed(tmp_path)
    resp = client.get("/usage/summary?window=30d")
    assert resp.status_code == 200
    assert resp.json()["totals"]["events"] == 3


def test_usage_summary_default_window_is_7d(client, tmp_path):
    _seed(tmp_path)
    resp = client.get("/usage/summary")
    assert resp.status_code == 200
    assert resp.json()["window"] == "7d"


def test_usage_summary_rejects_unknown_window(client):
    resp = client.get("/usage/summary?window=forever")
    assert resp.status_code == 422


def test_usage_summary_empty_ledger(client):
    resp = client.get("/usage/summary?window=today")
    assert resp.status_code == 200
    body = resp.json()
    assert body["totals"]["events"] == 0
    assert body["totals"]["cost_usd"] == 0.0
    assert body["by_model"] == []
