import React, { useCallback, useEffect, useState } from 'react';
import { fetchPendingAuthorityActions, type PendingAuthorityAction } from '../../api';

// AOS-AUTHORITY-001 (UI) — the pending authority actions queue on the Awaiting You
// surface (eval Finding 10). Every high-impact action awaiting a human decision
// (an ApprovalRecord with approval_status "pending") is visible here, most recent
// first, with its declared capability, target, requester, and risk level. This is
// the operator-facing half of "review-first is enforced infrastructure".

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

// Higher action_level = more dangerous (repo_write..delete_destructive); tint the
// level pill so a destructive request reads as urgent at a glance.
function levelTier(level: number): string {
  if (level >= 6) return 'risk';
  if (level >= 4) return 'warn';
  return '';
}

function ActionCard({ action }: { action: PendingAuthorityAction }) {
  const requester = action.actor || action.agent || action.tool || 'unknown';
  return (
    <li
      className="aos-hud glass aos-card"
      data-testid="authority-action-card"
      data-capability={action.requested_capability ?? ''}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span className={`aos-pill ${levelTier(action.action_level)}`} data-testid="authority-action-level">
          level {action.action_level}
        </span>
        <h3 style={{ margin: 0, fontSize: 15 }}>{action.requested_capability ?? 'action'}</h3>
        <span className="aos-pill info" data-testid="authority-action-status">
          {action.approval_status}
        </span>
      </div>

      <div className="aos-rowmeta aos-mono" style={{ marginTop: 6 }}>
        {action.target ? `target ${action.target} · ` : ''}requested by {requester}
      </div>

      {action.reason ? (
        <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 12.5 }}>{action.reason}</p>
      ) : null}
    </li>
  );
}

export function AuthorityQueue() {
  const [actions, setActions] = useState<PendingAuthorityAction[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setActions(await fetchPendingAuthorityActions());
    } catch (err) {
      setActions(null);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const count = actions?.length ?? 0;
  const isEmpty = actions !== null && actions.length === 0;

  return (
    <div data-testid="authority-queue" style={{ marginTop: 24 }}>
      <h3 style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', margin: '0 0 10px' }}>
        Authority actions awaiting approval
        {actions !== null && count > 0 ? (
          <span className="aos-pill warn" data-testid="authority-count">
            {count} pending
          </span>
        ) : null}
      </h3>

      {error ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Authority queue</span>
          <p role="alert" className="aos-error" data-testid="authority-error" style={{ marginTop: 8 }}>
            Authority queue unavailable: {error}
          </p>
        </div>
      ) : loading && actions === null ? (
        <div className="aos-hud glass aos-card">
          <p className="aos-muted" data-testid="authority-loading" style={{ margin: 0 }}>
            Loading the authority queue…
          </p>
        </div>
      ) : isEmpty ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Authority queue</span>
          <p className="aos-muted" data-testid="authority-empty" style={{ margin: '8px 0 0' }}>
            No high-impact actions awaiting approval. Write and destructive actions land here for a human decision before they run.
          </p>
        </div>
      ) : actions !== null ? (
        <ul className="aos-rows" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {actions.map((action) => (
            <ActionCard key={action.id} action={action} />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
