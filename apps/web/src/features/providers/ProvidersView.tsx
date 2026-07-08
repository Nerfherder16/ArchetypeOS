import React, { useCallback, useEffect, useState } from 'react';
import {
  fetchUsageSummary,
  type UsageBucket,
  type UsageSummary,
  type UsageWindow,
} from '../../api';
import { ConnectorsView } from '../connectors/ConnectorsView';

// The two panels of the Providers & Model Routing surface: LLM usage (the ledger)
// and the connector registry (AOS-CONNECTOR-001 governance, eval Finding 9).
type ProvidersPanel = 'usage' | 'connectors';

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

// Windows offered by the ledger API (default 7d), in display order.
const WINDOWS: { id: UsageWindow; label: string }[] = [
  { id: 'today', label: 'Today' },
  { id: '7d', label: '7 days' },
  { id: '30d', label: '30 days' },
];

// The three reported tiers, in the deck's order, each with its design-token
// accent: Claude → --signal (cyan), Local → --lex (blue), Free → --agent-scout
// (purple). `key` indexes `summary.by_tier`.
const TIERS: { key: keyof UsageSummary['by_tier']; label: string; sub: string; color: string }[] = [
  { key: 'claude', label: 'Claude', sub: 'subscription', color: 'var(--signal)' },
  { key: 'local', label: 'Local', sub: 'RTX 3070', color: 'var(--lex)' },
  { key: 'free', label: 'Free', sub: 'hosted', color: 'var(--agent-scout)' },
];

const intFmt = new Intl.NumberFormat('en-US');
const compactFmt = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

function formatTokens(n: number): string {
  return intFmt.format(n);
}

function formatCompact(n: number): string {
  return compactFmt.format(n);
}

// Cost is a dollar estimate; keep small values legible (sub-cent → 4 dp) without
// drowning larger totals in noise.
function formatCost(usd: number): string {
  if (usd <= 0) {
    return '$0.00';
  }
  if (usd < 0.01) {
    return `$${usd.toFixed(4)}`;
  }
  return `$${usd.toFixed(2)}`;
}

// A bucket's cost, prefixed `~` when any figure feeding it was length-derived, so
// an estimate is never presented as exact.
function costLabel(bucket: UsageBucket): string {
  return `${bucket.estimated ? '~' : ''}${formatCost(bucket.cost_usd)}`;
}

// Share (0..100) of the window's total tokens this bucket represents.
function sharePct(bucket: UsageBucket, totalTokens: number): number {
  if (totalTokens <= 0) {
    return 0;
  }
  return Math.min(100, (bucket.total_tokens / totalTokens) * 100);
}

function EstimatedMarker() {
  return (
    <span
      className="aos-pill info"
      data-testid="providers-estimated"
      title="At least one figure was length-derived (an LLM envelope lacked exact usage). Costs shown are estimates."
    >
      estimated
    </span>
  );
}

function TierRow({ bucket, tier, totalTokens }: {
  bucket: UsageBucket;
  tier: (typeof TIERS)[number];
  totalTokens: number;
}) {
  const pct = sharePct(bucket, totalTokens);
  const zeroed = bucket.total_tokens === 0;
  return (
    <div
      data-testid="providers-tier-row"
      data-tier={tier.key}
      style={{
        display: 'grid',
        gridTemplateColumns: '150px 1fr auto',
        gap: 16,
        alignItems: 'center',
        padding: '10px 0',
        borderBottom: '1px solid var(--frame)',
        opacity: zeroed ? 0.45 : 1,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            aria-hidden="true"
            style={{ width: 9, height: 9, borderRadius: 2, background: tier.color, flex: '0 0 auto' }}
          />
          <span className="aos-strong" style={{ fontSize: 14 }}>
            {tier.label}
          </span>
        </div>
        <span className="aos-rowmeta" style={{ display: 'block', marginTop: 2 }}>
          {tier.sub}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div
          style={{
            position: 'relative',
            height: 10,
            background: 'var(--panel-2)',
            border: '1px solid var(--frame)',
            borderRadius: 3,
            overflow: 'hidden',
          }}
          role="img"
          aria-label={`${tier.label}: ${pct.toFixed(0)}% of tokens`}
        >
          <div
            style={{
              position: 'absolute',
              inset: 0,
              width: `${pct}%`,
              background: tier.color,
              boxShadow: zeroed ? undefined : `0 0 10px color-mix(in srgb, ${tier.color} 55%, transparent)`,
              // Width transition only; the global reduced-motion rule in tokens.css
              // disables it for viewers who ask for reduced motion.
              transition: 'width 0.35s ease',
            }}
          />
        </div>
        <span className="aos-mono aos-rowmeta">
          {formatTokens(bucket.total_tokens)} tok · {formatTokens(bucket.input_tokens)} in /{' '}
          {formatTokens(bucket.output_tokens)} out · {pct.toFixed(0)}%
        </span>
      </div>

      <div style={{ textAlign: 'right', minWidth: 88 }}>
        <div className="aos-mono aos-strong" style={{ fontSize: 15 }}>
          {costLabel(bucket)}
        </div>
        <span className="aos-rowmeta">est. cost</span>
      </div>
    </div>
  );
}

export function ProvidersView() {
  const [panel, setPanel] = useState<ProvidersPanel>('usage');
  const [usageWindow, setUsageWindow] = useState<UsageWindow>('7d');
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (w: UsageWindow) => {
    setLoading(true);
    setError(null);
    try {
      setSummary(await fetchUsageSummary(w));
    } catch (err) {
      // Graceful degradation: the API being absent (static preview / backend
      // down) must never throw or blank the screen — surface a readable notice.
      setSummary(null);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(usageWindow);
  }, [load, usageWindow]);

  const totals = summary?.totals ?? null;
  const isEmpty = totals !== null && totals.events === 0;

  return (
    <section className="aos-view" data-testid="providers-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--signal)' }} aria-hidden="true">
            &#9672;
          </span>
          Providers &amp; Model Routing
        </span>
        <h2>LLM usage across your tiers</h2>
      </div>

      {/* Panel tabs: LLM usage ledger vs the connector governance registry. */}
      <div className="aos-form-row" role="tablist" aria-label="Providers panel" style={{ marginTop: 0 }}>
        <button
          type="button"
          role="tab"
          className={panel === 'usage' ? 'aos-mchip on' : 'aos-mchip'}
          data-testid="providers-tab-usage"
          aria-selected={panel === 'usage'}
          onClick={() => setPanel('usage')}
        >
          Usage
        </button>
        <button
          type="button"
          role="tab"
          className={panel === 'connectors' ? 'aos-mchip on' : 'aos-mchip'}
          data-testid="providers-tab-connectors"
          aria-selected={panel === 'connectors'}
          onClick={() => setPanel('connectors')}
        >
          Connectors
        </button>
      </div>

      {panel === 'connectors' ? (
        <ConnectorsView />
      ) : (
      <>
      {/* Window selector — always present so the view mounts with its controls
          even when the API is absent. Switching re-fetches. */}
      <div className="aos-form-row" role="group" aria-label="Usage window" style={{ marginTop: 0 }}>
        {WINDOWS.map((w) => (
          <button
            key={w.id}
            type="button"
            className={usageWindow === w.id ? 'aos-mchip on' : 'aos-mchip'}
            data-testid={`providers-window-${w.id}`}
            aria-pressed={usageWindow === w.id}
            onClick={() => setUsageWindow(w.id)}
          >
            {w.label}
          </button>
        ))}
      </div>

      {error ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Usage ledger</span>
          <p role="alert" className="aos-error" data-testid="providers-error" style={{ marginTop: 8 }}>
            Usage unavailable: {error}
          </p>
          <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 13 }}>
            The ledger reads <span className="aos-mono">GET /usage/summary</span>. Once the API is
            reachable, real token and cost usage appears here.
          </p>
        </div>
      ) : loading && summary === null ? (
        <div className="aos-hud glass aos-card">
          <p className="aos-muted" data-testid="providers-loading" style={{ margin: 0 }}>
            Loading usage…
          </p>
        </div>
      ) : isEmpty ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Usage ledger</span>
          <p className="aos-muted" data-testid="providers-empty" style={{ margin: '8px 0 0' }}>
            No usage recorded yet.
          </p>
          <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 13 }}>
            The ledger records reasoned LLM calls once a real provider tier (Claude subscription, the
            local model, or a free hosted API) is configured. Deterministic calls record nothing.
          </p>
        </div>
      ) : summary && totals ? (
        <>
          {/* Headline: total tokens + est. cost for the window. */}
          <div className="aos-hud glass aos-card">
            <span className="aos-eyebrow">Total — {summary.window}</span>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'flex-end',
                gap: '10px 40px',
                marginTop: 8,
              }}
            >
              <div>
                <div
                  className="aos-display"
                  data-testid="providers-total-tokens"
                  title={`${formatTokens(totals.total_tokens)} tokens`}
                  style={{ fontSize: 52, lineHeight: 0.9 }}
                >
                  {formatCompact(totals.total_tokens)}
                </div>
                <span className="aos-mono aos-rowmeta">{formatTokens(totals.total_tokens)} tokens</span>
              </div>
              <div>
                <div
                  className="aos-display"
                  data-testid="providers-total-cost"
                  style={{ fontSize: 52, lineHeight: 0.9, color: 'var(--signal)' }}
                >
                  {totals.estimated ? '~' : ''}
                  {formatCost(totals.cost_usd)}
                </div>
                <span className="aos-mono aos-rowmeta">estimated cost</span>
              </div>
              {totals.estimated ? (
                <div style={{ alignSelf: 'center' }}>
                  <EstimatedMarker />
                </div>
              ) : null}
            </div>

            {/* In / out split. */}
            <dl className="aos-kv" style={{ marginTop: 18 }}>
              <dt>Input tokens</dt>
              <dd className="aos-mono">{formatTokens(totals.input_tokens)}</dd>
              <dt>Output tokens</dt>
              <dd className="aos-mono">{formatTokens(totals.output_tokens)}</dd>
              <dt>Events</dt>
              <dd className="aos-mono">{formatTokens(totals.events)}</dd>
            </dl>
          </div>

          {/* Per-tier rows. All three always render; a zeroed tier is dimmed. */}
          <div className="aos-hud glass aos-card">
            <span className="aos-eyebrow">By tier</span>
            <div style={{ marginTop: 8 }}>
              {TIERS.map((tier) => (
                <TierRow
                  key={tier.key}
                  tier={tier}
                  bucket={summary.by_tier[tier.key]}
                  totalTokens={totals.total_tokens}
                />
              ))}
            </div>
          </div>

          {/* Per-model table, busiest first. */}
          <div className="aos-hud glass aos-card">
            <span className="aos-eyebrow">By model</span>
            {summary.by_model.length === 0 ? (
              <p className="aos-muted" style={{ margin: '12px 0 0' }}>
                No per-model usage in this window.
              </p>
            ) : (
              <table className="aos-table" style={{ marginTop: 12 }}>
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Tier</th>
                    <th>Total tokens</th>
                    <th>In / out</th>
                    <th>Est. cost</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.by_model.map((row) => (
                    <tr key={`${row.model}-${row.tier}`} data-testid="providers-model-row">
                      <td className="aos-mono aos-strong">{row.model}</td>
                      <td className="aos-mono">{row.tier}</td>
                      <td className="aos-mono">{formatTokens(row.total_tokens)}</td>
                      <td className="aos-mono">
                        {formatTokens(row.input_tokens)} / {formatTokens(row.output_tokens)}
                      </td>
                      <td className="aos-mono">{costLabel(row)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      ) : null}
      </>
      )}
    </section>
  );
}
