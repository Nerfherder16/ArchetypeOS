import React, { useCallback, useEffect, useState } from 'react';
import { fetchNodes, type NodeInfo } from '../../api';

// AOS-NODE-001 (UI) — Operations → Nodes. Read-only surface showing registered
// execution nodes: health, capabilities, and their safety posture (read-only vs
// write, sensitivity ceiling). The control plane routes capability-declared work
// to eligible nodes; this is where the operator sees the fleet.

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

const STATUS_TIER: Record<string, string> = {
  healthy: 'good',
  degraded: 'warn',
  offline: 'risk',
  unknown: '',
};

function NodeCard({ node }: { node: NodeInfo }) {
  return (
    <li className="aos-hud glass aos-card" data-testid="node-card" data-status={node.node_status}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span className={`aos-pill ${STATUS_TIER[node.node_status] ?? ''}`} data-testid="node-status">
          {node.node_status}
        </span>
        <h3 style={{ margin: 0, fontSize: 15 }}>{node.name}</h3>
        <span className="aos-eyebrow" style={{ letterSpacing: '0.12em' }}>
          {node.node_type}
        </span>
        <span className={`aos-pill ${node.write_access ? 'warn' : ''}`} title="write access">
          {node.write_access ? 'read-write' : 'read-only'}
        </span>
        <span className="aos-pill" title="max sensitivity">
          {node.max_sensitivity}
        </span>
      </div>

      <div className="aos-rowmeta aos-mono" style={{ marginTop: 6 }}>
        {node.endpoint ?? 'no endpoint'}
        {node.last_seen_at ? ` · last seen ${new Date(node.last_seen_at).toLocaleString()}` : ' · never seen'}
      </div>

      {node.capabilities.length > 0 ? (
        <div className="aos-pills" data-testid="node-capabilities" style={{ marginTop: 10 }}>
          {node.capabilities.map((cap) => (
            <span key={cap.id} className="aos-pill info">
              {cap.capability}
              {cap.capability_version ? ` v${cap.capability_version}` : ''}
            </span>
          ))}
        </div>
      ) : (
        <p className="aos-muted" style={{ margin: '10px 0 0', fontSize: 12.5 }}>No declared capabilities.</p>
      )}
    </li>
  );
}

export function NodesView() {
  const [nodes, setNodes] = useState<NodeInfo[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setNodes(await fetchNodes());
    } catch (err) {
      setNodes(null);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const count = nodes?.length ?? 0;
  const isEmpty = nodes !== null && nodes.length === 0;

  return (
    <section className="aos-view" data-testid="nodes-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--signal)' }} aria-hidden="true">
            &#9672;
          </span>
          Operations · Nodes / Runtime
        </span>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          Registered execution nodes
          {nodes !== null && count > 0 ? (
            <span className="aos-pill info" data-testid="nodes-count">
              {count} node{count === 1 ? '' : 's'}
            </span>
          ) : null}
        </h2>
      </div>

      {error ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Node registry</span>
          <p role="alert" className="aos-error" data-testid="nodes-error" style={{ marginTop: 8 }}>
            Registry unavailable: {error}
          </p>
        </div>
      ) : loading && nodes === null ? (
        <div className="aos-hud glass aos-card">
          <p className="aos-muted" data-testid="nodes-loading" style={{ margin: 0 }}>
            Loading the node registry…
          </p>
        </div>
      ) : isEmpty ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Node registry</span>
          <p className="aos-muted" data-testid="nodes-empty" style={{ margin: '8px 0 0' }}>
            No nodes registered yet. A node appears here after it calls POST /nodes/register with its capabilities.
          </p>
        </div>
      ) : nodes !== null ? (
        <ul className="aos-rows" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {nodes.map((node) => (
            <NodeCard key={node.id} node={node} />
          ))}
        </ul>
      ) : null}

      <p className="aos-mono aos-muted" style={{ margin: '16px 0 0', fontSize: 11.5 }}>
        Read-only surface. Nodes are read-only by default; capability-aware routing of jobs to eligible nodes is the next slice.
      </p>
    </section>
  );
}
