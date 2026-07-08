"""Connector registry + policy service (AOS-CONNECTOR-001, eval Finding 9).

Connectors define where data goes, so ArchetypeOS governs them as first-class
assets. The static governance attributes live in a declarative ``CONNECTOR_CATALOG``
(the single source of truth for type/tier/privacy posture/egress/browser-exposed/
quota); ``sync_connectors`` reconciles that catalog into the DB and recomputes
``configured`` from settings each time, so the "is this wired up?" bit is never
hand-maintained and cannot drift. Health is recorded by a probe (``record_health``),
mirroring the Node heartbeat pattern. Hermetic: pure DB + settings, no network.

See ``docs/CONNECTOR_POLICY.md`` for the governance rules these encode.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from ..models import Connector, now_utc

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session

    from ..config import Settings


@dataclass(frozen=True)
class ConnectorSpec:
    """Declarative governance record for a known connector.

    ``configured_when`` reads settings and answers "does this connector have the
    config it needs to run?" — the one dynamic bit, recomputed on every sync.
    """

    name: str
    connector_type: str
    tier: str
    privacy_class: str  # "private_ok" | "public_only"
    egress_allowed: bool
    browser_exposed: bool
    quota_policy: str
    configured_when: Callable[["Settings"], bool]
    enabled_default: bool = True


# The known connectors, exactly the set the eval enumerated (Finding 9). Adding a
# new external connection means adding a row here — that is what makes the registry
# the governance choke point instead of scattered env vars.
CONNECTOR_CATALOG: list[ConnectorSpec] = [
    ConnectorSpec(
        name="claude_code",
        connector_type="llm",
        tier="claude",
        privacy_class="private_ok",
        egress_allowed=True,
        browser_exposed=False,
        quota_policy="subscription",
        configured_when=lambda s: bool(s.llm_claude_enabled),
    ),
    ConnectorSpec(
        name="local_llm",
        connector_type="llm",
        tier="local",
        privacy_class="private_ok",
        egress_allowed=False,
        browser_exposed=False,
        quota_policy="self-hosted",
        configured_when=lambda s: bool(s.llm_base_url),
    ),
    ConnectorSpec(
        name="free_llm_pool",
        connector_type="llm",
        tier="free",
        privacy_class="public_only",
        egress_allowed=True,
        browser_exposed=False,
        quota_policy="free-tier",
        configured_when=lambda s: bool(s.llm_free_api_key),
    ),
    ConnectorSpec(
        name="groq_tts",
        connector_type="tts",
        tier="free",
        privacy_class="public_only",
        egress_allowed=True,
        browser_exposed=False,
        quota_policy="free-tier",
        configured_when=lambda s: bool(s.tts_api_key),
    ),
    ConnectorSpec(
        name="sotto_stt",
        connector_type="stt",
        tier="local",
        privacy_class="private_ok",
        egress_allowed=False,
        # VITE_SOTTO_TOKEN ships to the browser by design — it must be labeled so
        # the operator treats it as a public/client token (eval Finding 9).
        browser_exposed=True,
        quota_policy="self-hosted",
        configured_when=lambda s: bool(s.voice_stt_ws_url),
    ),
    ConnectorSpec(
        name="exa",
        connector_type="research",
        tier="external",
        privacy_class="public_only",
        egress_allowed=True,
        browser_exposed=False,
        quota_policy="metered",
        configured_when=lambda s: bool(s.exa_api_key),
    ),
    ConnectorSpec(
        name="searxng",
        connector_type="research",
        tier="local",
        privacy_class="public_only",
        egress_allowed=False,
        browser_exposed=False,
        quota_policy="self-hosted",
        configured_when=lambda s: bool(s.searxng_url),
    ),
    ConnectorSpec(
        name="crawl4ai",
        connector_type="research",
        tier="local",
        privacy_class="public_only",
        egress_allowed=False,
        browser_exposed=False,
        quota_policy="self-hosted",
        configured_when=lambda s: bool(s.crawl4ai_url),
    ),
    ConnectorSpec(
        name="firecrawl",
        connector_type="research",
        tier="external",
        privacy_class="public_only",
        egress_allowed=True,
        browser_exposed=False,
        quota_policy="metered",
        configured_when=lambda s: bool(s.firecrawl_url),
    ),
    ConnectorSpec(
        name="github",
        connector_type="integration",
        tier="external",
        privacy_class="public_only",
        egress_allowed=True,
        browser_exposed=False,
        quota_policy="rate-limited",
        # GitHub/CI/PR Guardian is wired through the platform, not a runtime setting.
        configured_when=lambda s: True,
    ),
]


def sync_connectors(db: "Session", settings: "Settings") -> list[Connector]:
    """Reconcile the catalog into the registry and recompute ``configured``.

    Idempotent by name: existing rows are updated in place (governance attributes
    refreshed from the catalog, ``configured`` recomputed from settings), missing
    rows are created. Health fields are never touched here — only ``record_health``
    writes them. Returns all connectors in catalog order.
    """
    existing = {c.name: c for c in db.query(Connector).all()}
    result: list[Connector] = []
    for spec in CONNECTOR_CATALOG:
        connector = existing.get(spec.name)
        if connector is None:
            connector = Connector(name=spec.name, enabled=spec.enabled_default)
            db.add(connector)
        connector.connector_type = spec.connector_type
        connector.tier = spec.tier
        connector.privacy_class = spec.privacy_class
        connector.egress_allowed = spec.egress_allowed
        connector.browser_exposed = spec.browser_exposed
        connector.quota_policy = spec.quota_policy
        connector.configured = bool(spec.configured_when(settings))
        result.append(connector)
    db.commit()
    for connector in result:
        db.refresh(connector)
    return result


def record_health(
    db: "Session", *, name: str, status: str = "healthy", error: str | None = None
) -> Connector | None:
    """Record a health-probe result on a connector. None if the connector is unknown."""
    connector = db.query(Connector).filter(Connector.name == name).first()
    if connector is None:
        return None
    connector.last_health_status = status
    connector.last_error = error
    connector.last_checked_at = now_utc()
    db.commit()
    db.refresh(connector)
    return connector
