import React, { useCallback, useEffect, useState } from 'react';
import {
  approveDecision,
  fetchDecisions,
  fetchProjects,
  rejectDecision,
  type Decision,
} from '../../api';
import { AuthorityQueue } from '../authority/AuthorityQueue';

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

// The two pending states this governance queue surfaces, most-actionable first:
// a `draft` is approvable now; a `needs_evidence` decision is blocked on
// evidence (the API enforces this with a 409 on approve — LES-019). `SORT_RANK`
// keeps `draft` cards ahead of `needs_evidence` ones regardless of fetch order.
const PENDING_STATES = ['draft', 'needs_evidence'] as const;
const SORT_RANK: Record<string, number> = { draft: 0, needs_evidence: 1 };

// The readable reason a `needs_evidence` decision cannot be approved — mirrors
// the LES-019 409 the API returns (abstention blocks approval).
const NEEDS_EVIDENCE_REASON = 'needs evidence — assemble evidence before approval';

// A pending decision tagged with the project it belongs to, so the aggregated
// queue can show provenance (which project each item came from).
type PendingItem = Decision & { projectId: string; projectName: string };

// `draft` counts research-note evidence entries as its "evidence count"; we show
// the full evidence array length, which is what the Council view reports.
function evidenceCount(decision: Decision): number {
  return Array.isArray(decision.evidence) ? decision.evidence.length : 0;
}

// Aggregate every pending decision across the operator's projects into one list.
// N+1 by design (small portfolio; a `GET /decisions/pending` endpoint is a noted
// future optimization). A per-project decisions fetch that fails is SKIPPED via
// Promise.allSettled — one bad project never fails the whole queue. Throws only
// if the top-level `fetchProjects()` itself fails (surfaced as the error state).
async function loadPending(): Promise<PendingItem[]> {
  const projects = await fetchProjects();
  const settled = await Promise.allSettled(projects.map((p) => fetchDecisions(p.id)));
  const items: PendingItem[] = [];
  settled.forEach((result, index) => {
    if (result.status !== 'fulfilled') {
      return; // skip a project whose decisions could not be loaded
    }
    const project = projects[index];
    for (const decision of result.value) {
      if ((PENDING_STATES as readonly string[]).includes(decision.status)) {
        items.push({ ...decision, projectId: project.id, projectName: project.name });
      }
    }
  });
  // Most-actionable first: draft before needs_evidence; stable within a tier.
  items.sort((a, b) => (SORT_RANK[a.status] ?? 9) - (SORT_RANK[b.status] ?? 9));
  return items;
}

function StatusPill({ status }: { status: string }) {
  // needs_evidence renders distinct (muted-red `warn`); draft is actionable `info`.
  const tier = status === 'needs_evidence' ? 'warn' : 'info';
  return <span className={`aos-pill ${tier}`}>{status}</span>;
}

type ApprovalCardProps = {
  item: PendingItem;
  onResolved: (decisionId: string) => void;
};

function ApprovalCard({ item, onResolved }: ApprovalCardProps) {
  const [approver, setApprover] = useState('');
  const [rationale, setRationale] = useState('');
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const blocked = item.status === 'needs_evidence';
  const trimmedApprover = approver.trim();
  const trimmedRationale = rationale.trim();

  const approve = useCallback(async () => {
    if (blocked) {
      return; // guarded by the disabled button; belt-and-suspenders
    }
    if (!trimmedApprover) {
      setError('Enter an approver name.');
      return;
    }
    setBusy('approve');
    setError(null);
    try {
      await approveDecision(item.id, trimmedApprover, trimmedRationale || undefined);
      onResolved(item.id);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(null);
    }
  }, [blocked, item.id, trimmedApprover, trimmedRationale, onResolved]);

  const reject = useCallback(async () => {
    if (!trimmedApprover) {
      setError('Enter an approver name.');
      return;
    }
    // Reject requires a non-empty rationale (the API enforces it).
    if (!trimmedRationale) {
      setError('Enter a rationale to reject.');
      return;
    }
    setBusy('reject');
    setError(null);
    try {
      await rejectDecision(item.id, trimmedApprover, trimmedRationale);
      onResolved(item.id);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(null);
    }
  }, [item.id, trimmedApprover, trimmedRationale, onResolved]);

  return (
    <li className="aos-hud glass aos-card" data-testid="approval-card" data-status={item.status}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <StatusPill status={item.status} />
        <span className="aos-eyebrow" style={{ letterSpacing: '0.12em' }}>
          {item.projectName}
        </span>
      </div>

      <h3 style={{ margin: '8px 0 4px', fontSize: 16 }}>{item.title}</h3>
      <div className="aos-rowmeta aos-mono">
        confidence {item.confidence} · {evidenceCount(item)} evidence
        {evidenceCount(item) === 1 ? ' item' : ' items'}
      </div>

      {blocked ? (
        <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 13 }} data-testid="approval-blocked-reason">
          {NEEDS_EVIDENCE_REASON}
        </p>
      ) : null}

      <div className="aos-form-row" style={{ marginTop: 10 }}>
        <input
          className="aos-input"
          type="text"
          data-testid="approval-approver"
          value={approver}
          placeholder="Approver name"
          aria-label={`Approver for ${item.title}`}
          onChange={(event) => setApprover(event.target.value)}
          style={{ width: 'auto', flex: '1 1 180px' }}
        />
        <input
          className="aos-input"
          type="text"
          data-testid="approval-rationale"
          value={rationale}
          placeholder={blocked ? 'Rejection rationale (required)' : 'Rationale (optional to approve)'}
          aria-label={`Rationale for ${item.title}`}
          onChange={(event) => setRationale(event.target.value)}
          style={{ width: 'auto', flex: '1 1 220px' }}
        />
        <button
          type="button"
          className="aos-btn aos-btn-sm"
          data-testid="approval-approve"
          disabled={blocked || busy !== null}
          title={blocked ? NEEDS_EVIDENCE_REASON : undefined}
          aria-disabled={blocked || busy !== null}
          onClick={() => void approve()}
        >
          {busy === 'approve' ? 'Approving…' : 'Approve'}
        </button>
        <button
          type="button"
          className="aos-btn-ghost aos-btn-sm"
          data-testid="approval-reject"
          disabled={busy !== null}
          onClick={() => void reject()}
        >
          {busy === 'reject' ? 'Rejecting…' : 'Reject'}
        </button>
      </div>

      {error ? (
        <p role="alert" className="aos-error" style={{ margin: '8px 0 0' }}>
          {error}
        </p>
      ) : null}
    </li>
  );
}

export function ApprovalsView() {
  const [items, setItems] = useState<PendingItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await loadPending());
    } catch (err) {
      // Graceful degradation: a missing/absent API (static preview, backend
      // down) must never throw or blank the screen — surface a readable notice.
      setItems(null);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // On approve/reject success, drop the resolved card and decrement the count.
  const handleResolved = useCallback((decisionId: string) => {
    setItems((prev) => (prev ? prev.filter((item) => item.id !== decisionId) : prev));
  }, []);

  const count = items?.length ?? 0;
  const isEmpty = items !== null && items.length === 0;

  return (
    <section className="aos-view" data-testid="approvals-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--signal)' }} aria-hidden="true">
            &#9672;
          </span>
          Council · Awaiting You
        </span>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          Decisions awaiting your approval
          {items !== null && count > 0 ? (
            <span className="aos-pill info" data-testid="approvals-count">
              {count} pending
            </span>
          ) : null}
        </h2>
      </div>

      {error ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Governance queue</span>
          <p role="alert" className="aos-error" data-testid="approvals-error" style={{ marginTop: 8 }}>
            Queue unavailable: {error}
          </p>
          <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 13 }}>
            The queue aggregates <span className="aos-mono">GET /projects</span> and each project&apos;s{' '}
            <span className="aos-mono">/decisions</span>. Once the API is reachable, pending decisions
            appear here.
          </p>
        </div>
      ) : loading && items === null ? (
        <div className="aos-hud glass aos-card">
          <p className="aos-muted" data-testid="approvals-loading" style={{ margin: 0 }}>
            Loading the governance queue…
          </p>
        </div>
      ) : isEmpty ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Governance queue</span>
          <p className="aos-muted" data-testid="approvals-empty" style={{ margin: '8px 0 0' }}>
            Nothing awaiting you — the council queue is clear.
          </p>
          <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 13 }}>
            Drafted decisions in <span className="aos-mono">draft</span> or{' '}
            <span className="aos-mono">needs_evidence</span> across your projects surface here for a
            named approve or reject.
          </p>
        </div>
      ) : items !== null ? (
        <ul className="aos-rows" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {items.map((item) => (
            <ApprovalCard key={item.id} item={item} onResolved={handleResolved} />
          ))}
        </ul>
      ) : null}

      {/* AOS-AUTHORITY-001: the enforced authority action queue. High-impact
          actions (write/destructive/sensitive egress) land here for a human
          decision before they run — review-first as infrastructure. */}
      <AuthorityQueue />

      <p className="aos-mono aos-muted" style={{ margin: '16px 0 0', fontSize: 11.5 }}>
        Decisions approve/reject above; high-impact authority actions await approval below. Temporary
        grants, audit search, and Emergency Stop are still coming.
      </p>
    </section>
  );
}
