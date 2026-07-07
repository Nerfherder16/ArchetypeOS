"""LLM usage ledger service (AOS-USAGE-001).

Records token/cost usage for every reasoned LLM call and summarizes it per
**tier** (claude / local / free) so the operator can see all three tiers they use
— the Claude subscription, the local RTX 3070, and the free hosted APIs — in one
place. Each provider reports its own real numbers; this service only derives the
tier, applies the cost rate table for the estimate, aggregates, and windows.

Design notes:

- ``derive_tier`` maps a provider name (+ config) to a tier. The two OpenAI-
  compatible tiers (local vs free hosted) are distinguished by ``base_url``.
- ``record_provider_usage`` is the entry point the :class:`InstrumentedProvider`
  sink calls; it derives the tier, resolves cost (provider-reported cost wins,
  else the rate-table estimate), and inserts a :class:`UsageEvent`. The
  deterministic tier records **nothing**.
- ``make_ledger_sink`` builds the injected sink for the ``llm/`` wrapper, keyed on
  a session factory so ``llm/`` never imports the DB.
- ``summarize_usage`` returns totals + per-tier + per-model breakdowns for a
  window (``today`` / ``7d`` / ``30d``).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models import UsageEvent, now_utc

# Tier vocabulary (mirrors aos_core.services.llm_router.Tier values).
TIER_DETERMINISTIC = "deterministic"
TIER_CLAUDE = "claude"
TIER_LOCAL = "local"
TIER_FREE = "free"

# The tiers surfaced in the summary's per-tier breakdown (deterministic records
# nothing, so it never appears).
REPORTED_TIERS = (TIER_CLAUDE, TIER_LOCAL, TIER_FREE)

_MTOK = 1_000_000.0

_WINDOWS = ("today", "7d", "30d")


def _free_base_urls(settings) -> list[str]:
    """Base URLs that identify the *free hosted* tier (vs the local endpoint)."""
    urls: list[str] = []
    single = getattr(settings, "llm_free_base_url", "") if settings is not None else ""
    if single:
        urls.append(single)
    # The rotation pool's known free providers (assembled from env keys elsewhere).
    try:
        from .llm_pool import DEFAULT_FREE_POOL

        urls.extend(member.base_url for member in DEFAULT_FREE_POOL)
    except Exception:
        pass
    return urls


def derive_tier(provider_name: str, *, base_url: str | None = None, settings=None) -> str:
    """Map a provider name (+ optional ``base_url``/``settings``) to a tier.

    ``deterministic`` → deterministic; ``claude_code`` → claude; ``rotating`` (the
    free rotation pool) → free; ``openai_compatible`` → free when its ``base_url``
    matches a configured free-hosted endpoint, else local (the on-node model).
    """
    if provider_name == "deterministic":
        return TIER_DETERMINISTIC
    if provider_name == "claude_code":
        return TIER_CLAUDE
    if provider_name == "rotating":
        return TIER_FREE
    if provider_name == "openai_compatible":
        if base_url:
            normalized = base_url.rstrip("/")
            if any(normalized == url.rstrip("/") for url in _free_base_urls(settings)):
                return TIER_FREE
        return TIER_LOCAL
    # Unknown reasoned backend: treat as local (a self-hosted model) rather than
    # inventing a cost tier.
    return TIER_LOCAL


def estimate_cost(
    tier: str, input_tokens: int | None, output_tokens: int | None, settings
) -> float:
    """Cost estimate ($) for ``tier`` from the config rate table ($/1M tokens).

    Local/free tiers are ~$0 (self-hosted / free). Claude uses distinct input and
    output per-Mtoken rates. Only used when the provider did not report a real cost.
    """
    in_tok = input_tokens or 0
    out_tok = output_tokens or 0
    if tier == TIER_CLAUDE:
        in_rate = getattr(settings, "usage_cost_claude_input_per_mtok", 3.0)
        out_rate = getattr(settings, "usage_cost_claude_output_per_mtok", 15.0)
        return (in_tok * in_rate + out_tok * out_rate) / _MTOK
    if tier == TIER_FREE:
        rate = getattr(settings, "usage_cost_free_per_mtok", 0.0)
        return (in_tok + out_tok) * rate / _MTOK
    # local + anything else
    rate = getattr(settings, "usage_cost_local_per_mtok", 0.0)
    return (in_tok + out_tok) * rate / _MTOK


def record_usage(
    db: Session,
    *,
    provider: str,
    tier: str,
    model: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_usd: float | None = None,
    estimated: bool = False,
    agent: str | None = None,
    session: str | None = None,
    context: str | None = None,
    ts: datetime | None = None,
    commit: bool = True,
) -> UsageEvent:
    """Insert one :class:`UsageEvent`. Low-level — callers pass an explicit tier."""
    event = UsageEvent(
        ts=ts or now_utc(),
        provider=provider,
        tier=tier,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        estimated=estimated,
        agent=agent,
        session=session,
        context=context,
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    else:
        db.flush()
    return event


def record_provider_usage(
    db: Session,
    *,
    provider: str,
    model: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    cost_usd: float | None,
    estimated: bool,
    base_url: str | None = None,
    settings=None,
    agent: str | None = None,
    session: str | None = None,
    context: str | None = None,
    commit: bool = True,
) -> UsageEvent | None:
    """Record a provider's real usage: derive the tier, resolve cost, insert.

    The deterministic tier records **nothing** (returns ``None``). Provider-
    reported cost (e.g. Claude Code's ``total_cost_usd``) wins; otherwise the
    rate-table estimate is used and, when that estimate is non-trivial (the Claude
    tier), the event's ``estimated`` flag is set. The token-estimate flag from the
    provider is always carried through.
    """
    tier = derive_tier(provider, base_url=base_url, settings=settings)
    if tier == TIER_DETERMINISTIC:
        return None

    resolved_estimated = bool(estimated)
    if cost_usd is None:
        cost_usd = estimate_cost(tier, input_tokens, output_tokens, settings)
        # A Claude cost we computed ourselves (no reported total_cost_usd) is an
        # estimate; local/free rates are a real $0 policy, not an estimate.
        if tier == TIER_CLAUDE:
            resolved_estimated = True

    return record_usage(
        db,
        provider=provider,
        tier=tier,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        estimated=resolved_estimated,
        agent=agent,
        session=session,
        context=context,
        commit=commit,
    )


def make_ledger_sink(
    session_factory,
    settings,
    *,
    context: str | None = None,
    agent: str | None = None,
    session: str | None = None,
):
    """Build the sink the :class:`InstrumentedProvider` calls per ``generate()``.

    ``session_factory`` is a zero-arg callable returning a new
    :class:`~sqlalchemy.orm.Session` (e.g. ``SessionLocal``). Keeping the sink a
    plain closure over a factory means the ``llm/`` package never imports the DB.

    ``context``/``agent``/``session`` are factory-level **defaults**: the wrapper
    forwards its own per-instance labels in ``fields`` (both currently default to
    ``None`` from ``get_provider``), so a caller-set default fills them in when the
    wrapper did not. Best-effort: the wrapper already swallows exceptions, but the
    sink also opens and closes its own session.
    """

    def sink(**fields) -> None:
        # The wrapper always forwards context/agent/session (possibly None); apply
        # the factory-level default when it did not supply one — never pass a key
        # twice (that raised a swallowed TypeError before this merge).
        if fields.get("context") is None:
            fields["context"] = context
        if fields.get("agent") is None:
            fields["agent"] = agent
        if fields.get("session") is None:
            fields["session"] = session
        db = session_factory()
        try:
            record_provider_usage(db, settings=settings, **fields)
        finally:
            db.close()

    return sink


def _window_since(window: str, now: datetime) -> datetime:
    if window == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if window == "30d":
        return now - timedelta(days=30)
    # default / "7d"
    return now - timedelta(days=7)


def _empty_bucket() -> dict:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "events": 0,
        "estimated": False,
    }


def _accumulate(bucket: dict, event: UsageEvent) -> None:
    in_tok = event.input_tokens or 0
    out_tok = event.output_tokens or 0
    bucket["input_tokens"] += in_tok
    bucket["output_tokens"] += out_tok
    bucket["total_tokens"] += in_tok + out_tok
    bucket["cost_usd"] += event.cost_usd or 0.0
    bucket["events"] += 1
    if event.estimated:
        bucket["estimated"] = True


def summarize_usage(db: Session, *, window: str = "7d", now: datetime | None = None) -> dict:
    """Totals + per-tier + per-model usage for ``window`` (today / 7d / 30d).

    Returns a JSON-serializable dict: ``totals`` (tokens in/out, total, cost,
    events, whether any figure is estimated), ``by_tier`` (a bucket for each of
    claude/local/free — always present, zeroed when empty), and ``by_model`` (one
    bucket per (model, tier), busiest first).
    """
    if window not in _WINDOWS:
        raise ValueError(f"Unknown window {window!r} (expected one of {_WINDOWS})")
    now = now or datetime.now(timezone.utc)
    since = _window_since(window, now)

    events = (
        db.query(UsageEvent)
        .filter(UsageEvent.ts >= since)
        .order_by(UsageEvent.ts)
        .all()
    )

    totals = _empty_bucket()
    by_tier: dict[str, dict] = {tier: _empty_bucket() for tier in REPORTED_TIERS}
    by_model: dict[tuple[str, str], dict] = {}

    for event in events:
        _accumulate(totals, event)
        tier_bucket = by_tier.setdefault(event.tier, _empty_bucket())
        _accumulate(tier_bucket, event)
        model_key = (event.model or "unknown", event.tier)
        model_bucket = by_model.get(model_key)
        if model_bucket is None:
            model_bucket = _empty_bucket()
            model_bucket["model"] = event.model or "unknown"
            model_bucket["tier"] = event.tier
            by_model[model_key] = model_bucket
        _accumulate(model_bucket, event)

    by_model_list = sorted(
        by_model.values(), key=lambda bucket: bucket["total_tokens"], reverse=True
    )

    return {
        "window": window,
        "since": since.isoformat(),
        "totals": totals,
        "by_tier": by_tier,
        "by_model": by_model_list,
    }


__all__ = [
    "TIER_DETERMINISTIC",
    "TIER_CLAUDE",
    "TIER_LOCAL",
    "TIER_FREE",
    "REPORTED_TIERS",
    "derive_tier",
    "estimate_cost",
    "record_usage",
    "record_provider_usage",
    "make_ledger_sink",
    "summarize_usage",
]
