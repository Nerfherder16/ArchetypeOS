"""Connector registry + policy API tests (AOS-CONNECTOR-001, eval Finding 9).

Connectors are governed as first-class assets: a declarative catalog is reconciled
into the registry, `configured` is computed from settings (never hand-maintained),
privacy posture (privacy_class / egress_allowed / browser_exposed) is visible, and
health is recorded via a probe. Hermetic: the service-level `configured` logic is
exercised against constructed Settings; the API surface is exercised via the sqlite
`client` fixture. Disabled/unconfigured connectors must be visible without errors.
"""

from __future__ import annotations


# --- service-level: catalog reconcile + configured computation (pure, no leakage) ---


def test_sync_seeds_the_known_connector_catalog_idempotently(db_session):
    from aos_core.config import Settings
    from aos_core.services.connectors import CONNECTOR_CATALOG, sync_connectors

    settings = Settings()
    first = sync_connectors(db_session, settings)
    names = {c.name for c in first}
    # Every catalogued connector the eval named is present.
    for expected in ("claude_code", "sotto_stt", "exa", "free_llm_pool"):
        assert expected in names
    assert len(first) == len(CONNECTOR_CATALOG)

    # Re-sync is idempotent: same rows, no duplicates.
    second = sync_connectors(db_session, settings)
    assert {c.id for c in second} == {c.id for c in first}
    assert len(second) == len(CONNECTOR_CATALOG)


def test_configured_is_computed_from_settings(db_session):
    from aos_core.config import Settings
    from aos_core.services.connectors import sync_connectors

    # Exa unconfigured (no key) → configured False; with a key → configured True.
    off = {c.name: c for c in sync_connectors(db_session, Settings(exa_api_key=""))}
    assert off["exa"].configured is False

    on = {c.name: c for c in sync_connectors(db_session, Settings(exa_api_key="exa-key"))}
    assert on["exa"].configured is True, "re-sync recomputes configured from settings"


def test_sotto_is_flagged_browser_exposed_and_carries_privacy_class(db_session):
    from aos_core.config import Settings
    from aos_core.services.connectors import sync_connectors

    connectors = {c.name: c for c in sync_connectors(db_session, Settings())}
    sotto = connectors["sotto_stt"]
    # VITE_SOTTO_TOKEN ships to the browser by design — it must be labeled.
    assert sotto.browser_exposed is True
    # A free public LLM pool must never be marked able to receive private data.
    assert connectors["free_llm_pool"].privacy_class == "public_only"
    assert connectors["free_llm_pool"].egress_allowed is True


# --- API surface ---


def test_get_connectors_lists_catalog_without_errors_when_unconfigured(client):
    resp = client.get("/connectors")
    assert resp.status_code == 200, resp.text
    connectors = resp.json()
    assert len(connectors) >= 8, "the whole catalog is visible, configured or not"
    # Shape carries the governance fields the dashboard needs.
    sample = connectors[0]
    for field in (
        "name",
        "connector_type",
        "tier",
        "enabled",
        "configured",
        "privacy_class",
        "egress_allowed",
        "browser_exposed",
        "last_health_status",
    ):
        assert field in sample
    # Unconfigured connectors are present, not errored out.
    assert any(c["configured"] is False for c in connectors)


def test_record_health_rolls_status_onto_connector(client):
    client.get("/connectors")  # ensure the catalog is synced
    resp = client.post("/connectors/exa/health", json={"status": "degraded", "error": "429 rate limited"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["last_health_status"] == "degraded"
    assert body["last_error"] == "429 rate limited"
    assert body["last_checked_at"]
    # Reflected on the listing.
    listed = {c["name"]: c for c in client.get("/connectors").json()}
    assert listed["exa"]["last_health_status"] == "degraded"


def test_health_for_unknown_connector_404(client):
    client.get("/connectors")
    resp = client.post("/connectors/does-not-exist/health", json={"status": "healthy"})
    assert resp.status_code == 404


def test_get_unknown_connector_404(client):
    client.get("/connectors")
    assert client.get("/connectors/nope").status_code == 404
