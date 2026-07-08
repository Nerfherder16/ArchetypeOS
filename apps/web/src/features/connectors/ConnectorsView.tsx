import React, { useCallback, useEffect, useState } from 'react';
import { fetchConnectors, type Connector } from '../../api';

// AOS-CONNECTOR-001 (UI) — the Connectors tab under Operations → Providers & Model
// Routing. Read-only governance panel (eval Finding 9): every external connection
// in one place, each showing its privacy posture (privacy class, egress, and
// whether a token is browser-exposed), whether it is configured/enabled, and its
// last recorded health. Connectors define where data goes; this is where the
// operator sees and audits that.

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

const HEALTH_TIER: Record<string, string> = {
  healthy: 'good',
  degraded: 'warn',
  offline: 'risk',
  unknown: '',
};

// A connector that may receive private data is the one to watch — surface it.
const privacyLabel = (c: Connector): string =>
  c.privacy_class === 'private_ok' ? 'private-ok' : 'public-only';

function ConnectorCard({ connector }: { connector: Connector }) {
  const health = connector.configured ? connector.last_health_status : 'unconfigured';
  return (
    <li
      className="aos-hud glass aos-card"
      data-testid="connector-card"
      data-connector={connector.name}
      style={{ opacity: connector.configured ? 1 : 0.62 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span
          className={`aos-pill ${connector.configured ? HEALTH_TIER[connector.last_health_status] ?? '' : ''}`}
          data-testid="connector-health"
        >
          {health}
        </span>
        <h3 style={{ margin: 0, fontSize: 15 }}>{connector.name}</h3>
        <span className="aos-eyebrow" style={{ letterSpacing: '0.12em' }}>
          {connector.connector_type} · {connector.tier}
        </span>
        <span
          className={`aos-pill ${connector.privacy_class === 'private_ok' ? 'warn' : ''}`}
          data-testid="connector-privacy"
          title="privacy class"
        >
          {privacyLabel(connector)}
        </span>
        <span className="aos-pill" title="network egress">
          {connector.egress_allowed ? 'egress: external' : 'egress: local'}
        </span>
        {connector.browser_exposed ? (
          <span className="aos-pill risk" data-testid="connector-browser-exposed" title="a token/URL for this connector ships to the browser">
            browser-exposed
          </span>
        ) : null}
        {!connector.configured ? (
          <span className="aos-pill" data-testid="connector-unconfigured">unconfigured</span>
        ) : !connector.enabled ? (
          <span className="aos-pill">disabled</span>
        ) : null}
      </div>

      <div className="aos-rowmeta aos-mono" style={{ marginTop: 6 }}>
        quota: {connector.quota_policy}
        {connector.last_checked_at
          ? ` · checked ${new Date(connector.last_checked_at).toLocaleString()}`
          : ' · never checked'}
      </div>

      {connector.configured && connector.last_error ? (
        <p className="aos-error" data-testid="connector-error" style={{ margin: '8px 0 0', fontSize: 12.5 }}>
          {connector.last_error}
        </p>
      ) : null}
    </li>
  );
}

export function ConnectorsView() {
  const [connectors, setConnectors] = useState<Connector[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setConnectors(await fetchConnectors());
    } catch (err) {
      setConnectors(null);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const count = connectors?.length ?? 0;
  const configuredCount = connectors?.filter((c) => c.configured).length ?? 0;
  const isEmpty = connectors !== null && connectors.length === 0;

  return (
    <div data-testid="connectors-view">
      {connectors !== null && count > 0 ? (
        <p className="aos-rowmeta aos-mono" data-testid="connectors-count" style={{ margin: '0 0 12px' }}>
          {configuredCount}/{count} configured
        </p>
      ) : null}

      {error ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Connector registry</span>
          <p role="alert" className="aos-error" data-testid="connectors-error" style={{ marginTop: 8 }}>
            Registry unavailable: {error}
          </p>
        </div>
      ) : loading && connectors === null ? (
        <div className="aos-hud glass aos-card">
          <p className="aos-muted" data-testid="connectors-loading" style={{ margin: 0 }}>
            Loading the connector registry…
          </p>
        </div>
      ) : isEmpty ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Connector registry</span>
          <p className="aos-muted" data-testid="connectors-empty" style={{ margin: '8px 0 0' }}>
            No connectors registered.
          </p>
        </div>
      ) : connectors !== null ? (
        <ul className="aos-rows" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {connectors.map((connector) => (
            <ConnectorCard key={connector.id} connector={connector} />
          ))}
        </ul>
      ) : null}

      <p className="aos-mono aos-muted" style={{ margin: '16px 0 0', fontSize: 11.5 }}>
        Read-only governance view. Connectors define where data goes; see docs/CONNECTOR_POLICY.md for the rules.
        Public-only connectors must never receive private data; browser-exposed tokens are client tokens.
      </p>
    </div>
  );
}
