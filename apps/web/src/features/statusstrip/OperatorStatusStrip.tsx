import { useEffect, useState } from 'react';
import { fetchNodes, fetchPendingAuthorityActions } from '../../api';

// AOS-UX-IA-001 (deliverable 3) — the global operator status strip. A compact
// topbar summary of the things an operator most wants at a glance: how many
// actions await their approval and how healthy the node network is. Both are
// global (project-independent) reads. It is deliberately non-blocking: any fetch
// failure degrades a single pill to "—" and never affects the rest of the shell.
export function OperatorStatusStrip() {
  const [pendingApprovals, setPendingApprovals] = useState<number | null>(null);
  const [nodesHealthy, setNodesHealthy] = useState<number | null>(null);
  const [nodesTotal, setNodesTotal] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      // Each read is independent so one failing endpoint does not blank the other.
      try {
        const pending = await fetchPendingAuthorityActions();
        if (!cancelled) {
          setPendingApprovals(pending.length);
        }
      } catch {
        if (!cancelled) {
          setPendingApprovals(null);
        }
      }
      try {
        const nodes = await fetchNodes();
        if (!cancelled) {
          setNodesHealthy(nodes.filter((node) => node.node_status === 'healthy').length);
          setNodesTotal(nodes.length);
        }
      } catch {
        if (!cancelled) {
          setNodesHealthy(null);
          setNodesTotal(null);
        }
      }
    };

    void load();
    // Light poll so the strip stays roughly current without hammering the API.
    const id = window.setInterval(() => void load(), 30000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const approvalsTier = pendingApprovals && pendingApprovals > 0 ? 'warn' : '';
  const nodesTier =
    nodesTotal !== null && nodesHealthy !== null && nodesHealthy < nodesTotal ? 'warn' : 'good';

  return (
    <div
      className="aos-status-strip"
      data-testid="operator-status-strip"
      aria-label="Operator status"
    >
      <span
        className={`aos-pill ${approvalsTier}`}
        data-testid="status-strip-approvals"
        title="Actions awaiting your approval"
      >
        {pendingApprovals === null ? '—' : pendingApprovals} awaiting
      </span>
      <span
        className={`aos-pill ${nodesTotal ? nodesTier : ''}`}
        data-testid="status-strip-nodes"
        title="Healthy nodes / total registered nodes"
      >
        {nodesHealthy === null || nodesTotal === null
          ? '— nodes'
          : `${nodesHealthy}/${nodesTotal} nodes`}
      </span>
    </div>
  );
}
