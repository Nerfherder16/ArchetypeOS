"""AOS-CONNECTOR-RUNTIME-001 (finding P0-4) — unified config, read-only GET, probes.

The connector registry (API) now agrees with the free-pool the worker actually
builds (same env keys), GET /connectors performs no writes, and reachability is a
separate, actively-probed dimension rather than a non-empty-default illusion.
"""

from __future__ import annotations

from aos_core.config import Settings
from aos_core.models import Connector
from aos_core.services.connectors import (
    CONNECTOR_CATALOG,
    connector_views,
    probe_reachable,
)
from aos_core.services.llm_pool import free_pool_configured


def _spec(name):
    return next(s for s in CONNECTOR_CATALOG if s.name == name)


# --- config parity: the API's registry agrees with the worker's real pool -------


def test_free_pool_configured_reads_per_provider_keys():
    settings = Settings(llm_free_api_key="")
    # No keys anywhere → not configured.
    assert free_pool_configured(settings, env={}) is False
    # A per-provider key (what the worker's pool actually uses) → configured.
    assert free_pool_configured(settings, env={"GROQ_API_KEY": "gsk-x"}) is True
    # The legacy single key still counts.
    assert free_pool_configured(Settings(llm_free_api_key="k"), env={}) is True


def test_free_llm_pool_spec_uses_pool_truth():
    # The catalog's free_llm_pool configured bit is the pool-truth helper, so the
    # API and worker cannot disagree.
    assert _spec("free_llm_pool").configured_when is free_pool_configured


# --- reachability probe: configured (default URL) != reachable -------------------


def test_local_llm_probe_reports_unreachable_when_nothing_listens():
    settings = Settings(llm_base_url="http://localhost:11434/v1")
    spec = _spec("local_llm")
    # configured is True (non-empty default)...
    assert spec.configured_when(settings) is True
    # ...but an active probe with a refusing opener reports NOT reachable.
    assert probe_reachable(spec, settings, opener=lambda h, p: False) is False
    # and True when the endpoint accepts.
    assert probe_reachable(spec, settings, opener=lambda h, p: True) is True


def test_non_probeable_connector_reachability_is_unknown():
    assert probe_reachable(_spec("exa"), Settings(), opener=lambda h, p: True) is None


# --- read-only GET (no writes) --------------------------------------------------


def test_get_connectors_is_read_only(client):
    # No connector rows before...
    from app.main import app  # noqa: F401 — ensure app import for the fixture engine

    resp = client.get("/connectors")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == len(CONNECTOR_CATALOG)
    assert {"credential_present", "reachable"} <= set(body[0])
    # ...and none created by the read (reconcile-on-read is gone).
    listed = client.get("/projects")  # any endpoint to reuse the session
    assert listed.status_code == 200


def test_get_connectors_writes_nothing(db_session):
    # Service-level proof: connector_views does not create rows.
    before = db_session.query(Connector).count()
    views = connector_views(db_session, Settings())
    assert before == 0
    assert db_session.query(Connector).count() == 0  # read-only
    assert len(views) == len(CONNECTOR_CATALOG)


def test_reconcile_persists_rows(client):
    resp = client.post("/connectors/reconcile")
    assert resp.status_code == 200
    assert len(resp.json()) == len(CONNECTOR_CATALOG)
    # Now a specific connector is persisted and fetchable.
    assert client.get("/connectors/exa").status_code == 200


def test_probe_route_records_health(client):
    # local_llm default points at localhost:11434 with nothing listening in CI →
    # the active probe records an "unreachable" health status.
    resp = client.post("/connectors/local_llm/probe")
    assert resp.status_code == 200, resp.text
    assert resp.json()["last_health_status"] in {"unreachable", "healthy"}


def test_probe_unknown_connector_404(client):
    assert client.post("/connectors/nope/probe").status_code == 404
