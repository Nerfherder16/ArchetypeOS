import React, { useCallback, useEffect, useState } from 'react';
import {
  fetchReuseRecommendations,
  type TransferEvidence,
  type TransferRecommendation,
} from '../../api';

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

// Lit signal-bars for a 0..1 confidence, per spec: round(confidence * 5), clamped.
function litBars(confidence: number): number {
  const lit = Math.round(confidence * 5);
  return Math.max(0, Math.min(5, lit));
}

// The first distillation evidence entry is what a recommendation "cites".
function firstDistillationRef(evidence: TransferEvidence[]): string | null {
  for (const entry of evidence) {
    if (entry.type === 'distillation') {
      return entry.ref;
    }
  }
  return null;
}

function ConfidenceMeter({ confidence }: { confidence: number }) {
  const lit = litBars(confidence);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6 }}>
      <div className="aos-bars" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className={i < lit ? 'aos-bar lit' : 'aos-bar'} />
        ))}
      </div>
      <div
        className="aos-mono"
        style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em' }}
      >
        {confidence.toFixed(2)}
      </div>
      <div
        className="aos-eyebrow"
        style={{ fontSize: 9, letterSpacing: '0.18em' }}
        aria-label={`confidence ${confidence.toFixed(2)}`}
      >
        confidence
      </div>
    </div>
  );
}

function EvidenceList({ evidence }: { evidence: TransferEvidence[] }) {
  if (evidence.length === 0) {
    return <p style={{ margin: 0, color: 'var(--ink-3)' }}>No evidence recorded.</p>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
      {evidence.map((entry, i) => (
        <span
          key={i}
          className="aos-mono"
          style={{ fontSize: 12, color: 'var(--signal)', display: 'inline-flex', alignItems: 'center', gap: 7 }}
        >
          {entry.type === 'distillation' ? entry.ref : entry.id}
          <span
            style={{
              color: 'var(--ink-3)',
              background: 'var(--panel-2)',
              padding: '1px 6px',
              border: '1px solid var(--frame)',
              fontSize: 10,
            }}
          >
            {entry.type}
          </span>
        </span>
      ))}
    </div>
  );
}

function DetailBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="aos-eyebrow" style={{ display: 'block', marginBottom: 6 }}>
        {label}
      </span>
      {children}
    </div>
  );
}

function ReuseCard({ rec, rank }: { rec: TransferRecommendation; rank: number }) {
  const [open, setOpen] = useState(false);
  const citedRef = firstDistillationRef(rec.evidence);
  const detailId = `reuse-detail-${rank}`;

  return (
    <article
      className="aos-hud glass"
      data-testid="reuse-result-row"
      style={{ ['--cut' as string]: '13px', marginBottom: 12 }}
    >
      <div style={{ position: 'absolute', top: 8, left: 12, zIndex: 3 }}>
        <span className="aos-eyebrow" style={{ fontSize: 9, letterSpacing: '0.14em' }}>
          {String(rank).padStart(2, '0')}
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '110px 1fr auto',
          gap: 18,
          padding: '15px 18px',
          alignItems: 'center',
        }}
      >
        <ConfidenceMeter confidence={rec.confidence} />

        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap' }}>
            <span
              style={{
                width: 9,
                height: 9,
                transform: 'rotate(45deg)',
                background: 'var(--signal)',
                boxShadow: 'var(--glow-soft)',
                flex: '0 0 auto',
              }}
              aria-hidden="true"
            />
            <h3 className="aos-mono" style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>
              {rec.source_repository}
            </h3>
          </div>
          <div style={{ color: 'var(--ink-2)', fontSize: 13, margin: '6px 0 9px' }}>
            {rec.reusable_asset}
          </div>
          {rec.matched_terms.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {rec.matched_terms.map((term) => (
                <span key={term} className="aos-chip">
                  {term}
                </span>
              ))}
            </div>
          ) : (
            <span className="aos-chip dim">semantic match only</span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            type="button"
            className="aos-btn-ghost"
            data-testid="reuse-expand"
            aria-expanded={open}
            aria-controls={detailId}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? 'Hide detail' : 'Show detail'}
          </button>
        </div>
      </div>

      {open ? (
        <div id={detailId} style={{ padding: '4px 18px 16px' }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '15px 26px',
              paddingTop: 14,
              borderTop: '1px dashed var(--frame-bright)',
            }}
          >
            <DetailBlock label="Reason">
              <p style={{ margin: 0, color: 'var(--ink-2)', fontSize: 13 }}>{rec.reason}</p>
            </DetailBlock>
            <DetailBlock label="Evidence">
              <EvidenceList evidence={rec.evidence} />
            </DetailBlock>
            <DetailBlock label="Required changes">
              <p style={{ margin: 0, color: 'var(--ink-2)', fontSize: 13 }}>
                {rec.required_changes ?? 'None recorded.'}
              </p>
            </DetailBlock>
            <DetailBlock label="Risks">
              <p style={{ margin: 0, color: 'var(--ink-2)', fontSize: 13 }}>
                {rec.risks ?? 'None recorded.'}
              </p>
            </DetailBlock>
          </div>
        </div>
      ) : null}

      <div
        className="aos-mono"
        style={{
          fontSize: 11,
          color: 'var(--ink-3)',
          padding: '9px 18px',
          marginTop: 4,
          borderTop: '1px solid var(--frame)',
          background: 'color-mix(in srgb, var(--panel-2) 60%, transparent)',
        }}
      >
        {citedRef
          ? `provenance: cites ${citedRef}`
          : 'provenance: every claim traces to the source distillation'}
      </div>
    </article>
  );
}

export function ReuseView({ projectId }: { projectId: string | null }) {
  const [need, setNeed] = useState('');
  const [results, setResults] = useState<TransferRecommendation[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Set once a scan has actually run, so the empty state only shows post-submit.
  const [hasRun, setHasRun] = useState(false);

  // Reset the panel when the selected project changes — results from one
  // project must never bleed into another.
  useEffect(() => {
    setResults(null);
    setError(null);
    setHasRun(false);
  }, [projectId]);

  const trimmedNeed = need.trim();

  const runScan = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!projectId || !trimmedNeed) {
        return;
      }
      setLoading(true);
      setError(null);
      setHasRun(true);
      try {
        setResults(await fetchReuseRecommendations(projectId, trimmedNeed));
      } catch (err) {
        setResults(null);
        setError(errorMessage(err));
      } finally {
        setLoading(false);
      }
    },
    [projectId, trimmedNeed],
  );

  return (
    <section
      className="aos-surface"
      data-testid="reuse-view"
      style={{ marginTop: 24, padding: 24, borderRadius: 2 }}
    >
      <header style={{ marginBottom: 16 }}>
        <div className="aos-eyebrow" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--signal)' }} aria-hidden="true">
            &#9672;
          </span>
          Knowledge Transfer Engine
        </div>
        <h2 className="aos-display" style={{ fontSize: 42, marginTop: 9 }}>
          Reuse across your <span style={{ color: 'var(--signal)' }}>portfolio</span>
        </h2>
        <p style={{ color: 'var(--ink-2)', margin: '7px 0 0', maxWidth: '60ch', fontSize: 13.5 }}>
          Describe what you&apos;re about to build. The engine scans every distilled repository
          across the portfolio and ranks evidence-backed reuse candidates by confidence.
        </p>
      </header>

      {projectId === null ? (
        <div className="aos-hud glass" style={{ padding: 18 }}>
          <p style={{ margin: 0, color: 'var(--ink-2)' }}>
            Select or create a project above to scan the portfolio for reusable knowledge.
          </p>
        </div>
      ) : (
        <>
          <div className="aos-hud glass lit raise" style={{ padding: 20 }}>
            <form onSubmit={runScan} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <label htmlFor="reuse-need" className="aos-eyebrow">
                Target need
              </label>
              <div style={{ display: 'flex', gap: 11, flexWrap: 'wrap' }}>
                <div style={{ flex: '1 1 260px', position: 'relative' }}>
                  <input
                    id="reuse-need"
                    className="aos-input"
                    type="text"
                    data-testid="reuse-need-input"
                    value={need}
                    placeholder="e.g. an LLM provider abstraction to route prompts across model backends"
                    onChange={(event) => setNeed(event.target.value)}
                    aria-describedby="reuse-scope"
                  />
                </div>
                <button
                  type="submit"
                  className="aos-btn"
                  data-testid="reuse-run"
                  disabled={loading || trimmedNeed === ''}
                >
                  {loading ? 'Scanning…' : 'Find reuse'}
                </button>
              </div>
              {hasRun || trimmedNeed !== '' ? null : (
                <p style={{ margin: 0, fontSize: 11.5, color: 'var(--ink-3)' }} className="aos-mono">
                  Describe a need first, then run the scan.
                </p>
              )}
              <div
                id="reuse-scope"
                className="aos-mono"
                style={{ fontSize: 11.5, color: 'var(--ink-3)', display: 'flex', gap: 7, alignItems: 'center' }}
              >
                <span
                  style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--ink-3)' }}
                  aria-hidden="true"
                />
                Scoped to this project — its own repositories are excluded from results.
              </div>
            </form>
          </div>

          {error ? (
            <p
              role="alert"
              data-testid="reuse-error"
              style={{ color: 'var(--red)', marginTop: 16 }}
            >
              {error}
            </p>
          ) : null}

          {!error && hasRun && !loading && results !== null && results.length === 0 ? (
            <p data-testid="reuse-empty" style={{ marginTop: 16, color: 'var(--ink-2)' }}>
              No reuse found across the portfolio for that need.
            </p>
          ) : null}

          {!error && results !== null && results.length > 0 ? (
            <div style={{ marginTop: 20 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, margin: '0 2px 12px' }}>
                <h3 style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>Ranked candidates</h3>
                <span className="aos-mono" style={{ fontSize: 11, color: 'var(--ink-3)' }}>
                  {results.length} matched
                </span>
              </div>
              {results.map((rec, index) => (
                <ReuseCard key={`${rec.source_repository}-${index}`} rec={rec} rank={index + 1} />
              ))}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
