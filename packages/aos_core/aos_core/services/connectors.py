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

import socket
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable
from urllib.parse import urlparse

from ..models import Connector, now_utc
from .llm_pool import free_pool_configured

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
    # AOS-CONNECTOR-RUNTIME-001 (finding P0-4): the settings field holding a URL to
    # actively probe for reachability, so a connector "configured" from a non-empty
    # default (e.g. local_llm's localhost base_url) is not reported live when nothing
    # is listening. None → not cheaply probeable (reachability reported as unknown).
    probe_setting: str | None = None


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
        probe_setting="llm_base_url",  # a non-empty default ≠ reachable (P0-4)
    ),
    ConnectorSpec(
        name="free_llm_pool",
        connector_type="llm",
        tier="free",
        privacy_class="public_only",
        egress_allowed=True,
        browser_exposed=False,
        quota_policy="free-tier",
        # The real pool is keyed on the per-provider env vars (GROQ/CEREBRAS/GEMINI/
        # MISTRAL) that the worker uses; free_pool_configured reads that same source
        # so the API's registry agrees with the worker's pool (finding P0-4).
        configured_when=free_pool_configured,
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


_CATALOG_BY_NAME = {spec.name: spec for spec in CONNECTOR_CATALOG}


def _apply_spec(connector: Connector, spec: ConnectorSpec, settings: "Settings") -> None:
    connector.connector_type = spec.connector_type
    connector.tier = spec.tier
    connector.privacy_class = spec.privacy_class
    connector.egress_allowed = spec.egress_allowed
    connector.browser_exposed = spec.browser_exposed
    connector.quota_policy = spec.quota_policy
    connector.configured = bool(spec.configured_when(settings))


def sync_connectors(db: "Session", settings: "Settings") -> list[Connector]:
    """Reconcile the catalog into the registry and recompute ``configured``.

    Idempotent by name. This WRITES — it is the explicit reconciliation path
    (startup or ``POST /connectors/reconcile``), no longer invoked on a read GET
    (finding P0-4). Returns all connectors in catalog order.
    """
    existing = {c.name: c for c in db.query(Connector).all()}
    result: list[Connector] = []
    for spec in CONNECTOR_CATALOG:
        connector = existing.get(spec.name)
        if connector is None:
            connector = Connector(name=spec.name, enabled=spec.enabled_default)
            db.add(connector)
        _apply_spec(connector, spec, settings)
        result.append(connector)
    db.commit()
    for connector in result:
        db.refresh(connector)
    return result


def ensure_connector(db: "Session", name: str, settings: "Settings") -> Connector | None:
    """Get-or-create a single connector row from the catalog. None if not catalogued."""
    spec = _CATALOG_BY_NAME.get(name)
    if spec is None:
        return None
    connector = db.query(Connector).filter(Connector.name == name).first()
    if connector is None:
        connector = Connector(name=spec.name, enabled=spec.enabled_default)
        db.add(connector)
    _apply_spec(connector, spec, settings)
    db.commit()
    db.refresh(connector)
    return connector


def _default_opener(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def probe_reachable(spec: ConnectorSpec, settings: "Settings", *, opener: Callable[..., bool] | None = None) -> bool | None:
    """Actively check whether a connector's endpoint accepts a TCP connection.

    Returns True/False for a probeable connector, or None when it is not cheaply
    probeable. This is the "reachable" dimension the eval asked to separate from
    "configured" (a non-empty default URL is configured but may be unreachable).
    """
    if not spec.probe_setting:
        return None
    url = getattr(settings, spec.probe_setting, "") or ""
    if not url:
        return False
    parsed = urlparse(url if "://" in url else f"//{url}")
    host = parsed.hostname
    if not host:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return (opener or _default_opener)(host, port)


def connector_views(db: "Session", settings: "Settings") -> list[dict]:
    """A READ-ONLY registry view: catalog + current settings + persisted health.

    No writes (finding P0-4): ``configured``/``credential_present`` are computed
    from settings in memory; persisted health is overlaid when a row exists; a
    connector with no row yet is reported as ``status="declared"``.
    """
    persisted = {c.name: c for c in db.query(Connector).all()}
    now = now_utc()
    views: list[dict] = []
    for spec in CONNECTOR_CATALOG:
        row = persisted.get(spec.name)
        credential_present = bool(spec.configured_when(settings))
        views.append(
            {
                "id": row.id if row else "",
                "name": spec.name,
                "connector_type": spec.connector_type,
                "tier": spec.tier,
                "enabled": row.enabled if row else spec.enabled_default,
                "configured": credential_present,
                "credential_present": credential_present,
                "reachable": None,  # populated by the explicit probe route, not on read
                "privacy_class": spec.privacy_class,
                "egress_allowed": spec.egress_allowed,
                "browser_exposed": spec.browser_exposed,
                "quota_policy": spec.quota_policy,
                "last_health_status": row.last_health_status if row else "unknown",
                "last_error": row.last_error if row else None,
                "last_checked_at": row.last_checked_at if row else None,
                "status": row.status if row else "declared",
                "version": row.version if row else 1,
                "created_at": row.created_at if row else now,
                "updated_at": row.updated_at if row else now,
            }
        )
    return views


def record_health(
    db: "Session",
    *,
    name: str,
    status: str = "healthy",
    error: str | None = None,
    settings: "Settings" | None = None,
) -> Connector | None:
    """Record a health-probe result. Creates the row on demand for a catalogued
    connector (so a read-only GET is no longer a prerequisite). None if unknown."""
    connector = db.query(Connector).filter(Connector.name == name).first()
    if connector is None:
        if settings is None:
            from ..config import get_settings

            settings = get_settings()
        connector = ensure_connector(db, name, settings)
        if connector is None:
            return None
    connector.last_health_status = status
    connector.last_error = error
    connector.last_checked_at = now_utc()
    db.commit()
    db.refresh(connector)
    return connector


def probe_and_record(
    db: "Session", *, name: str, settings: "Settings", opener: Callable[..., bool] | None = None
) -> Connector | None:
    """Active reachability probe → recorded health (replaces manual health posting).

    ``healthy`` when reachable, ``unreachable`` when the endpoint refuses, ``unknown``
    when the connector is not probeable. None if the connector is not catalogued.
    """
    spec = _CATALOG_BY_NAME.get(name)
    if spec is None:
        return None
    reachable = probe_reachable(spec, settings, opener=opener)
    if reachable is None:
        status, err = "unknown", "connector is not reachability-probeable"
    elif reachable:
        status, err = "healthy", None
    else:
        status, err = "unreachable", f"no TCP connection to {getattr(settings, spec.probe_setting, '')}"
    return record_health(db, name=name, status=status, error=err, settings=settings)
